---
name: vertical-slice-first
description: Nothing outside the six-step vertical slice gets built until step 6 works and has real usage behind it
metadata:
  type: project
---

The agreed build order is one working slice end to end before scope widens in
any direction: create the database, hand-enter a few dozen German words, build
FSRS plus learning steps, build the typing exercise, wire it to the scheduler,
then a minimal due-queue interface. Full list in `docs/TODO.md`.

Do not start on sentences, grammar concepts, additional exercise types, audio,
speech recognition, statistics views, a second learner, or Dutch until step 6
works and has been used for real review sessions.

**Why:** The risk in a project like this is building four exercise types, a
content pipeline and a multi-language abstraction before discovering the core
loop is wrong. Typing was chosen as the first exercise specifically because it
is a stronger recall signal than multiple choice and needs no audio pipeline or
ASR to get started.

**How to apply:** When a task would touch anything outside the slice, say it is
out of scope and why, rather than doing it as a small extra. The one exception
already agreed: the plain-text export comes first after step 6. Also do not
build a per-language processing abstraction until Dutch content actually exists,
because the points of variation cannot be seen from one language. See
[[no-gamification]].
