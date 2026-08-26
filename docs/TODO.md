# TODO

Closed items move to [TODO_archive.md](TODO_archive.md) verbatim, they are not deleted.

## Focus

**Slice step 3: the FSRS scheduler, with the learning-steps state machine in
front of it.** Steps 1 and 2 are done. The live database at `word-hoard.db`
holds 117 lexical items, 74 of them scheduled for learner Ian at pristine
defaults, so there is a real due queue for the scheduler to read.
The stack decision gates step 6 only, not steps 3 to 5, because the scheduler is
framework-free domain logic. Nothing in `wordhoard/` imports a web framework and
nothing should until step 6.

Content volume is knowingly thin: 74 drillable words at the default 10 new per
day is about a week of fresh material. Scaling it is a data task that step 2e
has now made cheap, and it is deliberately queued behind step 6 rather than
done now, because generating content the learner cannot verify before the
verify cycle exists would write false lapses into an append-only log. See
**Content quality** below.

---

## Open decisions

- [x] **Backend and frontend stack. DECIDED: FastAPI, at the edge only.**
      Nothing in `wordhoard/` imports it. Chosen for the free `/docs`
      interface during the UI-less build phase and for Pydantic validating
      the columns the schema deliberately left unconstrained, not for being
      new (it is from 2018). Confirmed 2026-08-23.
- [ ] Exact format and location of the plain-text backup export. Decided in
      principle: newline-delimited JSON of `review_log` and `item_state`.
      Undecided: file layout, directory, and what triggers the export.
- [ ] Whether speech recognition is built at all. Deprioritised below typing,
      reading and listening. German and Dutch ASR is a lot of complexity for a
      personal tool.
- [ ] Content sourcing beyond the first hand-entered batch: Tatoeba for
      sentence pools, selective LLM generation for typing sentences built
      around a specific word being drilled.
- [ ] Where the learning-step durations live. Default assumption is a module
      constant, not a settings table. Confirm when step 3 is built.
- [x] CHECK constraints. **DECIDED:** added on `item_state.state` and
      `review_log.rating`, which are closed sets fixed by the state machine
      and by FSRS. Deliberately NOT added on `content_type` or
      `exercise_type`, which are meant to gain values and which SQLite could
      only unconstrain by rebuilding the table. Verified: bad values
      rejected, new content and exercise types still insert without
      migration.
- [ ] Whether `CLAUDE_TEMPLATE.md` stays in this repo now that `CLAUDE.md` is
      adopted, or is kept elsewhere as a reusable template.

## Vertical slice

Do not start anything outside this list until step 6 works and has been used for
real review sessions.

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
- [ ] 2f. Import the 8 drafted sentences from
      `data/review/german_sentences_draft.tsv` into `sentences` and
      `sentence_lexical_items`. **After step 6**, not now: sentences are
      outside the vertical slice. Drafted early only because the mindmap
      gives the sentence-to-word links for free.
- [ ] 3. Implement the FSRS scheduler. Use or closely follow `py-fsrs` rather
      than reimplementing from the paper. Include the learning-steps state
      machine that sits in front of it.
- [ ] 3a. Make sure `learner_languages.target_retention` actually reaches the
      scheduler. Do not hardcode 0.9.
- [ ] 4. Build the typing exercise: prompt in English, learner types the
      German. Expected answer is `answer_form` where set, otherwise `lemma`.
      Implement that fallback in one place.
- [x] 4a. How strictly to grade the determiner. **DECIDED 2026-08-23: grade
      the determiner and the noun separately**, so the feedback can say
      "right word, wrong gender" rather than a flat wrong. Chosen as the
      better learning signal.
- [ ] 4a-i. Follow-on, undecided: what rating a right-word-wrong-gender
      answer feeds into FSRS. It is not a clean 1 (again) and not a 3
      (good). Decide when step 4 is built, and record the reasoning.
- [x] 4b. Whether capitalisation is graded. **DECIDED 2026-08-23: yes,
      enforced.** German nouns are capitalised and the point is to learn it
      correctly. Applies to the noun itself; see 4a for how the determiner
      is scored alongside it.
- [ ] 5. Wire typing to the scheduler: read due items from `item_state`, grade
      the response, append to `review_log`, update `item_state`.
- [ ] 6. Minimal due-queue interface. What is due, answer it, next item. No
      stats dashboard yet.

## Content quality

- [ ] **Build a verify/validate cycle for generated target-language content.**
      Agreed in principle, deliberately deferred. The user does not speak
      German or Dutch and cannot check drafted content, so correctness rests
      on Claude's output plus a changes column. Options to weigh: check
      lemmas and genders against an independent dictionary source, round-trip
      translations, or a second-model review pass. Raise this before any
      large content generation run, not after.
- [ ] Consider drilling the plain article form of family nouns as well as the
      possessive, so `der Bruder` is learned alongside `mein Bruder`. That is
      a second row per word, currently recorded only in `notes`. Deferred:
      it doubles 8 cards for unclear benefit before the loop has been used.
- [ ] Backfill `frequency_rank` from a real frequency list once there is a
      reason to care about ordering.
- [ ] Dutch mindmap has its own errors, including three de/het gender
      mistakes (`de brood`, `de kind`, `de meisje` should all be `het`). Not
      touched: Dutch is out of scope until the slice works.

## After the slice works

Ordered, but not started until step 6 has real usage behind it.

- [ ] Plain-text export and backup job.
- [ ] More content, then the remaining exercise types.
- [ ] Grammar concept tagging.
- [ ] Statistics views, including accuracy by exercise type from `review_log`.
- [ ] Second learner.
- [ ] Dutch. Only at this point does the per-language processing abstraction get
      designed, against two real languages rather than one.

## Housekeeping

- [x] Delete `handover.md` once the first commit has landed, so it stays
      recoverable from git history. Its content now lives in `CLAUDE.md`,
      `docs/OVERVIEW.md`, `schema.sql`, this file and `memory/`. Deleted in
      commit `93d5eed`, recoverable from `00c9eb9`.
- [x] Add `pip-system-certs` to `requirements.txt` when that file is first
      created. See the Environment section of `CLAUDE.md` for why.
- [ ] Pin `requirements.txt` versions from `pip freeze` after the first
      successful install on this machine. Left open deliberately: a guessed pin
      looks authoritative and is not.
- [x] Run the real `python scripts/init_db.py --learner "NAME" --language de`
      against the project root. Run 2026-08-25 as `--learner "Ian"`: created
      `word-hoard.db` with 9 tables, 2 languages seeded, learner Ian at id 1.
      The file is gitignored; the versioned artifact is the plain-text export.
- [ ] Decide what happens to `word-hoard.db` if it is ever lost before the
      plain-text export exists. Right now the content is fully rebuildable
      from `data/review/german_draft.tsv` by re-running the import, but
      `review_log` is not rebuildable by anything. That gap closes when the
      export is built, and until then it is a real single point of failure.
