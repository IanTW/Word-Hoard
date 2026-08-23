---
name: plain-text-backup-not-db-file
description: The versioned backup artifact is a newline-delimited JSON export, never the live SQLite .db file
metadata:
  type: project
---

The live `.db` file is not versioned and is gitignored. Backups are a periodic
export of `review_log` and `item_state` to newline-delimited JSON, and that
export is what goes into the repository.

**Why:** SQLite files diff terribly. A small logical change rewrites large
stretches of the binary, so committing the database would produce a large
history that tells a reader nothing. Newline-delimited JSON is small, diffs
cleanly, is human-inspectable, and can be reconstructed back into SQLite.

**How to apply:** Keep `*.db` in `.gitignore`. Build the export job as the first
task after the vertical slice works, not before. If the export outgrows git,
move it to cloud backup rather than switching to versioning the database. See
[[review-log-is-append-only]] and [[vertical-slice-first]].
