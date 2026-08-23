---
name: fsrs-not-sm2
description: The scheduler is FSRS with learning steps in front of it, never SM-2, and py-fsrs is preferred over a from-scratch implementation
metadata:
  type: project
---

The spaced repetition scheduler is FSRS. Not SM-2, which is what old Anki and
most homemade SRS tools use. Short fixed learning steps (for example one minute,
then ten minutes) sit **in front of** FSRS as a small state machine, using the
`state` and `step_index` columns on `item_state`. They are not implemented
inside FSRS itself.

**Why:** SM-2 has a single ease number standing in for two quantities that
behave differently. FSRS separates intrinsic difficulty from current memory
stability and predicts recall probability from both, which is what allows
scheduling to aim at a target retention rate. Separately, pure FSRS interval
maths handles brand-new and just-failed items badly, which is why every real
implementation (Anki, RemNote) layers short delays in front of the long-term
schedule.

**How to apply:** Depend on or closely follow `py-fsrs` from the
open-spaced-repetition project rather than reimplementing the algorithm from the
paper. Feed `learner_languages.target_retention` into the scheduler as its
desired-retention parameter; do not hardcode 0.9. Step durations live as a
module constant, not a settings table, unless that is revisited. See
[[review-log-is-append-only]] and [[deliberate-schema-tradeoffs]].
