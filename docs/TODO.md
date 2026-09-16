# TODO

Closed items move to [TODO_archive.md](TODO_archive.md) verbatim, they are not deleted.

## Focus

**The app is in real use. The next session starts at M3.** The vertical slice
is complete. `.venv/Scripts/python.exe scripts/serve.py` serves the app at
http://127.0.0.1:8000, and `scripts/review.py` does the same thing in a
terminal. **`review_log` now holds real history (22 rows at the 2026-09-10
backup). Never reset the database.**

**M1 is done as of 2026-09-08: the backup exists and runs automatically.**
`data/backup/` holds newline-delimited JSON of `review_log`, `item_state` and
the learner rows, refreshed after every answer in the browser and at the end of
every terminal session.

**M2a is done as of 2026-09-10:** `finish session`, a summary page and `Go
again`, requested by the first real session. The rest of M2 waits on use.

**M3 leg 1 has its source**, German Wiktionary's live API, chosen by probe on
2026-09-10. **The probe script was lost with its session scratchpad**, so the
next step is rebuilding it under `wordhoard/` from the description in M3.

The standing rule was that nothing after the slice begins until the loop has
been used for real. **The user confirmed on 2026-09-08 that they will now use
it**, so that rule is satisfied rather than lifted, and the questions it was
holding open are now answerable by evidence instead of argument: whether 0.95
retention is right, whether ten new a day is right, whether the feedback wording
helps, whether the missing Easy rating grates, and how fast 74 words runs dry.

That confirmation is what made M1 urgent, and M1 was therefore done first. From
the first real session `review_log` holds irreplaceable history and the database
file is gitignored. Content is rebuildable from the TSV; the log is rebuildable
by nothing, which is why the export had to exist before the studying started
rather than after.

The largest known gap is content volume: 74 drillable words is about a week at
ten a day. It is now M4 in the plan below, and it is blocked on M3 rather than
on real use. Verification comes first because generating entries the learner
cannot check, before a check exists, writes false lapses into a log that has
just become permanent.

Dependencies now live in a project venv at `.venv`, created 2026-08-26. Point
VS Code at `.venv/Scripts/python.exe`, or the `fsrs` import will fail.

Three project conventions landed 2026-09-07 and change how the next session
works rather than what it builds: the no-dashes rule now has a mechanical check
behind it, learner-facing features need a `docs/TESTPLAN.md` section agreed
before any code, and Wrap Up gained a housekeeping step. See **Project
conventions** below.

The 34 closed items were archived to `docs/TODO_archive.md` on 2026-09-07,
verbatim. Nothing was summarised; the file is the record of how each decision
was reached, and several carry measurements that are not written down anywhere
else.

---

## Open decisions

- [x] Exact format and location of the plain-text backup export. **SETTLED
      2026-09-08 by building it (M1).** Newline-delimited JSON, one file per
      table, in `data/backup/`, committed to git. Triggers: after every answer
      in the browser, at session end in the terminal, and on demand via
      `scripts/export_backup.py`.
- [ ] Whether speech recognition is built at all. Deprioritised below typing,
      reading and listening. German and Dutch ASR is a lot of complexity for a
      personal tool.
- [ ] Content sourcing beyond the first hand-entered batch: Tatoeba for
      sentence pools, selective LLM generation for typing sentences built
      around a specific word being drilled.
- [ ] Whether `CLAUDE_TEMPLATE.md` stays in this repo now that `CLAUDE.md` is
      adopted, or is kept elsewhere as a reusable template.

## Vertical slice

All six steps are closed and archived. What remains here is the four items that
were deliberately deferred rather than done, kept under this heading because
each one was a decision made during the slice and is best read next to it. The
gate on everything else is no longer step 6, which works; it is real use.

- [ ] 2f. Import the 8 drafted sentences from
      `data/review/german_sentences_draft.tsv` into `sentences` and
      `sentence_lexical_items`. **After step 6**, not now: sentences are
      outside the vertical slice. Drafted early only because the mindmap
      gives the sentence-to-word links for free.
- [ ] 4a-ii. The grader never produces Easy (4), because a typing exercise
      cannot observe effort: a correct answer typed slowly and one typed
      instantly are identical to it. The consequence is real, in that intervals
      for genuinely easy items grow more slowly than an Anki user pressing Easy
      would see. If that becomes annoying the fix is an explicit "that was
      easy" control in the step 6 interface, not an inference in the grader.
      Revisit after real review sessions, not before.
- [ ] 6a. `_describe_interval` is duplicated between `scripts/review.py` and
      `web/app.py`. Deliberate for now, since it is presentation and the two
      surfaces may reasonably word things differently. If they ever must agree,
      it moves into `wordhoard/`. Left as a marker, not a defect.
- [x] 6b. The web interface has no way to leave a session, because it has no
      notion of one. The terminal runner has `:q`. Decide whether the browser
      needs anything, after real use. **ANSWERED BY REAL USE 2026-09-10**, which
      is what "after real use" was waiting for: "could do with a restart button
      if I want to go again and a quit button". Closed by M2a below.

## Content quality

The verify/validate cycle that used to head this section is now **M3** in the
delivery plan, with its approach decided. `frequency_rank` moved into **M4**,
where the data is already being handled. Neither is restated here: one list, one
definition, or the two drift and the drift looks like progress.

What remains are the items the plan does not cover.

- [ ] Consider drilling the plain article form of family nouns as well as the
      possessive, so `der Bruder` is learned alongside `mein Bruder`. That is
      a second row per word, currently recorded only in `notes`. Deferred:
      it doubles 8 cards for unclear benefit before the loop has been used.
      **Now answerable by use rather than argument**, since the user is
      studying: if `mein Bruder` turns out to be drilled without `der Bruder`
      ever being learned, that shows up in practice.
- [ ] Dutch mindmap has its own errors, including three de/het gender
      mistakes (`de brood`, `de kind`, `de meisje` should all be `het`). Not
      touched: Dutch is the last milestone and nothing before it needs Dutch.
      Worth noting that these three are exactly what M3 leg 1 would catch
      automatically, so they are a free test case for the dictionary check.

## Delivery plan after the slice

Written 2026-09-08, replacing six one-line placeholders. Those placeholders were
an honest backlog and a dishonest plan: three of the four learning modes named
in `CLAUDE.md` were represented by the clause "the remaining exercise types",
and the content strategy by the words "more content".

**The gate has changed.** The standing rule was that nothing here starts until
the loop has real use behind it. The user confirmed on 2026-09-08 that they will
now use it, so the rule is satisfied by that rather than lifted. The immediate
consequence was M1, which is why that milestone was built the same day.

Milestones are ordered by what unblocks the most, not by what is most
interesting. Each learner-facing one needs its `docs/TESTPLAN.md` section agreed
before any code.

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
- [ ] **The backup is still on the same disk as the database.** It survives a
      corrupt database file, not a lost machine. Off-machine only happens when
      `data/backup/` is committed and pushed, which is manual. Decide whether
      that is good enough or whether a commit should be automatic too.

**Why this is first and why it is now urgent.** Content is fully rebuildable
from the TSV by re-running the import. `review_log` is rebuildable by nothing.
Until today that gap cost nothing, because the log was empty and every row in it
was a test. From the first real session it holds irreplaceable history, and the
database file is gitignored, so a disk failure loses it outright. This milestone
is small, boring, and the only one that protects something that cannot be
recreated.

### M2. Make the interface usable for daily sessions

The one page was specified as minimal and was verified as correct. Minimal was
right for proving the loop; it is not right for someone opening it every day.

**M2a is done, 2026-09-10, requested by the first real session.** Plan and
results in `docs/TESTPLAN.md`.

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
- [ ] Show progress within the session: how many answered, how many left today.
      The header already shows what is waiting; whether an in-session counter
      adds anything is a question for use, not for argument.
- [ ] Decide whether the "that was easy" control from 4a-ii belongs here. It is
      the fix for the grader never producing Easy, and this is the milestone
      where an extra control has somewhere to live.
- [ ] **Watch for a punishing review day** a few days after leaning on
      `Go again`. That is the signal the grant size is wrong, and the fix is the
      number, not the button. First use 2026-09-10: **"works good"**, which
      settles the feel of it but not the consequence, since the consequence
      arrives days later as a heavier queue.

### M3. Content verification. **Blocks all content growth.**

Approach decided 2026-09-08: **dictionary check plus an independent model as
auditor.** Neither alone is enough, and they fail differently, which is the
point.

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
- [ ] **Rebuild the probe as the implementation.** The 2026-09-10 probe
      batched up to 50 titles per call, parsed the heading template and handled
      a missing entry, but it lived only in a session scratchpad and **was gone
      by 2026-09-16**. Build it under `wordhoard/` with a cache so a re-run costs
      nothing, decide what to do with an unparsed entry, and re-run the three
      probe checks above (45 nouns, 20 corruptions, 3 Dutch errors) to confirm
      the rebuild matches.
- [ ] **Leg 2, model auditor.** A second pass that reviews each drafted entry
      and returns a structured verdict rather than prose. Runs as a separate
      call from whatever generated the entry.
- [ ] **The suppression rule.** An entry needs both legs to agree before it is
      imported. Any disagreement suppresses the entry and records why, rather
      than deleting it or importing it with a warning. Suppression is reversible
      by re-running; a bad row written into an append-only history is not.
- [ ] **Size the error rate honestly.** Before trusting the pipeline, draw a
      **uniform random sample** from the entries it passed and check them by
      hand or against a third source. A sample of the entries it flagged
      measures nothing about the ones it let through. Report the interval, not
      just the point estimate: zero errors in 60 draws is "under about 5%", not
      "0%".
- [ ] **Sample both sides.** Also check a sample of what the pipeline
      suppressed. A wrongly rejected word never appears among the accepted ones,
      so a precision sample cannot see it at any size.

**What this cannot fix.** Both legs check whether an entry is correct German.
Neither can tell whether it is a word worth learning, and neither closes the gap
in [[learner-cannot-verify-target-language]] so much as narrows it. Be explicit
about that when reporting a rate.

**A caution on the word independent.** A dictionary is genuinely independent: a
different kind of artefact, built by different people, failing in different
ways. A second model call is only partly independent, because it shares training
data and therefore shares blind spots with whatever drafted the entry. Use a
different model from the drafter, and treat agreement between two models as
weaker evidence than agreement with the dictionary.

### M4. Scale the content

- [x] Decide a target size. **DECIDED 2026-09-08, user agreed the proposal:
      600 drillable entries first**, roughly Goethe A1 coverage, **then 1300 for
      A2.** Current count is 74, so A1 alone is an eight-fold increase and A2 a
      seventeen-fold one. Both numbers are targets rather than measurements: no
      claim is made that 600 words is A1, only that A1 wordlists are around that
      size.
- [ ] Decide the source. Candidates already noted: a frequency list, the Goethe
      A1 and A2 wordlists, or generation audited through M3. Frequency lists put
      function words at the top, which are the worst possible typing cards, so
      they need filtering rather than taking from the top.
- [ ] Run it through M3 before importing anything. This milestone does not start
      until M3 has a measured pass rate.
- [ ] Backfill `frequency_rank` while the data is being handled anyway.

### M5. Sentences

- [ ] Import the 8 already-drafted sentences, which is TODO 2f, still open.
- [ ] Build a sentence pool. Tatoeba is the candidate already recorded.
- [ ] Make sentences schedulable. The dispatch table in `wordhoard/session.py`
      was built for exactly this: it should be one entry.

**Sentences are a dependency, not a feature.** Reading and listening both need
material longer than a single word, so M5 blocks M6 and M7.

### M6. Reading exercise

- [ ] Decide the form. The strongest machine-gradable candidate is **cloze**:
      show a German sentence with one word removed, learner types the missing
      word. It tests comprehension in context and it grades exactly like typing,
      so it reuses the grader.
- [ ] Alternative to weigh: German sentence shown, learner types the English.
      Rejected on first look because it cannot be graded mechanically, which
      would put a model in the review loop.

### M7. Audio and listening

- [ ] Decide the audio source. **Offline text-to-speech is the strong
      candidate**, since it fits a self-hosted personal tool, costs nothing per
      item, regenerates freely when content changes, and avoids the SSL proxy
      entirely. Recorded human audio is better quality and does not scale to
      1300 words.
- [ ] Decide where audio files live and whether they are generated ahead of time
      or on demand. They should not go in git.
- [ ] Listening exercise: hear it, type what you heard. Grades with the existing
      grader.
- [ ] **This is the milestone that forces JavaScript**, or at least an audio
      element and a play control. The no-JavaScript property of the current page
      was a step 6 simplification, not a principle, but it should be given up
      deliberately rather than by accident.

### M8. Speaking

- [ ] **Still a genuinely open decision: whether this is built at all.** Carried
      over unchanged from **Open decisions**.
- [ ] If it is built, the shape to evaluate is local speech recognition rather
      than a hosted service, for the same reasons as M7: no per-item cost, no
      proxy, and nothing leaving the machine.
- [ ] Decide what "correct" means for a spoken answer before writing anything.
      This is where a test plan agreed in advance matters most, because a
      pronunciation grader can be made to look good by being lenient.

### Later, and deliberately unscheduled

These are real but none of them blocks anything above.

- [ ] Statistics views, including accuracy by exercise type from `review_log`.
      Worth doing once the log holds enough to be worth looking at. Keep the
      no-gamification rule in view: a statistics page is where streaks get
      reinvented by accident.
- [ ] Grammar concept tagging. The `grammar_concepts` table exists and is empty.
- [ ] Second learner. The schema already supports it; nothing else does.
- [ ] Dutch. Only at this point does the per-language processing abstraction get
      designed, against two real languages rather than one.

## Project conventions

Adopted 2026-09-07 by porting from the atc-game project on this machine. See
`docs/DEVLOG.md` for that session.

- [x] **Offer to fix the two hook defects in atc-game.** The originals at
      `F:\Programming\Godot\Projects\atc-game\.claude\hooks\` carry both bugs
      found above, which means that project's dash check may never have blocked
      anything. Offered 2026-09-07. **DECLINED by the user the same day: leave
      it.** Recorded rather than dropped, so the next person to touch that
      project's hooks knows the bugs are known and the decision was deliberate.
      Both are described in `CLAUDE.md` under the mechanical check.
- [ ] Decide whether `.claude/settings.local.json` is ever needed here. Not
      created, because nothing so far is personal rather than project-wide.

## Housekeeping

- [ ] Decide what happens to `word-hoard.db` if it is ever lost before the
      plain-text export exists. Right now the content is fully rebuildable
      from `data/review/german_draft.tsv` by re-running the import, but
      `review_log` is not rebuildable by anything. That gap closes when the
      export is built, and until then it is a real single point of failure.
