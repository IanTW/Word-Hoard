"""Create the word-hoard database and seed the minimum needed to start.

Vertical slice step 1b. Run once:

    python scripts/init_db.py --learner "Ian" --language de

Deliberately a plain script with no web framework involved. Database setup has
nothing to do with how the app is eventually served, and tying the two together
would mean the framework choice blocks work that does not depend on it.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Allow running this file directly (python scripts/init_db.py) without needing
# the package installed or PYTHONPATH set. Keeps the run story to one command.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from wordhoard import db  # noqa: E402  (import must follow the sys.path fix above)


def main() -> int:
    """Parse arguments, create the database, report exactly what happened."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--db",
        default=db.DEFAULT_DB_PATH,
        help=f"Database file to create (default: {db.DEFAULT_DB_PATH.name})",
    )
    parser.add_argument(
        "--learner",
        help="Display name for an initial learner. Optional; learners can be "
             "added later.",
    )
    parser.add_argument(
        "--language",
        default="de",
        help="Language code to enrol the initial learner in (default: de)",
    )
    args = parser.parse_args()

    # Fail loudly rather than touching an existing database. review_log is the
    # one thing in this project that cannot be regenerated.
    try:
        conn = db.create_database(args.db)
    except FileExistsError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    # Report the real counts rather than a generic success message, so a re-run
    # against a fresh file is distinguishable from a no-op.
    table_count = conn.execute(
        "SELECT count(*) FROM sqlite_master WHERE type = 'table'"
    ).fetchone()[0]
    print(f"created {args.db} with {table_count} tables")

    inserted = db.seed_languages(conn)
    print(f"seeded {inserted} languages")

    if args.learner:
        learner_id = db.add_learner(conn, args.learner, args.language)
        print(
            f"added learner {args.learner!r} (id {learner_id}) "
            f"studying {args.language}"
        )
    else:
        print("no learner created; pass --learner NAME to add one")

    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
