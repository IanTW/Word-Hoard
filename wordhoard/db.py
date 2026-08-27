"""Database access for word-hoard.

This module is deliberately free of any web framework. Nothing in `wordhoard/`
imports FastAPI, Flask, or anything else that serves HTTP. The reasoning is that
the schema, the review history and the scheduler are the long-lived assets here,
and the web layer is the most replaceable part of the system. Keeping the
framework out of this package means swapping it later costs a routing layer
rather than a rewrite. See docs/OVERVIEW.md.

Uses the standard library `sqlite3` with no ORM. The schema is already
hand-written SQL in schema.sql; an ORM would only re-describe it in a second
place, and the two would drift.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

# Repository root, derived from this file's location rather than the working
# directory, so scripts work regardless of where they are invoked from.
REPO_ROOT = Path(__file__).resolve().parent.parent

# The authoritative schema definition. Read at database creation time rather
# than duplicated as Python string literals, so there is exactly one definition
# of the tables and it cannot drift.
SCHEMA_PATH = REPO_ROOT / "schema.sql"

# Default location of the live database. Gitignored: the versioned artifact is
# the plain-text export, not this file, because SQLite binaries diff terribly.
DEFAULT_DB_PATH = REPO_ROOT / "word-hoard.db"

# Languages seeded on database creation. 'de' is the language actually being
# built against; 'nl' is present because the schema is multi-language from the
# start and seeding it costs nothing. No Dutch *content* exists or should be
# added until the German vertical slice is working.
SEED_LANGUAGES = [
    ("de", "German"),
    ("nl", "Dutch"),
]


def connect(db_path: Path | str = DEFAULT_DB_PATH) -> sqlite3.Connection:
    """Open a connection to the database with the project's standard settings.

    Every connection in the app should come from here, so the pragmas below are
    applied consistently. SQLite applies foreign key enforcement per connection,
    not per database, so setting it in schema.sql alone would not be enough.
    """
    conn = sqlite3.connect(db_path)

    # Return rows that can be accessed by column name. Worth the negligible cost
    # because the alternative is positional indexing into SELECTs, which breaks
    # silently when a column is added.
    conn.row_factory = sqlite3.Row

    # Foreign key enforcement is OFF by default in SQLite for backwards
    # compatibility, and is a per-connection setting. Note this only protects
    # the real foreign keys; item_state and review_log reference content through
    # a polymorphic (content_type, content_id) pair with no FK by design, so
    # those two columns are not protected here or anywhere else in the database.
    conn.execute("PRAGMA foreign_keys = ON")

    return conn


def create_database(
    db_path: Path | str = DEFAULT_DB_PATH,
    schema_path: Path | str = SCHEMA_PATH,
) -> sqlite3.Connection:
    """Create the database file and apply the schema.

    Refuses to touch an existing file. Re-running against a live database would
    either fail on duplicate CREATE TABLE or, worse, silently succeed against a
    partially built one. Since review_log is irreplaceable (it records months of
    real human review events that cannot be regenerated), this path errs hard
    rather than doing anything clever.
    """
    db_path = Path(db_path)
    if db_path.exists():
        raise FileExistsError(
            f"{db_path} already exists. Refusing to touch an existing database: "
            f"review_log cannot be regenerated if it is lost. Move or delete the "
            f"file by hand if you really mean to start over."
        )

    schema_sql = Path(schema_path).read_text(encoding="utf-8")

    conn = connect(db_path)
    with conn:
        conn.executescript(schema_sql)
    return conn


def seed_languages(conn: sqlite3.Connection) -> int:
    """Insert the reference language rows. Idempotent.

    Returns the number of rows actually inserted, so callers can report honestly
    on a re-run rather than claiming work that did not happen.
    """
    with conn:
        cursor = conn.executemany(
            # OR IGNORE rather than OR REPLACE: languages is static reference
            # data, and a re-run should be a no-op, not a rewrite.
            "INSERT OR IGNORE INTO languages (code, name) VALUES (?, ?)",
            SEED_LANGUAGES,
        )
    return cursor.rowcount


def add_learner(
    conn: sqlite3.Connection,
    display_name: str,
    language_code: str,
) -> int:
    """Create a learner and enrol them in one language. Returns the learner id.

    Learner rows exist solely to keep one person's review history separate from
    another's. There is no authentication anywhere in this system by design.

    daily_new_limit and target_retention are left at their schema defaults (10
    and 0.95). Both are starting guesses rather than measured values and are
    expected to be tuned once real sessions have been run. The retention default
    is deliberately above the FSRS reference value of 0.9; see the comment on
    the column in schema.sql for the measurements behind that.
    """
    with conn:
        cursor = conn.execute(
            "INSERT INTO learners (display_name) VALUES (?)",
            (display_name,),
        )
        learner_id = cursor.lastrowid

        conn.execute(
            "INSERT INTO learner_languages (learner_id, language_code) VALUES (?, ?)",
            (learner_id, language_code),
        )

    return learner_id
