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
