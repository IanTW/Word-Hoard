# CLAUDE.md

Guidance for Claude Code (claude.ai/code) when working in this repository.

The general rules (session start, response format, punctuation, commits,
commenting, the documentation system, Wrap Up, measurement discipline, the
machine's environment traps, long-running work) live in `~/.claude/CLAUDE.md`
and load in every session. **This file holds only what is specific to this
project**, and where it disagrees with the global file, this file wins.
Trimmed to that on 2026-10-03, from 457 lines, by a change handed down from
claude-admin.

## Project Overview

word-hoard is a personal, self-hosted language learning tool for two people on
one machine, starting with German and adding Dutch only once the core works. It
is a deliberate inversion of Duolingo: it keeps the four learning modes
(typing, reading, listening, speaking) and drops every gamified element, so
there are no streaks, no XP, no mascots and no engagement mechanics anywhere in
scope. There is no authentication; a `learners` row exists only to tell whose
review history is whose.

The authoritative records are `schema.sql` for the database itself,
`docs/OVERVIEW.md` for the architecture and the reasoning behind it,
`docs/TODO.md` for the delivery order, and `language-app-erd.drawio` for the
schema drawn visually. The ERD is reference only and is not generated from
anything; if it disagrees with `schema.sql`, the SQL wins and the ERD is stale.

**The one architectural rule:** nothing under `wordhoard/` imports a web
framework. `wordhoard/` is framework-free domain logic (the scheduler, the
grader, the session rules); `web/` and `scripts/` are the edge and own no rules
of their own. The schema and `review_log` outlive any routing layer, so the
future-proofing lives in the layering rather than in the framework. Verified by
grep at step 6 and worth re-running: no `fastapi`, `uvicorn`, `starlette` or
`jinja2` anywhere under `wordhoard/`. Defend this split when it becomes
inconvenient.

As of 2026-08-29, **the vertical slice is COMPLETE.** All six steps are done:
the SQLite database, 117 hand-checked German entries of which 74 are drillable,
FSRS with library-supplied learning steps, the typing exercise, the review loop
with an introduction pass in front of it, and a server-rendered due-queue
interface. The database was reset after step 6 testing, so `review_log` is
empty and the first real session starts clean.

**Nothing outside the slice exists, and nothing outside it starts until the loop
has been used for real review sessions.** Sentences, grammar concepts, audio,
speech recognition, statistics, a second learner and Dutch are all planned, not
built. Treat every mention of them as design intent rather than live behaviour.
The one exception is the plain-text backup export (`wordhoard/backup.py`,
`scripts/export_backup.py`), built 2026-09-08 as milestone M1 once real review
history existed to protect. The first real session already overturned a design
assumption, which is that rule's argument in one line: 9 Again out of 17 reviews
measured nothing about German and nothing about the grader, only that the app
was demanding words back before it had ever shown them.

**The largest known gap is content volume.** 74 drillable words at the default
10 new per day is about a week of fresh material.

---

## Project conventions

- **Test plans:** every *learner-facing* feature gets a section in
  `docs/TESTPLAN.md`, **written and agreed before any code.** Import scripts,
  refactors, tooling and docs are exempt. A learner-facing feature is anything
  that changes what the learner sees, what counts as correct, what rating
  reaches FSRS, when an item returns, or what is written to `review_log`. The
  append-only log sets the bar: a feature that writes to it needs its plan
  agreed before it runs against the live database, not after.
- `docs/TESTPLAN.md` is the document easiest to blur. It is not a record of
  what was verified, which is what a DEVLOG entry carries; it is the agreement
  about what would count as verified, made before the code exists. The
  retrospective section at the bottom of that file is explicitly labelled as a
  record rather than an example, precisely so the distinction survives.

### Additions to the global rules

Details this project recorded that the global rules do not carry.

- **Run probes with a deliberately naive query set.** A probe that searches for
  what it is trying to find measures nothing.
- **No third estimate.** If two past estimates for a process were wrong by 3x
  or more, say so instead of producing a third. Give the measured range and
  its cause.
- **OVERVIEW bloat is fixed by cutting, not rewording.** Measured once:
  rewording saved about 5%, cutting cross-section duplication saved 25%.

---

## Mechanical checks

The dash and line reference checks are the shared hooks in `~/.claude/hooks/`,
deployed from claude-admin (this project moved onto them 2026-09-16; its own
copies, ported from atc-game 2026-09-07, were retired). This project's
exceptions to them, if any are ever agreed, go in `.claude/kit.json` with a
reason and a date.

**The response format sections are deliberately NOT hooked.** Two of the
format rules are judgement calls, omitting an empty section and dropping the
structure for a short reply, and a hook enforcing headings would push toward
padding an empty section rather than dropping it.

`tools/housekeeping.sh` runs at Wrap Up and reports only. Its project checks
include framework isolation under `wordhoard/` and the venv pins.

---

## Environment

Windows 10 Pro, Python project, developed in VS Code via
`word-hoard.code-workspace`.

**Running it.** Dependencies live in a project venv at `.venv`, created
2026-08-26. Always invoke through it explicitly rather than through a bare
`python`:

```bash
.venv/Scripts/python.exe scripts/serve.py     # browser interface on http://127.0.0.1:8000
.venv/Scripts/python.exe scripts/review.py    # the same review loop in the terminal
.venv/Scripts/python.exe scripts/import_lexical_items.py --dry-run
```

`serve.py` binds to loopback only, deliberately, because the system has no
authentication anywhere by design. FastAPI also serves `/docs` for free, which
is the interface to reach for when checking a route by hand.

**The trap is the interpreter.** A bare `python` on this machine is not the venv,
and the failure is `ModuleNotFoundError: No module named 'fsrs'` in files that
are perfectly correct. Point VS Code at `.venv/Scripts/python.exe`. Reach for
the interpreter before debugging the code.

**Remote:** `origin` is `https://github.com/IanTW/Word-Hoard.git`, branch
`main`. Wrap Up pushes to it. Never force-push.
