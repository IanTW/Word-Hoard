# DEVLOG

Dated session narrative, newest first. Entries are appended during Wrap Up.

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
