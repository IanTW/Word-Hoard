# TODO archive

Closed items from [TODO.md](TODO.md), moved here verbatim with their close-date
context rather than deleted. This file grows monotonically and is never
summarised or compressed. First archive run 2026-09-07, moving 34 items.

## Open decisions

- [x] **Backend and frontend stack. DECIDED: FastAPI, at the edge only.**
      Nothing in `wordhoard/` imports it. Chosen for the free `/docs`
      interface during the UI-less build phase and for Pydantic validating
      the columns the schema deliberately left unconstrained, not for being
      new (it is from 2018). Confirmed 2026-08-23.
- [x] Where the learning-step durations live. **DECIDED 2026-08-26: module
      constants** `LEARNING_STEPS` and `RELEARNING_STEPS` in
      `wordhoard/scheduler.py`, passed into the library's scheduler rather than
      driving a state machine of our own. Not a settings table: a two-person
      tool does not need a UI for a number that changes once a year.
- [x] CHECK constraints. **DECIDED:** added on `item_state.state` and
      `review_log.rating`, which are closed sets fixed by the state machine
      and by FSRS. Deliberately NOT added on `content_type` or
      `exercise_type`, which are meant to gain values and which SQLite could
      only unconstrain by rebuilding the table. Verified: bad values
      rejected, new content and exercise types still insert without
      migration.

- [x] Exact format and location of the plain-text backup export. **SETTLED
      2026-09-08 by building it (M1).** Newline-delimited JSON, one file per
      table, in `data/backup/`, committed to git. Triggers: after every answer
      in the browser, at session end in the terminal, and on demand via
      `scripts/export_backup.py`.

## Vertical slice

- [x] 1a. Write `schema.sql` from the agreed design. Verified by executing it
      against an in-memory SQLite database: all 9 tables create cleanly.
- [x] 1b. Build script that creates the actual `.db` file from `schema.sql`,
      including seeding `languages` and one `learners` row. `wordhoard/db.py`
      plus `scripts/init_db.py`. Verified end to end against a scratch database:
      9 tables created, 2 languages seeded, learner enrolled with the schema
      defaults (10 new/day, 0.9 retention), and a second run correctly refused
      with exit code 1 rather than touching the existing file.
- [x] 2a. Source the first batch. Decided: the learner's own FreeMind
      mindmaps at `C:/Users/Ian/Documents/General/German.mm` and `Dutch.mm`, in
      preference to a frequency list, because they are already at the right
      level and reflect what this learner actually studied. Frequency lists
      are demoted to backfilling `frequency_rank` later.
- [x] 2b. `scripts/parse_mindmap.py`: parse the mindmaps into reviewable TSV.
      Verified against both files: 117 German entries, 59 Dutch.
- [x] 2c. Draft the German batch with translations filled in, prompts
      disambiguated, genders and spellings corrected. `scripts/draft_german.py`
      produces `data/review/german_draft.tsv`: 117 entries, 74 drillable, 76
      carrying a recorded change. Mechanically checked for column count,
      duplicate lemmas, missing translations and bad flag values.
- [x] 2d1. Add `lexical_items.answer_form` and populate it: nouns drill as
      `das Haus`, family members as `mein Bruder`. 42 of 117 entries have an
      answer form distinct from the lemma. Asserted in the generator that no
      gendered noun escapes without a determiner.
- [x] 2d. User review of `data/review/german_draft.tsv`. Reviewed 2026-08-23,
      returned as `data/review/german_draft revised.tsv`. Seven pronunciation
      hints rewritten in the user's own respelling scheme (`pah-k`,
      `oo-baa-hn`, `beck-a-rye`, `becker`, `sh-or-n`, `zorn`, `v-oh`), the
      surrounding single quotes dropped, and the `changes` column cleared as
      a sign-off. No German content was disputed. Edits folded back into
      `scripts/draft_german.py` and regenerated.
- [x] 2d-ii. Delete `data/review/german_draft revised.tsv` once the folded
      edits are confirmed, so there is one draft rather than two. Confirmed by
      the user and deleted in commit `93d5eed`, still recoverable from
      `00c9eb9`.
- [x] 2e. Import script: reviewed TSV to `lexical_items`, and create
      `item_state` rows only for rows marked `drillable=yes`. Function words
      are stored as reference content but never enter the due queue, because
      an English prompt of "the" has three German answers.
      `scripts/import_lexical_items.py`, run 2026-08-25. Verified against the
      live database: 117 items, 74 scheduler rows, 43 stored as reference and
      unscheduled, 0 empty strings where NULL was meant, 0 gendered nouns
      without an `answer_form`, 0 scheduler rows pointing at absent content.
      Re-run reports 117 unchanged and creates no new scheduler rows.
      Separately verified that a content edit updates `lexical_items` while
      seeded scheduling progress (state `review`, stability 12.5, 7 reps,
      1 lapse, a set `due_at`) survives the re-import untouched.
- [x] 3. Implement the FSRS scheduler. `wordhoard/scheduler.py`, built on the
      `fsrs` PyPI package (note: NOT `py-fsrs`, which is only the repo name and
      does not install). **The learning-steps state machine was not written.**
      `fsrs` 6.x implements it: `Scheduler(learning_steps=...)` and `Card.step`.
      Our step durations are module constants passed in. Verified on a scratch
      copy of the live database: a new item walks 10 minutes, graduates to 2
      days, then 14 and 49; failing a graduated item moves it to `relearning`
      and increments `lapses`, while failing one still in learning does not;
      `review_log` gained 6 append-only rows carrying NULL before-state on
      first review and real elapsed and scheduled days thereafter.
- [x] 3a. Make sure `learner_languages.target_retention` actually reaches the
      scheduler. Do not hardcode 0.9. Verified by measurement on one identical
      card: retention 0.80 gave a 109 day interval, 0.90 gave 32 days, 0.99
      gave 2 days. The column is the single biggest lever on daily workload.
- [x] 3c. Retention and interval ceiling. **DECIDED 2026-08-27, prompted by the
      user questioning whether a 227 day interval could possibly be right.** It
      was not. Measured at the then-current retention of 0.9 with no ceiling, a
      word answered correctly every time was scheduled 163 days out on its
      fifth review, 498 on its sixth, **1348 on its seventh** and over twenty
      years by its ninth. FSRS is not wrong there; it answers when recall
      probability falls to the target. But retrievability on demand is not the
      objective for a language somebody means to speak.
      Two changes: `target_retention` default raised 0.9 to 0.95 in
      `schema.sql` and updated on the live row for Ian, and
      `MAXIMUM_INTERVAL_DAYS` capped at 365 in `wordhoard/scheduler.py`.
      Verified against the live database: the ladder now runs 1, 3, 8, 19, 43,
      89, 175, 325 days and meets the 365 cap on the tenth review.
      Costs roughly 1.5x the reviews. Still a starting value, not a measured
      one; revisit once `review_log` can support a parameter fit.
      A comment in `scheduler.py` claiming the uncapped default was deliberate
      because clipping means distrusting the model has been retracted in place:
      capping expresses a different objective, not a lack of confidence.
- [x] 3b. Due queue with the daily new limit. Verified: 10 new items offered on
      an unreviewed database, 0 offered once 10 had been introduced, and 10
      again the following day. The cap counts items whose FIRST review was
      today, not reviews today, which are different numbers.
- [x] 4. Build the typing exercise: prompt in English, learner types the
      German. Expected answer is `answer_form` where set, otherwise `lemma`.
      Implement that fallback in one place. `wordhoard/exercises.py`, with the
      fallback in `expected_answer()` and nowhere else. Verified by a 24 case
      table covering determiner errors, capitalisation, transliteration,
      whitespace, verbs, adjectives and phrases: 24 of 24 as expected.
- [x] 4c. Accept `ae`, `oe`, `ue` and `ss` for `ä`, `ö`, `ü` and `ß`, since the
      learner has no German keyboard. Folding is applied to both sides, so
      `Baeckerei` matches and `Backerei` (umlaut simply dropped) does not.
      Feedback always shows the properly spelled form. Affects 10 of the 74
      drillable answers, measured 2026-08-26.
- [x] 4d. Accept a determiner that disagrees with the drilled form but agrees
      with the stored gender: `der Bruder` against a drilled `mein Bruder` is
      correct German and demonstrates exactly the knowledge being tested.
      Rated Good with a note naming the drilled form. Grading it "wrong gender"
      would have been a lie about the one thing this exercise is for.
- [x] 4a. How strictly to grade the determiner. **DECIDED 2026-08-23: grade
      the determiner and the noun separately**, so the feedback can say
      "right word, wrong gender" rather than a flat wrong. Chosen as the
      better learning signal.
- [x] 4a-i. What rating a right-word-wrong-gender answer feeds into FSRS.
      **DECIDED 2026-08-26 by measurement, and against my own first
      recommendation.** On a mature item (stability 90 days, retention 0.9,
      fuzzing off): Again drops stability to 3.6 and returns it in 10 minutes;
      Hard raises it to 172.7 and returns it in 173 days; Good raises it to
      227.5 and returns it in 227 days. Hard is therefore not a middle course,
      it is a near-miss of Good, so rating a gender error Hard would tell the
      learner about it and then never drill it again.
      **A wrong or missing determiner is Again (1).** The item being scheduled
      is `das Haus`, not `Haus`, and it was not produced.
      **Capitalisation alone, with word and gender both right, is Hard (2).**
      Deliberate exception: noun capitalisation is one systematic rule rather
      than 42 separate facts, so a missed shift key says nothing about whether
      this word is known, and destroying 96% of an item's stability over it
      would make the tool punishing to use.
- [x] 4b. Whether capitalisation is graded. **DECIDED 2026-08-23: yes,
      enforced.** German nouns are capitalised and the point is to learn it
      correctly. Applies to the noun itself; see 4a for how the determiner
      is scored alongside it.
- [x] 5. Wire typing to the scheduler: read due items from `item_state`, grade
      the response, append to `review_log`, update `item_state`.
      `wordhoard/session.py` holds the rules and `scripts/review.py` holds the
      terminal input and output, split so step 6 reuses the rules rather than
      restating them. Verified on scratch copies: 8 answers written to
      `review_log` and to `item_state`, a failed item correctly reappearing one
      minute later inside the same session, `--limit` respected, `:q` and EOF
      both ending cleanly with everything already answered kept, and umlauts
      printing correctly with `PYTHONIOENCODING` unset.
- [x] 5b. **Introduce new items before testing them.** Found by the first real
      session on 2026-08-27, which produced 9 Again out of 17 reviews. That 53%
      measured nothing about German or about the grader: every one of those
      items was being demanded back by an app that had never shown it. A
      scheduler schedules the REVIEW of something already learned, and nothing
      in the system was doing the learning. A new item now shows its answer and
      asks for it to be copied; every encounter after the first is a real test.
      Recorded as `exercise_type = 'introduction'` at a fixed rating of 3,
      which is exactly what leaving that column unconstrained was for.
      Verified: one log row per introduction however many retries it took,
      retries write nothing, quitting mid-introduction leaves the item `new`
      so it is taught properly next time, and an introduced item comes back as
      a test rather than a second introduction.
- [x] 5c. **Reset the database**, since those 9 false lapses would otherwise sit
      permanently in an append-only log that FSRS later fits parameters
      against. Done 2026-08-29: rebuilt from `schema.sql` and re-imported from
      the TSV, giving 117 items, 74 scheduler rows, 0 reviews, all pristine.
      The fresh database inherited `target_retention` 0.95 from the schema
      default, which confirms that change reaches new databases and not only
      the row that was updated by hand. The discarded copy is in the session
      scratchpad, not in the repository.
- [x] 5a. `find_learner` moved from `scripts/import_lexical_items.py` into
      `wordhoard/db.py`, because a second script needed it and the project's own
      rule is one definition. Import script re-verified after the move.
- [x] 6. Minimal due-queue interface. What is due, answer it, next item. No
      stats dashboard yet. `web/app.py` plus one Jinja template, started by
      `scripts/serve.py`. Server-rendered HTML, no JavaScript.
      Verified against the live database: the index renders an introduction for
      a new item and a test for a seen one, form posts record correctly
      (`introduction` rating 3, `typing` rating 1 for a wrong gender), queue
      counts fall as items are learned, transliterated umlauts are accepted
      through the browser, and `/docs` comes free at status 200.
      **Post-then-redirect-then-get verified:** refreshing the feedback URL five
      times left `review_log` unchanged, so a stray reload cannot write a second
      row into an append-only log.
      **Framework isolation verified by grep:** no `fastapi`, `uvicorn`,
      `starlette` or `jinja2` anywhere under `wordhoard/`.

- [x] 6b. The web interface has no way to leave a session, because it has no
      notion of one. The terminal runner has `:q`. Decide whether the browser
      needs anything, after real use. **ANSWERED BY REAL USE 2026-09-10**, which
      is what "after real use" was waiting for: "could do with a restart button
      if I want to go again and a quit button". Closed by M2a below.

## Project conventions

- [x] **Mechanical check behind the no-dashes rule.** `.claude/settings.json`
      plus two PowerShell hooks: a Stop hook that will not let a turn end with
      an em or en dash in the reply, and a PostToolUse hook on Write and Edit
      that judges the text being written. Verified against 10 payload shapes,
      then confirmed live: an em dash written into a scratch `.md` was blocked.
      Two defects were found and fixed during the port, both still present in
      the atc-game originals: stdin read through `[Console]::In` decodes with
      the console codepage rather than UTF-8, so the dash never matched; and
      `powershell -Command "& script"` collapses exit 2 into exit 1, so the
      block never landed. Measured directly for both.
- [x] **Test plan convention.** `docs/TESTPLAN.md`, with the rule in
      `CLAUDE.md`: every learner-facing feature gets a section agreed before
      any code. Seeded with a retrospective record of what the slice actually
      verified, explicitly labelled as a record rather than an example.
- [x] **Housekeeping check.** `docs/HOUSEKEEPING.md` for the judgement half and
      `tools/housekeeping.sh` for the mechanical half, wired in as Wrap Up step
      4. Reports only, always exits 0. First run 2026-09-07 found one thing:
      30 closed items sitting in `docs/TODO.md`.

- [x] **Offer to fix the two hook defects in atc-game.** The originals at
      `F:\Programming\Godot\Projects\atc-game\.claude\hooks\` carry both bugs
      found above, which means that project's dash check may never have blocked
      anything. Offered 2026-09-07. **DECLINED by the user the same day: leave
      it.** Recorded rather than dropped, so the next person to touch that
      project's hooks knows the bugs are known and the decision was deliberate.
      Both are described in `CLAUDE.md` under the mechanical check.

## Housekeeping

- [x] Delete `handover.md` once the first commit has landed, so it stays
      recoverable from git history. Its content now lives in `CLAUDE.md`,
      `docs/OVERVIEW.md`, `schema.sql`, this file and `memory/`. Deleted in
      commit `93d5eed`, recoverable from `00c9eb9`.
- [x] Add `pip-system-certs` to `requirements.txt` when that file is first
      created. See the Environment section of `CLAUDE.md` for why.
- [x] Pin `requirements.txt` versions from `pip freeze` after the first
      successful install on this machine. Left open deliberately: a guessed pin
      looks authoritative and is not. Done 2026-08-26 and extended 2026-08-29
      when step 6 added the web layer; the item simply was not ticked at the
      time. Verified 2026-09-07 by `tools/housekeeping.sh`, which normalises
      names and diffs the file against `pip freeze` in the venv: pins match
      exactly, nothing pinned but uninstalled, nothing installed but unpinned.
- [x] Run the real `python scripts/init_db.py --learner "NAME" --language de`
      against the project root. Run 2026-08-25 as `--learner "Ian"`: created
      `word-hoard.db` with 9 tables, 2 languages seeded, learner Ian at id 1.
      The file is gitignored; the versioned artifact is the plain-text export.
- [x] Decide what happens to `word-hoard.db` if it is ever lost before the
      plain-text export exists. Right now the content is fully rebuildable
      from `data/review/german_draft.tsv` by re-running the import, but
      `review_log` is not rebuildable by anything. That gap closes when the
      export is built, and until then it is a real single point of failure.
      **Closed 2026-10-03:** the condition passed when the export was built
      2026-09-08 (M1). What remains, the backup sharing a disk with the
      database, is the open M1 item in `docs/TODO.md`.

## Delivery plan after the slice

### M1. Protect the review log. **DONE 2026-09-08.**

- [x] Plain-text export of `review_log` and `item_state` as newline-delimited
      JSON. Built 2026-09-08 as `wordhoard/backup.py` plus
      `scripts/export_backup.py`. Lands in `data/backup/`, which is committed:
      `*.db` is gitignored, so this is the versioned artifact. Every row carries
      a `content_key` natural key as well as its id, so a restore does not depend
      on autoincrement ids landing the same way. Writes are atomic, through a
      temporary file and `os.replace` with an `fsync`, so a crash cannot leave a
      truncated file that still parses. Verified by 15 checks agreed in
      `docs/TESTPLAN.md` before the code, run against scratch copies: counts,
      determinism, JSON validity, key agreement, round trip through a rebuilt
      database with reassigned ids, source integrity, and umlauts.

- [x] Decide the trigger. **DECIDED 2026-09-08: both, and automatically.** The
      browser exports after **every answer**, because it has no notion of a
      session to end and because the cost is negligible at this size, so a crash
      can never lose more than zero reviews. The terminal exports once at session
      end, because it does have a session. Both use `export_quietly`, which
      never raises: a backup failure must not cost the learner an answer.
      `scripts/export_backup.py` is the loud path for finding out why.
      Verified 14 of 14, three times.

- [x] Retire `memory/user-data-is-disposable-for-now.md`, or rewrite it to say
      the opposite. Its own expiry condition has fired. Done 2026-09-08: marked
      EXPIRED and inverted, rather than deleted, because other memories link to
      it and because the reversal is the fact worth keeping.

### M2. Make the interface usable for daily sessions

- [x] A notion of a session, so there is something to finish. `finish session`
      on every screen, a summary page, and `Go again`. Session state lives in
      `web/app.py` only; nothing in `wordhoard/` learns what a browser session
      is. Closes 6b.

- [x] An end-of-session summary. Answered, learned, the good/nearly/again tally,
      and when the next item is due. **Every number is read back out of
      `review_log` rather than counted alongside it**, so the summary cannot
      disagree with the history. No streaks, no XP, no percentages, no praise;
      a check greps the rendered page for all of them.

- [x] Going again past the daily cap. `Go again` grants exactly one further
      daily allowance of new words, and only when nothing is due under the
      ordinary rules. Bounded on purpose: introducing all 64 unseen words in one
      sitting would hand every one of them back over the following days.

### M3. Content verification. **Blocks all content growth.**

- [x] **Leg 1, dictionary. SOURCE DECIDED 2026-09-10 by probe, before any
      build.** German Wiktionary's own API, batched, up to 50 titles per call.
      Not the kaikki.org bulk dump: it exists and is reachable, but it is
      **1027 MB** for a check that needs one field per word, and the live API
      answered every noun we hold in **2 calls**. Roughly 30 calls would cover
      the 1300 word target.

      **Probe results, on a naive query set of all 45 gendered nouns in the
      database, in id order rather than chosen:**

      | Measure | Result |
      |---|---|
      | Entry found | 45 of 45 |
      | Gender parsed | 42 of 45 |
      | Agreed with ours | **42 of 42** |
      | Disagreed | 0 |

      The 3 that did not parse are `der`, `die` and `das`, which are articles
      carrying a gender in our data rather than nouns. Not a source failure.

      **The zero disagreements were checked rather than trusted.** Twenty
      genders were deliberately corrupted and the check caught **20 of 20**, so
      the agreement figure is a result about the content and not an artefact of
      an instrument that cannot fail.

      **And it was tested against the only real ground truth in the repository:**
      the three Dutch errors recorded in this file on 2026-08-23, long before
      this pipeline was imagined. Dutch Wiktionary returns neuter for `brood`,
      `kind` and `meisje`, so the method finds **3 of 3** errors that were
      documented independently of it.

      **What this does NOT establish**, and the distinction decides how much
      weight the number can carry: it measured content transcribed from the
      user's own mindmaps and hand-corrected. M3 exists to check content
      GENERATED at scale, which is a different population that may fail in
      different ways. 42 of 42 is a census of what we hold, not an estimate of
      what generation will produce. It also says nothing about translations,
      which are the other half of an entry and the half more likely to be wrong:
      gender is a closed three-way choice with a definitive answer, and a
      translation is neither.

### M4. Scale the content

- [x] Decide a target size. **DECIDED 2026-09-08, user agreed the proposal:
      600 drillable entries first**, roughly Goethe A1 coverage, **then 1300 for
      A2.** Current count is 74, so A1 alone is an eight-fold increase and A2 a
      seventeen-fold one. Both numbers are targets rather than measurements: no
      claim is made that 600 words is A1, only that A1 wordlists are around that
      size.
