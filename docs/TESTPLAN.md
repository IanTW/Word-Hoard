# Test plan

Every learner-facing feature gets a section here, **written and agreed before
any code is written for it.** Adopted 2026-09-07, ported from the atc-game
project on this machine.

## Why this file exists

The project already verifies things carefully. What it has not had is a place
where the verification is decided *before* the work, and a place where it
survives afterwards. Until now the record lived in `docs/TODO.md` bullets, which
is the wrong home for two reasons: a TODO item is closed and eventually archived,
so the evidence leaves with it, and a check invented after the code is written
tends to check what the code happens to do.

There is a second, sharper reason here. The person building this does not speak
German. Anything a speaker would catch by reading has to be caught by a check
instead, and the checks have to be decided while the feature is still an idea.

## What needs a plan, and what does not

**Needs a plan:** anything that changes what the learner sees, what counts as a
correct answer, what rating reaches FSRS, when an item comes back, or what gets
written to `review_log`. Exercise types, the grader, the scheduler, the session
rules, the interface.

**Exempt:** import and drafting scripts, refactors, tooling, documentation, and
anything under `.claude/`. These are checked by running them, not by a plan.

**The append-only rule sets the bar.** `review_log` cannot be corrected later,
so a feature that writes to it needs its plan agreed before it runs against the
live database, not after.

## Template

```
## <feature name>

**Status:** planned | agreed | built | verified
**Agreed:** YYYY-MM-DD

**What it must do:**
- ...

**What would make it wrong:**
- ...

**Checks, and what each one would catch:**
| Check | Catches | Result |
|---|---|---|
| ... | ... | pending |

**What this plan cannot check:**
- ...
```

The last section is not optional padding. Precision and recall are computed over
what you already hold, and say nothing about what was never ingested, so a plan
that does not name its blind spot is claiming a coverage it does not have.

---

# Retrospective record

Everything below was **verified after the code was written, not planned before
it.** It is recorded here so the evidence has a permanent home rather than
sitting in TODO items that will eventually be archived. Read it as a record, not
as an example of the convention being followed. The convention starts with the
next feature.

## Typing exercise: grading

**Status:** verified (2026-08-27)

**Checks and results:**

| Check | Catches | Result |
|---|---|---|
| 24 case table over determiners, capitalisation, transliteration, whitespace, verbs, adjectives, phrases | grader disagreeing with the intended rules | 24 of 24 as expected |
| `expected_answer()` is the only place the `answer_form` fallback lives | two surfaces drifting on what the right answer is | single definition confirmed |
| `ae`, `oe`, `ue`, `ss` folded on both sides | `Baeckerei` must pass, `Backerei` must not | both as specified, affects 10 of 74 answers |

**Ratings, settled by measurement on a mature item** (stability 90 days,
retention 0.9, fuzzing off):

| Rating | Resulting stability | Next interval |
|---|---|---|
| Again (1) | 3.6 | 10 minutes |
| Hard (2) | 172.7 | 173 days |
| Good (3) | 227.5 | 227 days |

That table is the whole argument for a wrong determiner being Again rather than
Hard. Hard is a near miss of Good, not a middle course.

**What this did not check:** whether the German content being graded is correct.
The grader can only compare against what the TSV says, so a wrong gender in the
source passes every check here and is drilled until memorised.

## Scheduler

**Status:** verified (2026-08-26, ceiling added 2026-08-27)

| Check | Catches | Result |
|---|---|---|
| Walk a new item through its steps | learning steps not reaching the library | 10 minutes, then 2, 14, 49 days |
| Fail a graduated item, then one still in learning | lapses counted on the wrong transition | graduated increments `lapses`, in-learning does not |
| Vary `target_retention` on one identical card | the column not reaching the scheduler | 0.80 gives 109 days, 0.90 gives 32, 0.99 gives 2 |
| Ladder under the 365 day ceiling at retention 0.95 | runaway intervals | 1, 3, 8, 19, 43, 89, 175, 325, cap met on the 10th review |
| `review_log` shape after 6 reviews | before-state written on a first review | NULL first, real elapsed and scheduled days after |

**What this did not check:** whether 0.95 and 365 are the right values. Both are
starting values, not measured ones, and cannot be measured until `review_log`
holds enough real history to support a parameter fit.

## Review loop and the introduction pass

**Status:** verified (2026-08-29)

| Check | Catches | Result |
|---|---|---|
| One log row per introduction, however many retries | retries polluting an append-only log | confirmed, retries write nothing |
| Quit mid-introduction | an untaught item recorded as taught | item stays `new`, taught properly next session |
| An introduced item's next encounter | teaching the same item twice | comes back as a test |
| `--limit`, `:q`, and EOF | a session ending losing answered work | everything already answered is kept |

**Found by real use, not by a check:** 9 Again out of 17 reviews on the first
session. Every one was an item the app had never shown. No planned check would
have caught it, because every component was behaving exactly as specified. This
is the strongest argument in the project for using a thing before widening it.

## Web interface

**Status:** verified (2026-08-29)

| Check | Catches | Result |
|---|---|---|
| Refresh the feedback URL five times | a stray reload writing a second row to an append-only log | `review_log` unchanged, post then redirect then get holds |
| Introduction renders for a new item, test for a seen one | the two surfaces disagreeing about item state | correct in both cases |
| Transliterated umlauts through the browser | encoding lost at the form boundary | accepted |
| grep for `fastapi`, `uvicorn`, `starlette`, `jinja2` under `wordhoard/` | the framework leaking out of the edge | 0 hits, re-confirmed 2026-09-07 |

**What this did not check:** anything about leaving a session, because the web
interface has no notion of one. Open as TODO 6b.

---

# Planned

## M2a: finish a session, and go again

**Status:** verified. Agreed 2026-09-10 before any code, built and verified the
same day, 22 of 22 checks against a scratch copy.
**Raised:** 2026-09-10, by the first real use of the app. The request was "could
do with a restart button if I want to go again and a quit button". This is the
gate working: the rule that nothing widens until the loop has real use behind it
existed to produce exactly this kind of feedback rather than a guess.

Closes TODO 6b, which has been open since step 6 and said the browser has no way
to leave a session because it has no notion of one.

**What it must do:**

- Give the browser a **notion of a session**: a start, an end, and a summary.
  The terminal already has one through `:q`; the browser has never had one.
- **Finish** ends the session and shows what happened: answered, learned, the
  rating tally, and when the next item is due. The server keeps running.
- **Go again** starts a fresh session. When items are due it simply continues.
  **When nothing is due it grants one more daily allowance of new words**, so
  the learner can keep going rather than stare at a countdown.
- Every number in the summary is **derived from `review_log`**, not from a
  counter kept alongside it. A summary that can disagree with the history is
  worse than no summary.
- Nothing in the summary is a streak, a score, an accuracy percentage over time,
  a record or a word of encouragement. See `memory/no-gamification.md`. This is
  the screen where gamification gets reinvented by accident.

**Decisions taken, with reasons:**

- **An extra allowance is one daily limit (10 by default), not an unlimited
  cap.** Lifting the cap entirely would let 60 unseen words be introduced in one
  sitting, and FSRS would return every one of them over the following days. The
  learner would be punished tomorrow for enthusiasm today, by a mechanism they
  cannot see while pressing the button. A bounded grant is explainable, repeats
  if they want more, and matches a setting that already exists.
- **The allowance is granted only when nothing is due.** That is exactly what
  was asked for. Granting it unconditionally would quietly inflate the daily new
  count on ordinary sessions.
- **Session state lives in the web layer, not in `wordhoard/`.** It is presentation
  state for one browser on one machine. Nothing in the domain layer should learn
  what a browser session is.
- **The summary derives from `review_log` by timestamp**, so losing the session
  state to a server restart costs only the "since" marker, never a number.
- **There is no Close button.** Server-rendered HTML cannot close a browser tab,
  and `window.close()` only works on windows a script opened. The summary page
  is the stopping point; closing the tab is the natural action and needs no
  control. Flagged because the agreed mockup showed one.

**What would make it wrong:**

- A summary whose counts disagree with `review_log`.
- Finish writing anything. It is a read, and it must stay a read.
- Go again granting an allowance when items were due anyway, inflating the
  daily new count.
- An allowance that persists past the session, so the cap is permanently gone.
- Refreshing the summary, or pressing back into it, changing anything.
- The extra allowance leaking into the terminal runner, which did not ask for it.

**Checks, and what each one would catch:**

| Check | Catches | Result |
|---|---|---|
| Answer a known number of items, finish, compare the summary against a direct `review_log` query | a summary that invents its numbers | PASS, answered and introduced both matched, tally sums to answered |
| `PRAGMA quick_check` and row counts before and after pressing Finish | Finish writing something | PASS, 16 rows before and after, quick_check ok |
| Refresh the summary five times, then press back into it | a stray reload changing state | PASS, five renders wrote nothing |
| Go again with items due, then check `introduced_today` | an allowance granted when it was not needed | PASS, no allowance granted |
| Go again with nothing due, count new items offered | the grant not working, or being unbounded | PASS, exactly 10 offered |
| Press Go again three times, confirm at most one allowance is available at once | an allowance that compounds silently | **PASS after a fix. This check found a real bug.** See below |
| Start a new session the next day, check the cap is back to 10 | a permanently lifted cap | PASS, 10 new offered tomorrow with no leftover |
| Confirm `scripts/review.py` never passes `extra_new_allowance` | the extra leaking into the terminal | PASS, only `web/app.py` passes it |
| Grep the RENDERED summary for streak, score, percentage, praise | gamification arriving through the back door | PASS, after the check itself was rewritten. See below |
| Finish with zero answers | a summary that only works on the happy path | PASS, renders "Nothing answered this session" |

**The bug this plan caught, which is the reason the plan exists.** The first
version of `/again` asked "is anything due?" using the allowance the session
already held. That conflated two different questions: whether there is work
under the ordinary daily rules, and whether a previous grant is still unspent.
The consequence was that pressing Go again twice **revoked the allowance it had
just given**: a new word appeared, and pressing the button again made it vanish.
The check now asks the question with no allowance at all.

The same fix exposed a second, quieter problem. Setting the extra to a flat 10
works once and then silently does nothing, because `introduced_today` has grown
past the raised cap and `remaining` falls back to zero. The extra is now set to
`introduced_today`, which makes the scheduler's arithmetic come out at exactly
one daily allowance however many words have already been learned today.

**A check that was wrong rather than a feature that was.** The gamification grep
read the template source and flagged "recorded" for containing "record", and a
`strftime` format string for containing "%". Both were false positives from a
lazy substring test against text the learner never sees. It now greps the
rendered page and looks for a percentage as a digit followed by a percent sign.

**Verified in production the same day, unplanned:** the user's first real
session recorded 10 introductions, and `data/backup/review_log.ndjson` came out
holding exactly 10 rows. M1's per-answer export works on real use, not only on
scratch copies.

**What this plan cannot check:**

- Whether the extra-allowance button is a good idea for learning. It trades a
  better session today against a heavier queue tomorrow, and only weeks of use
  can say whether that trade is worth it. Watch for review days that feel
  punishing after a session where the button was pressed.
- Whether one daily allowance per press is the right grant size. It is a
  defensible unit, not a measured one.

---

## M1: plain-text backup export

**Status:** verified
**Agreed:** 2026-09-08, before any code. **Verified:** 2026-09-08, 15 of 15
checks, against scratch copies rather than the live database.

**Note on scope.** By the rule at the top of this file the export is **exempt**:
it is tooling, it reads rather than writes, and it changes nothing the learner
sees. A section was written anyway, because the thing it protects cannot be
recreated and because the characteristic failure of a backup is that it appears
to work. Exempt means not required, not forbidden.

**What it must do:**

- Write `review_log` and `item_state` as newline-delimited JSON, one row per
  line, sorted deterministically so the file diffs cleanly in git.
- Carry a natural key alongside every polymorphic `(content_type, content_id)`
  pair, so a restore does not depend on autoincrement ids landing the same way.
- Include the learner and language rows needed to make sense of the above.
- Be committed to git. `*.db` is gitignored, so this file **is** the versioned
  artifact. That is the whole point of the format.
- Run without touching the database it reads. Read-only, always.
- Never break a review. A failed export must not fail the answer that triggered
  it.

**What would make it wrong:**

- A partial file that looks complete, for instance if the process dies mid-write
  and leaves a truncated last line that still parses as JSON up to that point.
- Silent loss of a row, especially the most recent, which is the one a backup
  exists to save.
- Row order that changes between runs with identical data, which would produce
  a spurious git diff on every export and train the reader to ignore diffs.
- An id-based restore that silently misattributes history to the wrong word.
- An exception in the export path that costs the learner an answer.

**Checks, and what each one would catch:**

| Check | Catches | Result |
|---|---|---|
| Export a database with known counts, count the lines | rows dropped | PASS, 74 item_state and 1 learner matched exactly |
| Export twice with no change, diff the files | nondeterministic ordering | PASS, byte identical |
| Parse every line as JSON | truncation, encoding damage | PASS, every line parsed |
| Compare each `content_key` against the item it points at | id and natural key disagreeing | PASS, 0 mismatches |
| Answer one review, re-export, diff | the newest row missing | PASS, log grew 0 to 1, key `lexical_item:de:sein` |
| Point the exporter at a directory it cannot write, then answer a review | a backup failure costing an answer | PASS, loud path raises, quiet path returns None, answer still 303 |
| Round trip: export, rebuild the database, restore, compare | a restore that does not restore | PASS, every row restored against reassigned ids |
| `PRAGMA quick_check` on the source before and after | the export mutating what it reads | PASS, ok both times, counts unchanged |
| Umlauts and eszett survive the round trip | encoding lost at the file boundary | PASS, lemmas appear verbatim |

**Two checks the plan did not anticipate, added during the build:**

| Check | Catches | Result |
|---|---|---|
| Review a scratch database, then inspect `data/backup/` | a test run overwriting the real backup | PASS, after a fix. See below |
| Run the wiring suite three times | flakiness in the automatic trigger | 14 of 14, three times |

**A defect the plan found by being written down.** Wiring the automatic export
into `scripts/review.py` exposed that `review.py --db scratch.db` would have run
a session against a throwaway database and then written its contents over
`data/backup/`, silently replacing the real backup with test data. Fixed by
deriving the output directory from the database path
(`backup.default_backup_dir_for`), so the project database exports to
`data/backup/` and anything else exports beside itself. The possibility is
removed rather than warned about.

**One failure that did not reproduce, recorded rather than swept up.** On the
first run of the wiring suite, the web route's backup call produced an empty
output directory: the directory was created, the files were not, and
`export_quietly` had swallowed whatever went wrong. Three subsequent runs of the
identical production path passed 14 of 14, and a direct call to `export_quietly`
with the same arguments succeeded. **The cause was not established.** It is
recorded here because a backup that fails once and then works is exactly the
shape of a problem worth remembering, and because `export_quietly` swallowing
the reason is the design decision that made it hard to see. If it recurs, the
first move is `scripts/export_backup.py`, which is loud.

**What this plan cannot check:**

- That the backup is kept anywhere other than this machine. An export sitting in
  the same directory as the database it protects survives a corrupt file, not a
  lost disk. Off-machine copies are what git push provides, and only for
  material that has been committed and pushed.
- Whether the restore path works against a schema that has since changed. The
  round trip check uses today's schema on both sides.
