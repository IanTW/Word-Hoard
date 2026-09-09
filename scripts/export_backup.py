"""Export the irreplaceable tables to plain text, loudly.

    .venv/Scripts/python.exe scripts/export_backup.py

The review loop also exports automatically after every answer, quietly, so this
script is not the only thing standing between the learner and a lost history.
It exists for the two cases the quiet path cannot serve: running a backup on
demand before doing something risky, and finding out why the automatic one is
not working. Where `wordhoard.backup.export_quietly` swallows every error by
design, this prints the traceback and exits non-zero.

Read-only with respect to the database.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# The repository root has to be importable before `wordhoard` resolves, since
# this script is run directly rather than as part of an installed package.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from wordhoard import backup, db  # noqa: E402  (must follow the sys.path fix)


def main() -> int:
    """Run the export and report what was written."""
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--db", default=str(db.DEFAULT_DB_PATH),
                        help="Database to export (default: the project database)")
    parser.add_argument("--out", default=None,
                        help="Directory to write the export into. Defaults to "
                             "data/backup for the project database, and to a "
                             "directory beside any other database, so exporting "
                             "a scratch copy cannot overwrite the real backup.")
    args = parser.parse_args()

    db_path = Path(args.db)
    if not db_path.exists():
        print(f"No database at {db_path}", file=sys.stderr)
        return 1

    out_dir = Path(args.out) if args.out else backup.default_backup_dir_for(db_path)
    manifest = backup.export(db_path=db_path, backup_dir=out_dir)

    print(f"Exported from {manifest['source_db']} at {manifest['exported_at']}")
    for table, count in sorted(manifest["counts"].items()):
        print(f"  {count:>6}  {table}")
    print(f"Written to {out_dir.resolve()}")

    # The number worth calling out. An empty review log is normal on a fresh
    # database and alarming on one that has been used, and only the person
    # running this knows which they have.
    if manifest["counts"]["review_log"] == 0:
        print("\nNote: review_log is empty. Expected on a fresh database.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
