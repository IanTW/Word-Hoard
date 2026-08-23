---
name: deliberate-schema-tradeoffs
description: Three schema choices that look like bugs but were made deliberately; do not refactor them silently
metadata:
  type: project
---

Three things in `schema.sql` look like mistakes a cleanup pass would fix, and
are not:

1. **`item_state.language_code` is denormalized.** It could be derived by
   joining out to the content tables.
2. **`item_state` and `review_log` reference content by a
   `(content_type, content_id)` pair with no foreign keys.** The database
   therefore cannot enforce referential integrity on those columns.
3. **There is one FSRS state per item, not one per (item, exercise type).**
   Recognising a word in multiple choice does not prove it can be typed.

**Why:** (1) `item_state` is read on every app launch to build the due queue, so
that has to stay a fast single-table query. (2) A schedulable thing may be a
lexical item or a sentence or something later, and the scheduler genuinely does
not care which; losing database-level integrity is an accepted trade for a
personal single-user tool. (3) Four independent schedulers per word quadruples
the due queue and becomes hard to reason about; recording `exercise_type` on
each `review_log` row keeps accuracy by modality reportable as a diagnostic
without letting it drive scheduling.

**How to apply:** If one of these looks wrong during implementation, raise it
for discussion rather than changing it. The reasoning is also recorded inline in
`schema.sql` and in `docs/OVERVIEW.md`. See [[fsrs-not-sm2]] and
[[review-log-is-append-only]].
