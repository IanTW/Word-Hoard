---
name: fsrs-not-sm2
description: The scheduler is FSRS, never SM-2; the fsrs PyPI package (not "py-fsrs") supplies both the algorithm and the learning steps, so do not hand-roll either
metadata:
  type: project
---

The spaced repetition scheduler is FSRS. Not SM-2, which is what old Anki and
most homemade SRS tools use. It is implemented in `wordhoard/scheduler.py` as a
thin translation layer between `item_state` rows and `fsrs.Card` objects.

**Why:** SM-2 has a single ease number standing in for two quantities that
behave differently. FSRS separates intrinsic difficulty from current memory
stability and predicts recall probability from both, which is what allows
scheduling to aim at a target retention rate.

**How to apply:**

- **The PyPI package is `fsrs`, not `py-fsrs`.** `py-fsrs` is the GitHub repo
  name, and `pip install py-fsrs` fails with "no matching distribution found",
  which does not hint at the real name. This cost a failed install on
  2026-08-26.
- **Do not write a learning-steps state machine.** The original design called
  for one in front of FSRS, because pure interval maths handles brand-new and
  just-failed items badly. From version 6 the library does it itself:
  `Scheduler(learning_steps=..., relearning_steps=...)` and `Card.step`.
  Verified against 6.3.2 on 2026-08-26: a fresh card rated Good goes to a ten
  minute step, then graduates to two days; a failed mature card drops to
  Relearning with a ten minute step. Requirements pins `fsrs==6.3.2` with a
  comment saying not to downgrade below 6 without restoring the machine.
- **Step durations are ours, the machine is not.** `LEARNING_STEPS` and
  `RELEARNING_STEPS` are module constants in `wordhoard/scheduler.py`, passed
  into the library. Not a settings table.
- **Feed `learner_languages.target_retention` in as `desired_retention`.** Never
  hardcode a literal. Measured on the same card, retention 0.8 gave a 109 day
  interval, 0.9 gave 32 days and 0.99 gave 2 days, so this column is the single
  biggest lever on daily workload.
- **The default is 0.95, not the FSRS reference 0.9, and the interval ceiling is
  365 days rather than the library's hundred years.** Both changed 2026-08-27.
  At 0.9 with no ceiling, a word answered correctly seven times running is not
  shown again for 1348 days, and over twenty years by the ninth review. FSRS is
  answering its own question correctly there, namely when recall probability
  falls to the target. The point is that **retrievability on demand is not the
  objective for a language somebody intends to speak**, so this project
  deliberately optimises for something other than the fewest possible reviews.
  Do not "restore the FSRS defaults" as a tidying exercise.
- **`item_state.state` carries a fourth value the library has no notion of.**
  `new` means an item that has been imported and scheduled but never reviewed;
  `fsrs.State` has only Learning, Review and Relearning, because a card there
  comes into existence at first review.
- **A lapse is failing a graduated item, not failing during learning.** Getting
  a brand-new word wrong on its second minute is the process working.

The general lesson, which cost a redesign here: a dependency's feature set is a
fact to check at the moment of use, not to inherit from whatever was true when
the design was written.

See [[review-log-is-append-only]] and [[deliberate-schema-tradeoffs]].
