"""Import a reviewed vocabulary TSV into lexical_items, and enrol the drillable
rows into the scheduler.

Vertical slice step 2e. Run:

    python scripts/import_lexical_items.py --language de
    python scripts/import_lexical_items.py --language de --dry-run

The reviewed TSV is the source of truth for content, and this script is a pure
re-runnable transcription of it into the database. Correct a word by editing the
generating script, regenerating the TSV, and re-running this import. Never patch
content by hand in the database, because then the two disagree and the file that
a human actually reviewed stops being the record of what is being drilled.

That re-runnability forces one hard asymmetry, which is the main thing to
understand about this file:

  * lexical_items is CONTENT. It is owned by the TSV and is safe to overwrite.
  * item_state is SCHEDULING PROGRESS. It is owned by the learner's real review
    history and is never overwritten, never reset, and never deleted here.

So a re-run may freely correct a translation or a gender, and must not undo a
fortnight of reviews. See docs/OVERVIEW.md on why review history is the asset
this project protects above everything else.
"""

from __future__ import annotations

import argparse
import csv
import sqlite3
import sys
from pathlib import Path

# Allow running this file directly (python scripts/import_lexical_items.py)
# without needing the package installed or PYTHONPATH set. Same trick as
# init_db.py; keeps the run story to one command.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from wordhoard import db  # noqa: E402  (import must follow the sys.path fix above)

# Where the reviewed drafts live, keyed by language. A plain dict rather than a
# naming convention because the file names are historical and one of them will
# not match whatever pattern gets invented later.
DEFAULT_TSV = {
    "de": db.REPO_ROOT / "data" / "review" / "german_draft.tsv",
}

# TSV columns that carry actual content and map straight onto lexical_items
# columns of the same name. Everything else in the file is review scaffolding.
CONTENT_COLUMNS = [
    "lemma",
    "answer_form",
    "part_of_speech",
    "gender",
    "translation_en",
    "pronunciation",
    "category",
    "notes",
]

# TSV columns that exist for the human review round trip and are deliberately
# NOT imported. `source_text` is the raw mindmap node the entry came from and
# `changes` records what Claude altered, both of which matter when a person is
# checking the draft and mean nothing to the scheduler. Listed explicitly rather
# than ignored silently, so that a new column added to the TSV fails the header
# check below instead of being dropped without anyone noticing.
REVIEW_ONLY_COLUMNS = ["drillable", "source_text", "changes"]

# The polymorphic content type these rows are scheduled under. item_state and
# review_log reference content by (content_type, content_id) with no foreign
# key, so this string is the only thing tying a scheduler row back to this
# table. It is a constant here rather than a literal at each call site because
# a typo would produce rows that silently never appear in any due queue.
CONTENT_TYPE = "lexical_item"


def read_rows(tsv_path: Path) -> list[dict[str, str]]:
    """Read the reviewed TSV and check its shape before anything is written.

    Every check here is a whole-file gate: the import either takes the file or
    refuses it. A partial import is the worst outcome, because it leaves the
    database in a state no file describes and a re-run cannot reason about.
    """
    with open(tsv_path, encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        header = reader.fieldnames or []
        rows = list(reader)

    # The header must match exactly. An unexpected column means the TSV format
    # moved and this script's assumptions are stale; a missing one means data
    # would be silently imported as NULL.
    expected = CONTENT_COLUMNS + REVIEW_ONLY_COLUMNS
    if sorted(header) != sorted(expected):
        missing = sorted(set(expected) - set(header))
        unexpected = sorted(set(header) - set(expected))
        raise ValueError(
            f"{tsv_path.name} header does not match the expected columns. "
            f"missing={missing} unexpected={unexpected}"
        )

    problems: list[str] = []

    # Duplicate lemmas would make the (language_code, lemma) match below
    # ambiguous, so they are rejected outright rather than resolved by guessing.
    seen: dict[str, int] = {}
    for line_number, row in enumerate(rows, start=2):  # start=2: line 1 is the header
        lemma = row["lemma"].strip()

        if not lemma:
            problems.append(f"line {line_number}: empty lemma")
            continue
        if lemma in seen:
            problems.append(
                f"line {line_number}: duplicate lemma {lemma!r} "
                f"(first seen at line {seen[lemma]})"
            )
        seen[lemma] = line_number

        if row["drillable"] not in ("yes", "no"):
            problems.append(
                f"line {line_number}: drillable must be 'yes' or 'no', "
                f"got {row['drillable']!r}"
            )

        if not row["part_of_speech"].strip():
            problems.append(f"line {line_number}: {lemma!r} has no part_of_speech")

        # A drillable row with no English gloss is unanswerable: the typing
        # exercise prompts in English, so there would be nothing to show. Worse
        # than useless, because the learner would fail it and review_log would
        # record a lapse that never happened. review_log is append-only and
        # feeds FSRS parameter refitting, so that false lapse is permanent.
        if row["drillable"] == "yes" and not row["translation_en"].strip():
            problems.append(
                f"line {line_number}: {lemma!r} is drillable but has no translation_en"
            )

        # A gendered noun must carry the determiner the learner is expected to
        # type. Accepting the bare noun would quietly excuse them from the
        # gender, which is the hard part. The generating script asserts this
        # too; it is repeated here because this is the last gate before the
        # content becomes something a person is actually drilled on.
        if row["part_of_speech"] == "noun" and row["gender"].strip():
            if not row["answer_form"].strip():
                problems.append(
                    f"line {line_number}: {lemma!r} is a gendered noun with no answer_form"
                )

    if problems:
        raise ValueError(
            f"{tsv_path.name} failed validation with {len(problems)} problem(s):\n  "
            + "\n  ".join(problems)
        )

    return rows


def blank_to_none(value: str) -> str | None:
    """Turn an empty TSV cell into SQL NULL.

    A TSV cannot express NULL, so an empty cell means 'not stated'. Storing it
    as an empty string instead would make every later query need to test for
    both, and one of those tests would eventually be forgotten.
    """
    value = value.strip()
    return value or None


def upsert_lexical_item(
    conn: sqlite3.Connection,
    language_code: str,
    row: dict[str, str],
) -> tuple[int, str]:
    """Insert or update one content row. Returns (id, 'inserted'|'updated'|'unchanged').

    Matched on (language_code, lemma) in Python rather than with an ON CONFLICT
    clause, because there is deliberately no UNIQUE index on that pair. German
    has genuine homographs that will eventually need two rows with one lemma
    ('die Bank' is both a bench and a bank), and a unique index added now to
    make this function tidier would block that content later. Instead the
    ambiguous case is refused loudly and left for a human, which is the right
    trade while the whole corpus fits on one screen.
    """
    values = {name: blank_to_none(row[name]) for name in CONTENT_COLUMNS}

    existing = conn.execute(
        "SELECT * FROM lexical_items WHERE language_code = ? AND lemma = ?",
        (language_code, values["lemma"]),
    ).fetchall()

    if len(existing) > 1:
        raise ValueError(
            f"{values['lemma']!r} already matches {len(existing)} rows in "
            f"lexical_items; cannot tell which one the TSV means. Resolve by hand."
        )

    if not existing:
        columns = ["language_code"] + CONTENT_COLUMNS
        placeholders = ", ".join("?" for _ in columns)
        cursor = conn.execute(
            f"INSERT INTO lexical_items ({', '.join(columns)}) VALUES ({placeholders})",
            [language_code] + [values[name] for name in CONTENT_COLUMNS],
        )
        return cursor.lastrowid, "inserted"

    current = existing[0]

    # Only write when something actually differs, so the reported counts mean
    # something. An import that claims 117 updates every run tells nobody
    # whether the last edit landed.
    changed = {
        name: values[name]
        for name in CONTENT_COLUMNS
        if current[name] != values[name]
    }
    if not changed:
        return current["id"], "unchanged"

    assignments = ", ".join(f"{name} = ?" for name in changed)
    conn.execute(
        f"UPDATE lexical_items SET {assignments} WHERE id = ?",
        list(changed.values()) + [current["id"]],
    )
    return current["id"], "updated"


def ensure_item_state(
    conn: sqlite3.Connection,
    learner_id: int,
    language_code: str,
    content_id: int,
) -> bool:
    """Create the scheduler row for one item if it does not exist. True if created.

    Never updates an existing row. That row may carry months of stability,
    difficulty and lapse counts derived from real reviews, and no amount of
    content correction justifies resetting it.

    New rows are left at the schema defaults: state 'new', step_index 0, and
    due_at NULL. NULL due_at is meaningful rather than missing. It means the
    item has never been seen, so the due queue picks it up through the daily new
    limit rather than through a date comparison, which is how the learning-steps
    machine expects to receive it.
    """
    cursor = conn.execute(
        """
        INSERT INTO item_state (learner_id, language_code, content_type, content_id)
        VALUES (?, ?, ?, ?)
        ON CONFLICT (learner_id, content_type, content_id) DO NOTHING
        """,
        (learner_id, language_code, CONTENT_TYPE, content_id),
    )
    return cursor.rowcount == 1


def main() -> int:
    """Parse arguments, import the file, and report exactly what changed."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--language",
        default="de",
        help="Language code of the content being imported (default: de)",
    )
    parser.add_argument(
        "--tsv",
        help="Reviewed TSV to import. Defaults to the known draft for --language.",
    )
    parser.add_argument(
        "--db",
        default=db.DEFAULT_DB_PATH,
        help=f"Database file to import into (default: {db.DEFAULT_DB_PATH.name})",
    )
    parser.add_argument(
        "--learner",
        help="Display name of the learner to create scheduler rows for. "
             "Optional when exactly one learner exists.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Do the whole import inside a transaction and roll it back. The "
             "counts reported are the real ones, not a prediction.",
    )
    args = parser.parse_args()

    # Resolve the input file before touching the database, so a typo in --tsv
    # costs nothing.
    if args.tsv:
        tsv_path = Path(args.tsv)
    elif args.language in DEFAULT_TSV:
        tsv_path = DEFAULT_TSV[args.language]
    else:
        print(
            f"error: no default TSV for language {args.language!r}; pass --tsv",
            file=sys.stderr,
        )
        return 1

    if not tsv_path.exists():
        print(f"error: {tsv_path} does not exist", file=sys.stderr)
        return 1

    db_path = Path(args.db)
    if not db_path.exists():
        print(
            f"error: {db_path} does not exist; run scripts/init_db.py first",
            file=sys.stderr,
        )
        return 1

    try:
        rows = read_rows(tsv_path)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    conn = db.connect(db_path)

    try:
        learner_id, learner_name = db.find_learner(conn, args.learner)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    # The language must already be seeded, since lexical_items.language_code is
    # a real foreign key. Checked here to give a readable message rather than a
    # constraint violation from deep inside the loop.
    if not conn.execute(
        "SELECT 1 FROM languages WHERE code = ?", (args.language,)
    ).fetchone():
        print(f"error: language {args.language!r} is not seeded", file=sys.stderr)
        return 1

    counts = {"inserted": 0, "updated": 0, "unchanged": 0}
    scheduled = 0
    warnings: list[str] = []

    # One transaction for the whole file rather than a commit per row. The
    # project's commit-per-item rule exists for jobs measured in hours, where an
    # interrupted run should keep what it finished. This run is a hundred-odd
    # rows and finishes instantly, so all-or-nothing is the safer property: the
    # database is never left holding half a vocabulary batch.
    #
    # It is also what makes --dry-run honest. The dry run takes the real write
    # path and rolls back at the end, so its numbers are measurements rather
    # than predictions.
    try:
        conn.execute("BEGIN")

        for row in rows:
            content_id, outcome = upsert_lexical_item(conn, args.language, row)
            counts[outcome] += 1

            if row["drillable"] == "yes":
                if ensure_item_state(conn, learner_id, args.language, content_id):
                    scheduled += 1
            else:
                # A row that was once drillable and has since been demoted keeps
                # its scheduler row. Suppressing content from future study is a
                # reversible edit; deleting item_state would throw away real
                # review counts to tidy up a table. Reported so the decision is
                # visible rather than silent.
                already = conn.execute(
                    "SELECT 1 FROM item_state WHERE learner_id = ? "
                    "AND content_type = ? AND content_id = ?",
                    (learner_id, CONTENT_TYPE, content_id),
                ).fetchone()
                if already:
                    warnings.append(
                        f"{row['lemma']!r} is marked drillable=no but already has a "
                        f"scheduler row; left in place rather than deleted"
                    )

        if args.dry_run:
            conn.execute("ROLLBACK")
        else:
            conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise

    prefix = "would import" if args.dry_run else "imported"
    print(f"{prefix} {tsv_path.name} into {db_path.name}")
    print(
        f"  lexical_items: {counts['inserted']} inserted, "
        f"{counts['updated']} updated, {counts['unchanged']} unchanged"
    )
    print(
        f"  item_state: {scheduled} scheduler rows created for {learner_name!r} "
        f"(id {learner_id})"
    )

    # Report the rows deliberately left out of the due queue, because that
    # number looks like data loss until you know it is a decision. Function
    # words are real reference content, but an English prompt of "the" has three
    # German answers and would record lapses that never happened.
    not_drillable = sum(1 for row in rows if row["drillable"] == "no")
    print(f"  {not_drillable} rows stored as reference only, not scheduled")

    for warning in warnings:
        print(f"  warning: {warning}")

    if args.dry_run:
        print("  (dry run: rolled back, nothing was written)")

    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
