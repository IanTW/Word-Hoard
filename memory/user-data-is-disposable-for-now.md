---
name: user-data-is-disposable-for-now
description: Until the user says otherwise, review history in word-hoard.db may be freely reset; testing against the live database is fine and does not need a throwaway copy
metadata:
  type: project
---

Review data in `word-hoard.db` is disposable until the user explicitly says it
is not. Testing against the live database is fine, and resetting it (rebuild
from `schema.sql`, re-import from `data/review/german_draft.tsv`) is a routine
move rather than a destructive one.

**Why:** Stated by the user on 2026-08-29: "I'm not planing on using the
application until it is more substantial so any user data can be treated as
disposable until I say so." They are not studying yet, so nothing in
`review_log` is real learning history.

**How to apply:**

- Do not build throwaway copies or ask permission before writing test reviews
  to `word-hoard.db`. It costs a step and buys nothing right now.
- Do still reset rather than leave junk behind, so the first genuine session
  starts from a clean log.
- **This expires the moment the user starts studying for real.** Watch for them
  saying so, or for a `review_log` that shows sessions spread across many days
  rather than one burst. At that point [[review-log-is-append-only]] becomes
  live in the strongest sense: the log is irreplaceable, resets are off, and a
  false rating written by a test is permanent.
- The content half is always rebuildable regardless, since the TSV is the source
  of truth and the import is a re-runnable transcription. It is only
  `review_log` that has no other copy.

See [[review-log-is-append-only]] and [[vertical-slice-first]].
