# Personal language learning app — project handover

This document is the brief for picking up development work in Claude Code. It captures the goals, the architecture, the decisions already made and why, the schema, and the build order. An ERD file (`language-app-erd.drawio`) accompanies this document and shows the same schema visually.

## Project goal

A personal, self-hosted tool for learning languages, starting with German, with Dutch planned as a second language once the core is working. The person building this used Duolingo previously and liked the core learning modes (typing, reading, listening, speaking) but wants none of the gamification, streaks, or graphics. The priority is a solid, honest learning engine with real progression tracking, not an engagement product.

It will be used by more than one person (the builder plus a family member), each learning potentially different languages, run locally rather than as a hosted service. No accounts or authentication are needed, just a way to distinguish whose data is whose.

## Non-goals for the initial build

Do not build gamified elements (XP, streak counters, leaderboards, mascots). Do not build a polished or animated UI up front, function over form. Do not build all four exercise types before one works end to end. Do not build a formal multi-language processing abstraction before there is a second real language's content to generalize against, beyond keeping `language_code` present everywhere in the schema. Do not build authentication.

## Architecture overview

The system is organized into these building blocks:

- **Language content** — where words, sentences, and audio come from (wordlists, Tatoeba corpus, hand-authored material, selectively LLM-generated sentences).
- **Language processing** — tagging content with part of speech, grammar concepts, frequency rank, and audio. For the MVP this lives in ingestion scripts, not a formal per-language adapter interface. Formalize this only once Dutch content is actually being added and the real points of variation are visible.
- **Data model & storage** — a single SQLite database, described in full below. This is the block everything else depends on and it was designed first.
- **Learner profiles** — minimal. A table of learners and which language(s) each is working on, no authentication.
- **Progression tracking (SRS engine)** — implements FSRS (Free Spaced Repetition Scheduler), not the older SM-2 algorithm. Reasoning below.
- **Learning material generation** — turns a due item from the scheduler into an actual exercise (typing first, others later).
- **UI/UX** — plain, functional interface. No specific framework has been chosen yet; that's an open decision for the build.

## Key design decisions and reasoning

**FSRS over SM-2.** FSRS models per-item difficulty and stability separately and predicts recall probability, giving materially better scheduling than SM-2's simpler interval multiplication (the algorithm behind old-school Anki and most homemade SRS tools). Reference implementations exist in Rust and Python (`open-spaced-repetition/py-fsrs` is a reasonable one to study or depend on directly rather than reimplementing from the paper).

**Store the raw review log, not just current state.** The database has two related but separate tables: `item_state`, which holds the current mutable scheduling state per item, and `review_log`, an append-only history of every review event. This split exists because FSRS's real value comes from refitting its parameters to the individual learner's actual review history, which is only possible if that history is preserved rather than overwritten. `item_state` answers "what's due now," `review_log` answers "how has this person actually been performing," and they are queried completely differently.

**Learning steps sit in front of FSRS, not inside it.** Pure FSRS interval math doesn't handle brand-new or just-failed items well; real implementations (Anki, RemNote) layer short fixed delays (e.g. "again in 1 minute, then 10 minutes") before an item graduates into the long-term FSRS schedule. This needs a small state machine (`state` and `step_index` columns on `item_state`) ahead of the FSRS scheduling call, not a rewrite of FSRS itself.

**One shared memory state per item across exercise types, not one per (item, exercise type) pair.** A word getting recognized correctly in multiple choice does not mean it can be produced by typing. Rather than run four independent schedulers per word (which quadruples the due queue and gets confusing fast), keep one FSRS state per item, but log which exercise type produced each review in `review_log` so accuracy-by-modality can still be reported separately as a diagnostic, distinct from what drives scheduling.

**Polymorphic content references in `item_state` and `review_log`.** Both tables reference content via a `(content_type, content_id)` pair rather than a hard foreign key to a single table, because content can be a lexical item or a sentence (and potentially other types later) and the scheduler genuinely doesn't care which. The tradeoff is no database-level referential integrity on those columns; for a personal single-user tool this is an acceptable and deliberate trade, not an oversight. This should not be "fixed" by adding real foreign keys later without re-discussing it.

**`language_code` is denormalized onto `item_state`.** It could be derived by joining through to the content tables, but this table is read on every app launch to build the due queue, and that needs to stay a simple, fast, single-table query. This is intentional denormalization on a hot read path, not an oversight to be refactored away.

**Content model is language-agnostic on purpose.** No column assumes a feature specific to German (e.g. grammatical gender is nullable, not required) since Dutch and any future language will vary in what grammatical features apply. German and Dutch specifically diverge on case marking (German retains it more, Dutch has largely lost it) and word order rules, which is part of why they're a good pair to keep in mind while shaping the schema even before Dutch content exists.

**Backups: plain-text export, not versioning the raw SQLite file.** SQLite files don't diff well in git (small logical changes rewrite large parts of the binary file), so the plan is to periodically export the review log and current state to newline-delimited JSON, which is small, diffs cleanly, is human-inspectable, and can be reconstructed back into SQLite if needed. This export is what goes into the git repo (or cloud backup if it grows too large for git). The live `.db` file itself is not intended to be the versioned artifact.

## Schema (SQLite)

```sql
-- Static reference, not user data
CREATE TABLE languages (
    code TEXT PRIMARY KEY,        -- 'de', 'nl'
    name TEXT NOT NULL
);

CREATE TABLE learners (
    id INTEGER PRIMARY KEY,
    display_name TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE learner_languages (
    learner_id INTEGER NOT NULL REFERENCES learners(id),
    language_code TEXT NOT NULL REFERENCES languages(code),
    daily_new_limit INTEGER NOT NULL DEFAULT 10,
    target_retention REAL NOT NULL DEFAULT 0.9,
    PRIMARY KEY (learner_id, language_code)
);

-- Content
CREATE TABLE lexical_items (
    id INTEGER PRIMARY KEY,
    language_code TEXT NOT NULL REFERENCES languages(code),
    lemma TEXT NOT NULL,
    part_of_speech TEXT NOT NULL,
    gender TEXT,                  -- nullable: not every language has this
    notes TEXT,
    frequency_rank INTEGER
);

CREATE TABLE grammar_concepts (
    id INTEGER PRIMARY KEY,
    language_code TEXT NOT NULL REFERENCES languages(code),
    name TEXT NOT NULL,
    description TEXT
);

CREATE TABLE sentences (
    id INTEGER PRIMARY KEY,
    language_code TEXT NOT NULL REFERENCES languages(code),
    text TEXT NOT NULL,
    translation_en TEXT NOT NULL,
    audio_path TEXT,
    source TEXT                   -- 'tatoeba', 'hand-authored', 'llm-generated'
);

CREATE TABLE sentence_lexical_items (
    sentence_id INTEGER NOT NULL REFERENCES sentences(id),
    lexical_item_id INTEGER NOT NULL REFERENCES lexical_items(id),
    PRIMARY KEY (sentence_id, lexical_item_id)
);

-- The scheduler's view: current state per learner per content item
CREATE TABLE item_state (
    learner_id INTEGER NOT NULL REFERENCES learners(id),
    language_code TEXT NOT NULL,          -- denormalized on purpose, see decisions above
    content_type TEXT NOT NULL,           -- 'lexical_item' | 'sentence'
    content_id INTEGER NOT NULL,
    state TEXT NOT NULL DEFAULT 'new',    -- new | learning | review | relearning
    step_index INTEGER NOT NULL DEFAULT 0,
    stability REAL,
    difficulty REAL,
    due_at TEXT,
    last_reviewed_at TEXT,
    reps INTEGER NOT NULL DEFAULT 0,
    lapses INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (learner_id, content_type, content_id)
);

-- The historian's view: append-only, never updated
CREATE TABLE review_log (
    id INTEGER PRIMARY KEY,
    learner_id INTEGER NOT NULL REFERENCES learners(id),
    content_type TEXT NOT NULL,
    content_id INTEGER NOT NULL,
    exercise_type TEXT NOT NULL,          -- 'typing' for the vertical slice
    reviewed_at TEXT NOT NULL DEFAULT (datetime('now')),
    rating INTEGER NOT NULL,              -- 1 again, 2 hard, 3 good, 4 easy
    stability_before REAL,
    difficulty_before REAL,
    elapsed_days REAL,
    scheduled_days REAL
);
```

An ERD covering these same tables, color-coded by role (gray: static reference, coral: learner data, blue: content, yellow: live scheduler state, orange: review history), is provided separately as `language-app-erd.drawio`. The dashed lines on that diagram are the polymorphic `content_type`/`content_id` links described above; they are deliberately not drawn as solid foreign keys.

## Plan of action: build the vertical slice first

The agreed build order is a single working slice end to end before expanding scope in any direction:

1. Set up the SQLite database from the schema above.
2. Hand-enter a small batch of German `lexical_items` (a few dozen is enough to start).
3. Implement the FSRS scheduler (use or closely follow an existing reference implementation, e.g. `py-fsrs`, rather than reimplementing the algorithm from the paper) plus the short learning-steps state machine that sits in front of it.
4. Build one exercise type: typing (prompt in English, learner types the German word or short sentence). This was chosen over multiple choice because it's a stronger signal of actual recall, and over listening/speaking because it needs no audio pipeline or ASR to get started.
5. Wire the typing exercise to read due items from `item_state`, grade the response, write to `review_log`, and update `item_state` via the scheduler.
6. Build the minimal due-queue UI: show what's due, let the learner answer, show the next item. No stats dashboard yet, that comes after the loop works.
7. Only after this loop works end to end: add the plain-text export/backup job, then expand outward (more content, more exercise types, grammar tagging, stats views, second learner, Dutch).

Do not start on sentences, grammar concepts, multiple exercise types, or Dutch content until step 6 is working and has been used for real review sessions.

## Open decisions not yet made

These were flagged during design but intentionally left open for the build phase:

- Backend language/framework and frontend approach (no strong constraint has been set; pick something that keeps the loop simple to run locally).
- Exact format and location of the plain-text backup export.
- Whether speech recognition is built at all, given the complexity of decent German/Dutch ASR relative to its value for a personal tool; deprioritized relative to the other three modes.
- Content sourcing plan beyond the initial hand-entered batch: Tatoeba for reading/listening sentence pools, selective LLM generation for typing sentences built around a specific word being drilled.

## Notes for Claude Code

Treat the schema and the decisions above as fixed unless a real problem surfaces during implementation, several of them (the denormalized `language_code`, the polymorphic content references, the shared-state-across-modalities choice) look like things a cleanup pass might "fix," but they were deliberate tradeoffs made with the reasoning stated above, not oversights. If you think one should change, raise it rather than silently refactoring it. Prioritize getting the six-step vertical slice above fully working before touching anything outside its scope.
