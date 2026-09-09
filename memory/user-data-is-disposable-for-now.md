---
name: user-data-is-disposable-for-now
description: EXPIRED 2026-09-08. Review history in word-hoard.db is now real and must never be reset; the file name is kept so older links still resolve
metadata:
  type: project
---

**This memory has expired, on the condition it named for itself.** It is kept
rather than deleted because other memories and documents link to it by name, and
because the reversal is the fact worth carrying.

**What it used to say:** review data in `word-hoard.db` was disposable. Testing
against the live database was fine, and resetting it (rebuild from `schema.sql`,
re-import from `data/review/german_draft.tsv`) was a routine move rather than a
destructive one. Stated by the user on 2026-08-29: "I'm not planing on using the
application until it is more substantial so any user data can be treated as
disposable until I say so."

**What is true now.** On 2026-09-08 the user said they will start using the
application. The old note named exactly this trigger and said the rule expires
the moment it fires. It has fired.

**How to apply, from 2026-09-08:**

- **Never reset `word-hoard.db`. Never delete or rewrite rows in `review_log`.**
  [[review-log-is-append-only]] is now live in its strongest sense: the log is
  irreplaceable, and a false rating written by a test is permanent.
- **Do not write test reviews to the live database.** Use a scratch copy. This
  is the exact opposite of the previous instruction, which said not to bother
  with scratch copies.
- Ask before anything that touches the database file, even when the change looks
  additive.
- The content half is still rebuildable, since the TSV is the source of truth
  and the import is a re-runnable transcription. It is only `review_log` and the
  scheduling state in `item_state` that have no other copy.
- **There is still no backup.** The database file is gitignored and the
  plain-text export is not built. That is M1 in the delivery plan in
  `docs/TODO.md`, and it is urgent for this reason rather than for tidiness.

**Why the reversal is worth keeping rather than overwriting.** The original note
wrote down the condition that would invalidate it, and that is what made the
expiry detectable at all. A standing rule with no stated expiry would have
quietly stayed in force and authorised a reset of real learning history. Write
the expiry condition into any memory that depends on a phase of the project.

See [[review-log-is-append-only]], [[vertical-slice-first]] and
[[learner-cannot-verify-target-language]].
