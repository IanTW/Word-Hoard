---
name: review-log-is-append-only
description: review_log rows are never updated or deleted, because FSRS parameter refitting needs the raw history
metadata:
  type: project
---

`review_log` is append-only. Rows are never updated and never deleted, and each
row records the scheduler inputs as they stood *before* that review was applied
(`stability_before`, `difficulty_before`, `elapsed_days`, `scheduled_days`).

**Why:** The main payoff of choosing FSRS is that its parameters can be refit to
an individual learner's real review history, turning a generic scheduler into a
personal one. That refit is impossible if reviews overwrite each other, and
storing only the after-state would make the log unreplayable. `item_state`
answers "what is due now" and `review_log` answers "how has this person actually
been performing"; they are separate tables because they are queried in
completely different ways.

**How to apply:** Never write an UPDATE or DELETE against `review_log`. If a
review needs correcting, that is a new row, not an edit. Treat any request to
prune the log as a change that would cost the parameter refitting, and say so.
See [[fsrs-not-sm2]] and [[plain-text-backup-not-db-file]].
