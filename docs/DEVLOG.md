# DEVLOG

Dated session narrative, newest first. Entries are appended during Wrap Up.

The entries for 2026-08-24, 08-26, 08-27 and 08-29 were reconstructed on
2026-09-07 from commit messages, `docs/TODO.md` and the working tree, because
those four sessions ended without a Wrap Up. They are marked as reconstructed
individually. Everything in them is traceable to a commit or a file; nothing is
recalled from a session that was not recorded at the time.

The entries for 2026-09-08 and 2026-09-10 were reconstructed the same way on
2026-09-16, from commits `3f10919` and `8fac450`, the uncommitted working tree,
`docs/TESTPLAN.md` and `docs/TODO.md`, after the housekeeping check flagged the
DEVLOG as older than the newest commit.

## 2026-09-10: Finish and Go again, and the dictionary source chosen by probe (M2a, M3 leg 1)

**Reconstructed:** _written 2026-09-16 from the uncommitted working tree,
`docs/TESTPLAN.md` (section M2a) and `docs/TODO.md` (M2 and M3). Not written
contemporaneously._

**Focus:** _Answer the first request from real use, a way to stop and a way to
go again, then choose the dictionary source for content verification._

**Worked on:**

- The first real session asked for it: "could do with a restart button if I want
  to go again and a quit button". Closes TODO 6b, open since step 6.
- `GET /finish` renders `web/templates/finished.html`: answered, learned, the
  good/nearly/again tally, and when the next item is due. A read; it writes
  nothing.
- `POST /again` starts a new session. When nothing is due it grants exactly one
  further daily allowance of new words.
- `session.summarise` in `wordhoard/session.py` reads every number out of
  `review_log` by timestamp. Introductions are counted apart from answers.
- `scheduler.due_queue` and `session.next_question` gained an
  `extra_new_allowance` argument, default 0. Only `web/app.py` passes it.
- Session state is a module dict in `web/app.py`. Nothing in `wordhoard/`
  learns what a browser session is.
- M3 leg 1: German Wiktionary's live API chosen over the kaikki.org dump.

**Measurements worth keeping:**

- M2a: **22 of 22** plan checks passed against a scratch copy.
- The user's first real session recorded 10 introductions and
  `data/backup/review_log.ndjson` held exactly 10 rows. The per-answer export
  works on real use. The backup now holds 22 `review_log` rows, exported
  2026-09-10 13:33 UTC.
- kaikki.org German dump: **1027 MB**. Live API: all 45 nouns in **2 calls**,
  about 30 calls for the 1300 word target.
- Probe over all 45 gendered nouns, id order: 45 found, 42 parsed, **42 of 42
  agree**. The 3 unparsed are the articles `der`, `die`, `das`.
- Corrupted 20 genders on purpose: caught **20 of 20**.
- Dutch ground truth recorded 2026-08-23 (`brood`, `kind`, `meisje`): found **3
  of 3**.

**Troubleshooting / dead ends:**

- **Go again revoked its own grant.** The first `/again` asked "is anything
  due?" with the current allowance included. Pressing it twice made a new word
  appear and then vanish. Fixed by asking with no allowance. Caught by the
  plan's "not cumulative" check, which is the argument for writing the plan
  first.
- **A flat grant of 10 worked once, then did nothing.** `introduced_today` had
  grown past the raised cap, so `remaining` fell to zero. The extra is now set
  to `introduced_today`, which always leaves exactly one daily allowance.
- **The no-gamification grep was wrong, not the page.** It read the template
  source and flagged "recorded" (contains "record") and a `strftime` "%". It now
  greps the rendered page and looks for a digit followed by a percent sign.
- **No Close button**, though the agreed mockup had one. `window.close()` only
  closes windows a script opened. The summary page is the stopping point.
- **The probe script was never saved to the repository.** It lived in a session
  scratchpad, and on 2026-09-16 every scratchpad folder for this project was
  empty. The TODO line that said "reuse the probe" is corrected.

**Decisions:**

- Grant one daily allowance, not an unlimited cap: 60 unseen words in one
  sitting would all come back over the following days.
- Grant only when nothing is due, so ordinary sessions do not inflate the daily
  new count.
- Summary from `review_log`, not a counter, so it cannot disagree with history
  and a server restart loses only the session boundary.
- Live API over the bulk dump: one field per word does not justify a 1 GB file.
- The 42 of 42 figure is a census of hand-corrected content, not an estimate for
  generated content, and says nothing about translations.

**Next:**

- Commit this work. It had sat uncommitted for six days, including the backup of
  real review history.
- Watch for a punishing review day after using Go again.
- M3: rebuild the Wiktionary check under `wordhoard/`, with a cache.

## 2026-09-08: Conventions ported from atc-game, backup export built, work after the slice planned (M1)

**Reconstructed:** _written 2026-09-16 from commits `3f10919` and `8fac450`
(both committed 2026-09-09), `docs/TESTPLAN.md` and `docs/TODO.md`. The work
spans 2026-09-07 to 2026-09-09. Not written contemporaneously._

**Focus:** _Bring over the no-dashes hooks, test plans and housekeeping from
atc-game, then protect `review_log` before real studying starts._

**Worked on:**

- `.claude/hooks/no_dashes_response.ps1` (Stop) and `no_dashes_file.ps1`
  (PostToolUse on Write and Edit), registered in `.claude/settings.json`.
- `docs/TESTPLAN.md` with the rule that learner-facing features get a section
  agreed before code. `docs/HOUSEKEEPING.md` and `tools/housekeeping.sh`.
- 34 closed TODO items archived verbatim, verified byte-identical.
- CLAUDE.md overview corrected: it still said the slice was just starting.
- The user confirmed they will now study with the app. That expired
  `memory/user-data-is-disposable-for-now.md`, which was inverted, not deleted.
- `wordhoard/backup.py` and `scripts/export_backup.py` write `review_log`,
  `item_state` and the learner rows as newline-delimited JSON into the committed
  `data/backup/`. Every row carries a `content_key` natural key beside its id.
- The browser exports after every answer; the terminal at session end. Both
  through `export_quietly`, which never raises.
- `docs/TODO.md` rewritten from six placeholder lines into milestones M1 to M8.
  M3 approach (dictionary plus model auditor) and M4 target (600, then 1300)
  agreed.

**Measurements worth keeping:**

- A script whose only statement is `exit 2` returns 1 through
  `powershell -Command` and 2 through `-File`.
- M1: 15 checks agreed before code, all passed on scratch copies. Automatic
  triggers passed 14 of 14 on three consecutive runs.
- Dash sweep of every tracked file: zero dashes, which is why the file hook
  covers `.py`, `.sql` and `.html` as well as `.md` and `.txt`.

**Troubleshooting / dead ends:**

- **The dash hook passed exactly what it exists to catch.** `[Console]::In`
  decoded stdin with the console codepage, so an em dash became three unrelated
  characters. Fixed with an explicit UTF-8 `StreamReader`.
- **The block never landed.** `-Command "& script.ps1"` turns exit 2 into exit
  1. Registered in exec form with `-File`. Both defects remain in atc-game.
- **The housekeeping check's first run found a bug in itself.** Plain
  `git ls-files` skipped three new untracked files and reported clean.
- **`review.py --db scratch.db` would have overwritten the real backup** with a
  throwaway database. The output directory now derives from the database path.
- **One trigger check failed once and never again** in three reruns. Cause not
  established; recorded in the test plan rather than swept up.

**Decisions:**

- Backup is the versioned artifact because `*.db` is gitignored and a binary
  file diffs to nothing.
- Natural keys because autoincrement ids match a rebuilt database by
  coincidence, not by guarantee.
- Atomic write through a temp file, `fsync` and `os.replace`, so a crash cannot
  leave a shorter file that still parses line by line.
- A backup failure must never cost the learner an answer.

**Next:**

- Start real use. Then M2 (daily comfort) or M3 (content verification).
- Open: the backup sits on the same disk until someone commits and pushes.

## 2026-08-29: The review loop closes and the slice is finished (steps 5 and 6)

**Reconstructed:** _written 2026-09-07 from commits `f067e74` and `8a65fc3`,
`docs/TODO.md` and the working tree. Not written contemporaneously._

**Focus:** _Join the scheduler, the content and the grader into one review loop,
then put a browser interface on it and close the vertical slice._

**Worked on:**

- `wordhoard/session.py` holds the rules that join scheduling, content and
  grading. `scripts/review.py` holds only terminal input and output. The split
  exists so step 6 could reuse the rules rather than restate them.
- The polymorphic `(content_type, content_id)` pair is resolved back to real
  content in one dispatch table in `session.py`. Making sentences schedulable
  later is one entry in that table.
- `find_learner` moved from `scripts/import_lexical_items.py` into
  `wordhoard/db.py`, because a second script needed it and one definition is
  the rule.
- Step 6: `web/app.py` serves two routes (show what is due, record an answer)
  through one Jinja template. Server-rendered, no JavaScript. `scripts/serve.py`
  starts it bound to loopback only, since the system has no authentication
  anywhere by design.
- `requirements.txt` re-pinned from a real `pip freeze`, with the web packages
  grouped and marked edge-only.
- The live database was reset after step 6 testing, so the first real session
  starts from an empty `review_log`.

**Measurements worth keeping:**

- The first real terminal session recorded **9 Again out of 17 reviews**, 53%.
  See the dead ends below for why that number measures nothing.
- Database after the rebuild and re-import: 117 items, 74 scheduler rows, 0
  reviews, `target_retention` 0.95 inherited from the schema default rather
  than set by hand.
- Post-then-redirect-then-get: five refreshes of the feedback URL left
  `review_log` unchanged.
- Framework isolation by grep: 0 hits for `fastapi`, `uvicorn`, `starlette` or
  `jinja2` anywhere under `wordhoard/`.
- `/docs` returns 200, free with FastAPI, which was the reason it was chosen.

**Troubleshooting / dead ends:**

- **The 53% Again rate exposed a design gap, not a grading bug, and not
  anything about German.** Every one of those nine items was being demanded
  back by an app that had never once shown it. A scheduler schedules the
  *review* of something already learned, and nothing in the system was doing
  the learning. The number is worth keeping precisely because it looked like a
  content or grader problem and was neither.
- **`python-multipart` is required, not optional.** Without it every
  `Form(...)` parameter raises at import time, and the error text does not
  mention forms, so the traceback points nowhere useful. Pinned explicitly with
  a comment saying so.

**Decisions:**

- **New items are introduced before they are tested.** The answer is shown, the
  learner copies it, and every encounter after the first is a real test.
  Recorded as `exercise_type = 'introduction'` at a fixed rating of 3, because a
  typo copied off the screen is not evidence about memory. Retries write
  nothing. Quitting mid-introduction leaves the item `new`, so it is taught
  properly next session. This is exactly what leaving `exercise_type`
  unconstrained was for.
- **The database was reset rather than left carrying nine false lapses.**
  `review_log` is append-only and FSRS later fits parameters against it, so a
  lapse that never happened would have been permanent input to the algorithm.
  Rebuilt from `schema.sql`, re-imported from the TSV. The discarded copy went
  to a session scratchpad, not into the repository.
- **Answering is post-then-redirect-then-get**, so a stray browser refresh
  cannot write a second row into an append-only log.
- **`_describe_interval` is left duplicated** between `scripts/review.py` and
  `web/app.py`. It is presentation, and the two surfaces are entitled to word
  things differently. Logged as TODO 6a rather than fixed, as a marker not a
  defect.
- Review data is disposable until the user says otherwise. Recorded as
  `memory/user-data-is-disposable-for-now.md`, with an explicit expiry
  condition: it lapses the moment real studying starts.

**Next:**

- Use the loop for real review sessions. That is the only thing gating
  everything under "After the slice works".
- The web interface has no way to leave a session, because it has no notion of
  one. The terminal runner has `:q`. TODO 6b, decide after real use.
- Content volume is the largest known gap: 74 drillable words at 10 new a day
  is about a week of fresh material.
- 4a-ii stays open. The grader never produces Easy, because a typing exercise
  cannot observe effort. If that grates, the fix is an explicit control in the
  interface, not an inference in the grader.

## 2026-08-27: Typing exercise, Hard settled by measurement, runaway intervals capped

**Reconstructed:** _written 2026-09-07 from commit `1e9cafe` and `docs/TODO.md`.
Not written contemporaneously._

**Focus:** _Build the grader for the typing exercise, then settle the grading
questions deferred from step 4._

**Worked on:**

- `wordhoard/exercises.py` grades a typed answer against a content item. The
  `answer_form` fallback lives in `expected_answer()` and nowhere else, which
  was the explicit requirement of step 4.
- Verified by a 24 case table covering determiner errors, capitalisation,
  transliteration, whitespace, verbs, adjectives and phrases. 24 of 24 as
  expected.
- `target_retention` default raised from 0.9 to 0.95 in `schema.sql` and set on
  the live row.
- `MAXIMUM_INTERVAL_DAYS` capped at 365 in `wordhoard/scheduler.py`.

**Measurements worth keeping:**

4a-i, measured on one mature item (stability 90 days, retention 0.9, fuzzing
off):

| Rating | Resulting stability | Next interval |
|---|---|---|
| Again (1) | 3.6 | 10 minutes |
| Hard (2) | 172.7 | 173 days |
| Good (3) | 227.5 | 227 days |

Uncapped ladder at retention 0.9, every answer correct: 5th review 163 days
out, 6th 498, **7th 1348**, and past twenty years by the 9th.

Capped ladder at retention 0.95 with the 365 day ceiling: 1, 3, 8, 19, 43, 89,
175, 325 days, meeting the cap on the 10th review. Costs roughly 1.5x the
reviews.

Umlaut and eszett transliteration affects 10 of the 74 drillable answers.

**Troubleshooting / dead ends:**

- **Hard is not a middle course, and the first recommendation was wrong.** The
  intuition was that a right-word-wrong-gender answer sits between wrong and
  right, so it should be Hard. The table above kills that: Hard returns the item
  in 173 days against Good's 227. Rating a gender error Hard would tell the
  learner about it and then effectively never drill it again. Corrected against
  my own recommendation, by measurement rather than argument.
- **A 227 day interval looked wrong to the user, and it was.** Questioning it is
  what exposed the uncapped ladder. FSRS is not miscomputing anything there; it
  answers correctly when recall probability falls to the target. But
  retrievability on demand is not the objective for a language somebody intends
  to speak, so the target was the wrong instruction, not the model.
- **A comment in `scheduler.py` was wrong and was retracted in place.** It
  claimed the uncapped default was deliberate, because clipping the model means
  distrusting it. Capping expresses a different objective; it is not a lack of
  confidence in FSRS.
- Capitalisation was nearly enforced on every word rather than on nouns. Applied
  to verbs it would fail `Gehen` for breaking no rule the learner is being
  taught. Restricted to nouns before it shipped.

**Decisions:**

- **Determiner and noun are graded separately**, so a correct noun with the
  wrong article reports "right word, wrong gender" rather than a flat wrong.
  Chosen as the better learning signal.
- **A wrong or missing determiner is Again (1).** The item being scheduled is
  `das Haus`, not `Haus`, and it was not produced.
- **Capitalisation alone, with word and gender both right, is Hard (2).** A
  deliberate exception: noun capitalisation is one systematic rule rather than
  42 separate facts, so a missed shift key says nothing about whether this
  particular word is known. Destroying 96% of an item's stability over it would
  make the tool punishing to use.
- `ae`, `oe`, `ue` and `ss` are accepted for `ä`, `ö`, `ü` and `ß`, since the
  learner has no German keyboard. Folded on both sides, so `Baeckerei` matches
  and `Backerei`, the umlaut simply dropped, does not. Feedback always shows the
  properly spelled form.
- A determiner that disagrees with the drilled form but agrees with the stored
  gender is Good, with a note naming the drilled form. `der Bruder` against a
  drilled `mein Bruder` is correct German and demonstrates exactly the knowledge
  being tested. Grading it "wrong gender" would have been a lie about the one
  thing this exercise is for.
- Retention 0.95 and the 365 day ceiling are **starting values, not measured
  ones.** Revisit once `review_log` holds enough history to support a parameter
  fit.

**Next:**

- Step 5: wire the exercise to the scheduler, appending to `review_log` and
  updating `item_state`.
- 4a-ii left open deliberately: the grader cannot produce Easy, because a
  typing exercise cannot observe effort.

## 2026-08-26: German batch imported, FSRS scheduler built, state machine deleted before it was written (steps 2e and 3)

**Reconstructed:** _written 2026-09-07 from commits `369d807` and `b248501`,
`requirements.txt` and `docs/TODO.md`. Not written contemporaneously._

**Focus:** _Get the reviewed TSV into the database, then build the scheduler on
top of it._

**Worked on:**

- `scripts/import_lexical_items.py` transcribes a reviewed TSV into
  `lexical_items`, creating `item_state` rows only for rows marked
  `drillable=yes`.
- `wordhoard/scheduler.py` translates `item_state` rows to and from `fsrs.Card`,
  appends to `review_log` **before** updating `item_state`, and builds the due
  queue with the daily new limit applied.
- Project venv created at `.venv`. `requirements.txt` pinned from a real freeze
  for the first time, including `fsrs==6.3.2`.
- Ran the real `scripts/init_db.py --learner "Ian" --language de` against the
  project root, creating `word-hoard.db`.

**Measurements worth keeping:**

- Import against the live database: 117 items, 74 scheduler rows, 43 stored as
  reference and unscheduled. 0 empty strings where NULL was meant, 0 gendered
  nouns without an `answer_form`, 0 scheduler rows pointing at absent content.
  A re-run reports 117 unchanged and creates no new scheduler rows.
- Scheduler walk on a scratch copy: a new item takes a 10 minute step, graduates
  to 2 days, then 14, then 49.
- `target_retention` on one identical card: 0.80 gives a 109 day interval, 0.90
  gives 32, 0.99 gives 2. That column is the single biggest lever on daily
  workload in the whole system.
- Failing a graduated item moves it to `relearning` and increments `lapses`.
  Failing one still in learning does not.
- `review_log` gained 6 append-only rows: NULL before-state on the first review,
  real elapsed and scheduled days thereafter.
- Daily new cap: 10 items offered on an unreviewed database, 0 once 10 had been
  introduced, 10 again the following day.

**Troubleshooting / dead ends:**

- **`pip install py-fsrs` fails.** `py-fsrs` is the GitHub project name; the
  PyPI distribution is plain `fsrs`. The error is "no matching distribution
  found", which gives no hint of the real name. Recorded in `requirements.txt`
  and in `memory/fsrs-not-sm2.md`.
- **The planned learning-steps state machine was not written, and should never
  be.** `fsrs` 6.x implements it, via `Scheduler(learning_steps=...)` and
  `Card.step`. The project had it queued as our own code across the TODO, the
  OVERVIEW and a memory file, and all three were corrected. The pin carries a
  note not to downgrade below 6 without restoring what the library provides.
- Nearly hardcoded 0.9 retention in the scheduler rather than reading
  `learner_languages.target_retention`. Caught as TODO 3a and settled by the
  measurement above instead of by assertion.

**Decisions:**

- **The import is re-runnable, and that forces one asymmetry.** `lexical_items`
  is content owned by the TSV and safe to overwrite. `item_state` is scheduling
  progress owned by the learner's review history, and is never reset or deleted.
  Verified by seeding progress (state `review`, stability 12.5, 7 reps, 1 lapse,
  a set `due_at`), editing the content, re-importing, and confirming the word
  changed while the progress survived untouched.
- **`--dry-run` takes the real write path and rolls back**, so its counts are
  measurements rather than predictions. A dry run that skips the write path
  over-counts, and that number is what a human uses to authorise the real run.
- **Function words are stored but never scheduled.** 43 of 117. An English
  prompt of "the" has three German answers. No new column was needed: simply
  create no `item_state` row, which is what separating content from scheduling
  in the schema bought.
- **Learning step durations live as module constants** `LEARNING_STEPS` and
  `RELEARNING_STEPS` in `wordhoard/scheduler.py`, passed into the library
  scheduler rather than driving a state machine of our own. Not a settings
  table: a two-person tool does not need a UI for a number that changes once a
  year.
- **FSRS is depended on rather than reimplemented from the paper.** The
  algorithm is the core value of the project, and a subtle reimplementation bug
  would be invisible for months.
- The daily new cap counts items whose **first** review was today, not reviews
  today. Those are different numbers.

**Next:**

- Step 4: the typing exercise, with the `answer_form` fallback in one place.
- Settle 4a-i, still open: what rating a right-word-wrong-gender answer feeds
  into FSRS.

## 2026-08-24: First commit landed, handover retired, remote recorded

**Reconstructed:** _written 2026-09-07 from commit `93d5eed` and the memory
files it touched. Not written contemporaneously._

**Focus:** _Clear the housekeeping that was deliberately queued behind the first
commit._

**Worked on:**

- Deleted `handover.md`. Its content now lives in `CLAUDE.md`,
  `docs/OVERVIEW.md`, `schema.sql`, `docs/TODO.md` and `memory/`, and the file
  stays recoverable from `00c9eb9`.
- Deleted `data/review/german_draft revised.tsv` once its seven pronunciation
  edits were folded back into `scripts/draft_german.py`, so there is one draft
  rather than two.
- Added the GitHub remote and replaced `memory/local-only-git-no-remote.md` with
  `memory/git-remote-and-push.md`. Updated `CLAUDE.md` to match, so the Wrap Up
  push step no longer instructs itself to skip.
- Recorded the content review round trip in
  `memory/learner-cannot-verify-target-language.md`.

**Troubleshooting / dead ends:**

- The remote was first added with the wrong URL, `Word_Hoard` with an underscore
  rather than `Word-Hoard` with a hyphen. Corrected with `git remote set-url`
  rather than by removing and re-adding.
- **Google Sheets mangled the returned TSV.** The reviewed file came back with
  stray apostrophes where the spreadsheet had half-stripped the quotes around
  the pronunciation hints. Treated as a round-trip artifact rather than an
  intended edit, confirmed with the user, then folded in.

**Decisions:**

- **The generating script, not the TSV, is the source of truth for a content
  batch.** Accepted edits go back into `scripts/draft_german.py` and the file is
  regenerated, so the two cannot drift.
- Returned review files are diffed before staging, never staged blind.

**Next:**

- Step 2e: the import script, which closes step 2.
- Then step 3, the scheduler.

## 2026-08-23: Project setup, schema landed, German content batch drafted

**Focus:** _Turn three loose files (a Claude template, a handover brief, an ERD)
into a working project, then get as far into the vertical slice as the open
decisions allowed._

**Worked on:**

- Initialised the repository (local only, no remote) and adopted
  `CLAUDE_TEMPLATE.md` as `CLAUDE.md` with both `FILL IN` blocks written.
- Ingested `handover.md` into permanent homes: `CLAUDE.md`, `docs/OVERVIEW.md`,
  `docs/TODO.md`, `schema.sql`, and 9 files under `memory/`. The original is
  still on disk pending the first commit.
- Wrote `schema.sql` as the authoritative database definition, with the
  reasoning for each deliberate tradeoff commented in place. Verified by
  execution against an in-memory database: 9 tables.
- Slice step 1b: `wordhoard/db.py` and `scripts/init_db.py`. Verified end to
  end against a scratch database. 9 tables, 2 languages seeded, learner enrolled
  at the schema defaults (10 new/day, 0.9 target retention). A second run
  refused with exit code 1 rather than touching the existing file.
- Slice step 2a to 2d: sourced content from the learner's own FreeMind
  mindmaps at `C:/Users/Ian/Documents/General/German.mm` and `Dutch.mm`.
  `scripts/parse_mindmap.py` extracts 117 German and 59 Dutch entries into
  reviewable TSV. `scripts/draft_german.py` produces the corrected German batch:
  117 entries, 74 drillable, 42 with an `answer_form` distinct from the lemma.
  Reviewed by the user with no corrections raised.
- Drafted 8 example sentences with their word links, which the mindmap supplies
  for free by nesting sentences beneath their word.

**Measurements worth keeping:**

| | German | Dutch |
|---|---|---|
| Mindmap entries parsed | 117 | 59 |
| Content words | 71 | 34 |
| Function words and rules | 46 | 25 |
| Content words usable as a card with no editing | 25 | 14 |
| Example sentences captured | 10 (3 false positives) | 5 |

The headline number is 25 of 71. The mindmaps were written for a reader who
already knew what he meant, so 41 of 117 German entries carried no English gloss
at all (`die pizza`, `der salat`, `das brot`).

**Troubleshooting / dead ends:**

- **Bash heredoc silently truncated `schema.sql`.** The write reported success
  and produced a 7645 byte file that stopped mid-way through the `review_log`
  CREATE, with the trailing `SQLEOF` and the verification command swallowed into
  the heredoc. Only caught because the verification step was a real execution
  rather than a file listing. Switched to the Write tool. **Lesson: verify a
  generated SQL file by running it, not by checking it exists.**
- **Python heredoc failed on a Windows path.** `"C:\Users\..."` in a
  non-raw string is a `SyntaxError: truncated \UXXXXXXXX escape`. The whole
  script failed at parse time, so a partial run was not a risk, but a full retry
  was needed. Forward slashes throughout since.
- **`parse_mindmap.py` first version misread categories.** A node whose children
  are all leaves is ambiguous: `Food` and `sein` look identical structurally.
  The parser emitted `Food` as a word whose translation was
  `die pizza | die wurst | der kase`. Caught by eyeballing the output, not by a
  test. Fixed with an explicit list of the category labels used in these two
  specific files, which is honest about the scope rather than pretending to a
  general heuristic. Also added handling for nested entries, which recovered
  `der bahnhof` (previously dropped because `hauptbahnhof` sits beneath it).
- **Sentence detection still has 3 known false positives.** `der Mann`,
  `die Frau` and `das Kind` are related-word nodes caught as sentences, because
  two words plus an article is shaped exactly like a short sentence. Nothing
  lost, since all three exist as proper entries, but the heuristic will need
  work if more mindmaps are parsed.
- **Reversal: possessives stripped, then restored.** The first draft reduced
  `meine mama` to lemma `Mama` with the possessive demoted to notes, on the
  reasoning that gender needs somewhere to live. The user corrected this: German
  nouns are learned with their determiner attached, and family members with
  their possessive. Both are true at once, which is what forced the
  `answer_form` column rather than a convention.
- **Two claims of mine that were wrong and got corrected in-session.** First,
  that the stack decision gated slice steps 3 to 6; it gates step 6 only, since
  steps 3 to 5 are framework-free domain logic. Second, that a Goethe A1
  wordlist was the right content source; the learner's own mindmaps are
  better on every axis.

**Decisions:**

- **Stack: FastAPI, at the edge only.** Nothing in `wordhoard/` imports it.
  Chosen for the auto-generated `/docs` interface, which gives a usable UI
  during a build phase whose UI is deliberately last, and for Pydantic
  validating the columns the schema deliberately leaves unconstrained. Not
  chosen for being new: it is from 2018. The future-proofing comes from the
  layering, not the framework, since the schema and the review history outlive
  any web layer.
- **Four columns added to `lexical_items`:** `translation_en` (the schema had
  no home for the English prompt at all, which blocked step 4 outright),
  `pronunciation`, `category`, and `answer_form`.
- **`answer_form` is a column, not a derivation.** Deriving `der Tisch` from
  gender is easy and cannot express `mein Bruder`, where the determiner is a
  possessive. Both patterns are in real use.
- **CHECK constraints on `item_state.state` and `review_log.rating` only.**
  Those two sets are closed, fixed by the state machine and by FSRS
  respectively. `content_type` and `exercise_type` deliberately get none: they
  are meant to gain values, and SQLite can only remove a CHECK by rebuilding the
  table. Verified both halves: bad values rejected, new content and exercise
  types still insert without migration.
- **Function words are ingested but not drilled.** 43 of 117 entries are marked
  `drillable=no`. They are real reference content, but an English prompt of
  "the" has three German answers. The schema already separates content from
  scheduling, so this needs no new column: simply create no `item_state` row.
- **Grade the determiner and the noun separately**, so a wrong article on a
  correct noun reports "right word, wrong gender" rather than a flat wrong.
- **Capitalisation is enforced.** A lowercase German noun is marked wrong.
- **Content source: the learner's mindmaps**, not a frequency list. Frequency
  lists are demoted to backfilling `frequency_rank` later. The top of any German
  frequency list is function words, which are the worst possible typing cards.

**Content corrections made to the source material** (the user does not speak
German and cannot verify these, hence the `changes` column in the draft):

- Spelling: `kase` to `Käse`, `bibliotek` to `Bibliothek`, `U-bahn` to `U-Bahn`.
- 14 lowercase German nouns capitalised.
- 9 missing genders supplied.
- `Die Bahnhof ist links` corrected to `Der Bahnhof`. The mindmap contradicted
  itself, having `der bahnhof` elsewhere.
- `nett` and `lecker` were both glossed "nice", which would have made one of them
  permanently unanswerable and recorded lapses that never happened. Split into
  "nice / kind (of a person)" and "tasty / delicious (of food)".
- Four profession pairs split into 8 separate male and female entries, likewise
  `sie` / `Sie`, `mein` / `meine`, `dein` / `deine`.
- `ist` and `bist` reclassified from Conjunctions to verb forms of `sein`.
  `mit` and `hier` were each listed twice; merged.

**Next:**

- Write the import script (2e): reviewed TSV into `lexical_items`, creating
  `item_state` rows only for `drillable=yes`. That closes step 2.
- Then step 3: FSRS via `py-fsrs`, plus the learning-steps state machine in
  front of it. Make sure `learner_languages.target_retention` reaches the
  scheduler rather than 0.9 being hardcoded.
- Open question deferred from 4a: what FSRS rating a right-word-wrong-gender
  answer should feed in. It is not a clean 1 and not a 3.
- `handover.md` deletion is queued behind the first commit.
- The Dutch mindmap has its own errors, including three `de`/`het` mistakes
  (`de brood`, `de kind`, `de meisje` should all be `het`). Deliberately
  untouched: Dutch is out of scope until the slice works.
