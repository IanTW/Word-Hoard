---
name: learner-cannot-verify-target-language
description: The user does not speak German or Dutch, so cannot check generated content for correctness; make machine-checkable claims machine-checked and surface every change for review
metadata:
  type: project
---

The user is learning German from scratch and does not speak it. The same will be
true of Dutch. When Claude drafts or corrects target-language content, the user
cannot tell a right answer from a confident wrong one.

**Why:** Stated directly by the user on 2026-08-23, when approving a drafted
vocabulary batch: "theres always a danger of getting it wrong since I don't
speak German". Wrong content here is unusually expensive. A wrong gender or a
wrong translation gets drilled until it is memorised, and `review_log` is
append-only, so the false reviews it generates stay in the history that FSRS
refits its parameters against.

**How to apply:**

- Never present drafted target-language content as simply correct. Show what was
  changed from the source and why, in a column or a list, so review can target
  the changes rather than requiring a full re-read.
- Check mechanically everything that can be checked mechanically: column counts,
  duplicate lemmas, missing translations, nouns without gender. The human review
  can then spend its attention on the part only a speaker can judge.
- Flag rather than silently auto-correct. A silent fix that is wrong is worse
  than an unfixed error, because nobody looks at it again.
- A verify/validate cycle for checking generated content against an independent
  source is agreed in principle and deferred. It is on `docs/TODO.md`. Raise it
  before any large content generation run, not after.

See [[review-log-is-append-only]] and [[vertical-slice-first]].
