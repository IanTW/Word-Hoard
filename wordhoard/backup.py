"""Plain-text export of the parts of the database that cannot be rebuilt.

The content half of this project is rebuildable at any time: `lexical_items` is
a transcription of a reviewed TSV, and `scripts/import_lexical_items.py` is
re-runnable. The learning half is not. `review_log` is append-only history and
`item_state` is the scheduler's memory of it, and nothing anywhere can
reconstruct either one. The database file itself is gitignored, deliberately,
because SQLite diffs terribly: a one-row logical change rewrites large stretches
of binary. So the versioned artifact is this export instead.

Format is newline-delimited JSON, one row per line. Chosen over a single JSON
document for three reasons that all matter for a file living in git: a new
review appends one line rather than reindenting the whole file, a truncated
write damages one line rather than the document, and a diff shows the rows that
changed rather than a wall of red and green.

**Natural keys, and why the ids alone are not enough.** `review_log` and
`item_state` point at content through a polymorphic `(content_type, content_id)`
pair, where `content_id` is an autoincrement primary key assigned at import
time. Restoring history against a rebuilt database therefore depends on those
ids landing identically, which happens to be true today because the import walks
the TSV in order, and which is a coincidence rather than a guarantee. Reorder
the TSV, or insert a word in the middle, and a restore would silently attribute
one word's history to another. Every exported row therefore carries a
`content_key` as well: a stable, human-readable identity resolved from the
content itself. The id is kept for reference; the key is what a restore should
match on.

This module is framework-free, like everything else under `wordhoard/`, and it
never writes to the database it reads.
"""

from __future__ import annotations

import json
import os
import sqlite3
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from wordhoard import db

# Where the export lands by default. Under data/ rather than at the repository
# root because it is data, and committed rather than gitignored because being
# committed is the entire purpose: see .gitignore, which excludes *.db and says
# so.
DEFAULT_BACKUP_DIR = db.REPO_ROOT / "data" / "backup"

# Bumped only when the shape of an exported line changes in a way that a reader
# would have to know about. A restore script checks this before trusting a file.
EXPORT_FORMAT_VERSION = 1


def default_backup_dir_for(db_path: Path | str) -> Path:
    """Choose where a given database's export belongs.

    The project database exports to data/backup/, which is the versioned
    artifact. **Any other database exports somewhere else**, next to itself.

    This exists because of a defect found while wiring the automatic export on
    2026-09-08: `scripts/review.py --db scratch.db` would have run a session
    against a throwaway database and then written that throwaway's contents over
    data/backup/, silently replacing the real backup with test data. The failure
    is quiet, it looks like a successful session, and it destroys exactly the
    thing this module exists to protect. Deriving the directory from the
    database removes the possibility rather than warning about it.
    """
    db_path = Path(db_path).resolve()
    if db_path == Path(db.DEFAULT_DB_PATH).resolve():
        return DEFAULT_BACKUP_DIR
    return db_path.parent / f"{db_path.stem}-backup"


def _utc_now_iso() -> str:
    """Timestamp for the manifest, in UTC with an explicit offset.

    Explicit rather than naive because the manifest is the one place a human
    looks to answer "how old is this backup", and a naive timestamp read on a
    machine in another timezone answers it wrongly.
    """
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _content_keys(conn: sqlite3.Connection) -> dict[tuple[str, int], str]:
    """Map every (content_type, content_id) pair to a stable natural key.

    The key format is "<content_type>:<language_code>:<identity>", for example
    "lexical_item:de:Haus". Language is part of it because the same lemma can
    legitimately exist in both German and Dutch, which is the whole reason this
    project is built around a language code rather than one table per language.

    Only lexical items exist as schedulable content today. Sentences are planned
    (M5), so the dispatch below is written to be extended by adding a query
    rather than by restructuring anything. If a content type appears that this
    function does not know, the caller raises rather than writing a row with no
    key, because a backup that silently drops the identity of its rows is worse
    than one that refuses to run.
    """
    keys: dict[tuple[str, int], str] = {}

    # Lexical items. The lemma is the natural identity: the import script already
    # treats it as unique per language, and it is what a human reading the export
    # would recognise.
    for row in conn.execute(
        "SELECT id, language_code, lemma FROM lexical_items ORDER BY id"
    ):
        keys[("lexical_item", row["id"])] = (
            f"lexical_item:{row['language_code']}:{row['lemma']}"
        )

    return keys


def _rows_as_dicts(conn: sqlite3.Connection, sql: str) -> list[dict]:
    """Run a query and return plain dicts, so json.dumps can take them directly.

    sqlite3.Row is convenient for access by name but is not JSON serialisable,
    and converting at the point of the query keeps that detail out of the three
    call sites below.
    """
    return [dict(row) for row in conn.execute(sql)]


def _attach_content_key(rows: list[dict], keys: dict[tuple[str, int], str],
                        source: str) -> list[dict]:
    """Add the natural key to every row that carries a polymorphic reference.

    Raises rather than skipping when a reference cannot be resolved. An
    unresolvable reference means either a content type this module has not been
    taught about, or a genuinely orphaned row; both are worth stopping for, and
    neither should be discovered later by someone trying to restore.
    """
    for row in rows:
        pair = (row["content_type"], row["content_id"])
        if pair not in keys:
            raise ValueError(
                f"{source}: cannot resolve a natural key for "
                f"content_type={row['content_type']!r} content_id={row['content_id']!r}. "
                "Refusing to write a backup whose rows cannot be matched back to "
                "their content. Teach _content_keys() about this content type."
            )
        row["content_key"] = keys[pair]
    return rows


def _write_ndjson(path: Path, rows: list[dict]) -> int:
    """Write rows as newline-delimited JSON, atomically.

    Atomic because the failure this guards against is specific and nasty: a
    process dying part way through a write leaves a file that still parses line
    by line up to the cut, so it looks like a smaller but valid backup rather
    than a damaged one. Writing to a temporary file in the same directory and
    then replacing means a reader sees either the previous complete file or the
    new complete file, never a partial one. Same directory matters, because
    os.replace is only atomic within a filesystem.

    ensure_ascii is off so that umlauts and eszett appear as themselves. The
    file is UTF-8 and the point of a plain-text artifact is that a human can
    read it; "M\\u00e4dchen" defeats that.

    sort_keys is on so a field order change in a query cannot produce a diff
    that looks like a data change.
    """
    path.parent.mkdir(parents=True, exist_ok=True)

    # delete=False because the file is renamed rather than dropped; the finally
    # block cleans it up if the replace never happens.
    tmp = tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", newline="\n",
        dir=str(path.parent), prefix=path.name + ".", suffix=".tmp",
        delete=False,
    )
    try:
        with tmp:
            for row in rows:
                tmp.write(json.dumps(row, ensure_ascii=False, sort_keys=True))
                tmp.write("\n")
            # Force the bytes to disk before the rename. Without this the rename
            # can be durable while the contents are not, which on a power loss
            # produces exactly the empty-but-present backup this is all meant to
            # prevent.
            tmp.flush()
            os.fsync(tmp.fileno())
        os.replace(tmp.name, path)
    except BaseException:
        # Best effort: if the temporary file survives a failure it is noise in a
        # data directory, and its absence must not mask the original error.
        try:
            os.unlink(tmp.name)
        except OSError:
            pass
        raise

    return len(rows)


def export(db_path: Path | str = db.DEFAULT_DB_PATH,
           backup_dir: Path | str | None = None) -> dict:
    """Export the irreplaceable tables to newline-delimited JSON.

    Returns a manifest dict describing what was written, which the caller can
    print or ignore. Read-only with respect to the database.

    Ordering is explicit and total in every query. Two exports of unchanged data
    must produce byte-identical files, or every export produces a spurious git
    diff and the reader learns to stop looking at them.
    """
    # None rather than a constant default, so a caller passing only a database
    # cannot accidentally aim a scratch database's export at the real backup.
    # See default_backup_dir_for().
    backup_dir = Path(backup_dir) if backup_dir is not None else default_backup_dir_for(db_path)
    conn = db.connect(db_path)
    try:
        keys = _content_keys(conn)

        # The append-only history. Ordered by id, which is both the insertion
        # order and a total order, so this file grows by appending lines.
        review_log = _attach_content_key(
            _rows_as_dicts(
                conn,
                "SELECT * FROM review_log ORDER BY id",
            ),
            keys, "review_log",
        )

        # The scheduler's current state. No autoincrement id here, so order by
        # the composite key that identifies a row.
        item_state = _attach_content_key(
            _rows_as_dicts(
                conn,
                "SELECT * FROM item_state "
                "ORDER BY learner_id, language_code, content_type, content_id",
            ),
            keys, "item_state",
        )

        # Context. Small, and without it the two files above are a pile of
        # integers: learner 1 and language 'de' mean nothing on their own.
        learners = _rows_as_dicts(conn, "SELECT * FROM learners ORDER BY id")
        learner_languages = _rows_as_dicts(
            conn,
            "SELECT * FROM learner_languages ORDER BY learner_id, language_code",
        )

        counts = {
            "review_log": _write_ndjson(backup_dir / "review_log.ndjson", review_log),
            "item_state": _write_ndjson(backup_dir / "item_state.ndjson", item_state),
            "learners": _write_ndjson(backup_dir / "learners.ndjson", learners),
            "learner_languages": _write_ndjson(
                backup_dir / "learner_languages.ndjson", learner_languages),
        }

        manifest = {
            "format_version": EXPORT_FORMAT_VERSION,
            "exported_at": _utc_now_iso(),
            "source_db": str(Path(db_path).name),
            "counts": counts,
        }

        # The manifest is ordinary JSON rather than NDJSON: it is one object, it
        # is read whole, and a human opening the backup directory should find the
        # summary in the obvious shape.
        manifest_path = backup_dir / "manifest.json"
        manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

        return manifest
    finally:
        conn.close()


def export_quietly(db_path: Path | str = db.DEFAULT_DB_PATH,
                   backup_dir: Path | str | None = None) -> dict | None:
    """Export, but never raise.

    For call sites inside the review loop. The ordering rule there is absolute:
    **a backup failure must not cost the learner an answer.** The answer has
    already been written to an append-only log by the time this runs, so an
    exception escaping here would turn a successful review into a failed request
    and, in the browser, into a lost keystroke and a confusing error page.

    Returns the manifest on success and None on failure, so a caller that wants
    to surface the problem can. Silence here is deliberate, not an oversight:
    the loud version is `scripts/export_backup.py`, which is what a human runs
    when they want to know.
    """
    try:
        return export(db_path=db_path, backup_dir=backup_dir)
    except Exception:
        return None
