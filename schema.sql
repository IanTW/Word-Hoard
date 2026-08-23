-- word-hoard schema (SQLite)
--
-- This file is the authoritative definition of the database. The ERD in
-- language-app-erd.drawio draws the same tables visually; if the two ever
-- disagree, this file wins and the ERD is stale.
--
-- Several choices here look like mistakes a cleanup pass would "fix". They are
-- deliberate, and the reasoning is recorded inline below and in
-- docs/OVERVIEW.md. Raise them for discussion rather than refactoring them.

PRAGMA foreign_keys = ON;

-- ---------------------------------------------------------------------------
-- Static reference data. Not user data, not expected to grow beyond a handful
-- of rows ('de' first, 'nl' planned).
-- ---------------------------------------------------------------------------
CREATE TABLE languages (
    code TEXT PRIMARY KEY,        -- ISO 639-1: 'de', 'nl'
    name TEXT NOT NULL
);

-- ---------------------------------------------------------------------------
-- Learner profiles. Deliberately minimal: this is a local tool for two people
-- on one machine, so there is no authentication and no account concept. A
-- learner row exists purely to keep one person's review history separate from
-- another's.
-- ---------------------------------------------------------------------------
CREATE TABLE learners (
    id INTEGER PRIMARY KEY,
    display_name TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Which language(s) each learner is working on, plus the per-learner scheduling
-- knobs. Two learners may study different languages, or the same language at
-- different settings, hence the settings live here rather than on learners.
CREATE TABLE learner_languages (
    learner_id INTEGER NOT NULL REFERENCES learners(id),
    language_code TEXT NOT NULL REFERENCES languages(code),
    -- Cap on how many 'new' items enter the queue per day. 10 is a starting
    -- guess, not a measured value; revisit once real sessions have been run.
    daily_new_limit INTEGER NOT NULL DEFAULT 10,
    -- Desired probability of recall at review time, fed straight into FSRS as
    -- its desired-retention parameter. 0.9 is the FSRS reference default.
    -- This column must actually reach the scheduler; do not hardcode 0.9.
    target_retention REAL NOT NULL DEFAULT 0.9,
    PRIMARY KEY (learner_id, language_code)
);

-- ---------------------------------------------------------------------------
-- Content. Kept language-agnostic on purpose: no column may assume a feature
-- specific to German, because Dutch and any later language will differ in what
-- grammatical features apply at all. German and Dutch diverge on case marking
-- (German retains it, Dutch has largely lost it) and on word order, which is
-- why they are a useful pair to hold in mind while shaping this even before any
-- Dutch content exists.
-- ---------------------------------------------------------------------------
CREATE TABLE lexical_items (
    id INTEGER PRIMARY KEY,
    language_code TEXT NOT NULL REFERENCES languages(code),
    -- Dictionary form, bare: 'Haus', 'Bruder', 'gehen'. This is what joins,
    -- frequency lookups and sentence linking key on, so it stays unadorned.
    lemma TEXT NOT NULL,
    -- What the learner is actually expected to type, which is NOT always the
    -- lemma. German nouns are learned with their article ('das Haus', never
    -- 'Haus'), and family members are learned with their possessive ('mein
    -- Bruder'). Accepting the bare noun would quietly excuse the learner from
    -- the hardest part of German nouns, which is the gender.
    --
    -- Nullable: when NULL the exercise falls back to lemma, which is correct
    -- for verbs, adjectives and adverbs. The fallback is implemented once, in
    -- wordhoard, rather than restated at each call site.
    --
    -- This is deliberately not derived from gender at exercise time. Derivation
    -- handles 'der Tisch' but cannot express 'mein Bruder', where the
    -- determiner is a possessive rather than an article, and both patterns are
    -- in real use in the source material.
    answer_form TEXT,
    part_of_speech TEXT NOT NULL,
    -- Nullable because grammatical gender is not universal. Required for German
    -- nouns, absent for German verbs, and absent again for languages that do
    -- not mark gender at all.
    gender TEXT,
    -- The English prompt shown by the typing exercise. Nullable rather than NOT
    -- NULL because content is ingested from hand-made learner mindmaps where
    -- many entries have no English gloss (the writer knew what "die Pizza"
    -- meant). Those rows are real content and worth storing; they are simply
    -- not drillable until a prompt is written. Enforcing NOT NULL here would
    -- mean either discarding them or inventing translations at import time.
    --
    -- Write the prompt to be unambiguous in the English-to-German direction.
    -- The source mindmap glossed both "nett" and "lecker" as "nice", which
    -- would make one of them permanently unanswerable and record lapses that
    -- never happened. review_log feeds FSRS parameter refitting, so a false
    -- negative is not merely annoying, it corrupts the scheduler's model.
    translation_en TEXT,
    -- Informal pronunciation hint as written by the learner, e.g. 'beck-e-rye'
    -- for Bäckerei. Its own column rather than buried in notes because it is
    -- structured data in the source and is the natural prompt for the listening
    -- and speaking exercises later. Not IPA, and not intended to be.
    pronunciation TEXT,
    -- Semantic field: 'Food', 'Places', 'Professions'. This is the organising
    -- spine of the source mindmaps and had no home in the original schema.
    -- Distinct from grammar_concepts, which covers grammar rather than topic.
    -- A plain nullable column rather than a tags table: a word belongs to one
    -- topic here, and a join table would be machinery this tool does not need.
    category TEXT,
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
    audio_path TEXT,              -- NULL until an audio pipeline exists
    source TEXT                   -- 'tatoeba' | 'hand-authored' | 'llm-generated'
);

-- Which words appear in which sentences. Drives "drill this word in context"
-- once sentence exercises are built.
CREATE TABLE sentence_lexical_items (
    sentence_id INTEGER NOT NULL REFERENCES sentences(id),
    lexical_item_id INTEGER NOT NULL REFERENCES lexical_items(id),
    PRIMARY KEY (sentence_id, lexical_item_id)
);

-- ---------------------------------------------------------------------------
-- The scheduler's view: current mutable state, one row per learner per content
-- item. Answers the single question "what is due now".
--
-- Deliberate choice: ONE state per item, not one per (item, exercise type).
-- Recognising a word in multiple choice genuinely does not prove it can be
-- typed from memory, but running four independent schedulers per word
-- quadruples the due queue and gets confusing fast. Instead, exercise type is
-- recorded on each review in review_log, so accuracy by modality stays
-- reportable as a diagnostic without driving scheduling.
-- ---------------------------------------------------------------------------
CREATE TABLE item_state (
    learner_id INTEGER NOT NULL REFERENCES learners(id),
    -- Denormalized on purpose. This could be derived by joining out to the
    -- content tables, but this table is read on every app launch to build the
    -- due queue and that has to stay a fast single-table query. Intentional
    -- denormalization on a hot read path, not an oversight.
    language_code TEXT NOT NULL,
    -- Polymorphic content reference, deliberately NOT a foreign key. Content
    -- may be a lexical item or a sentence (and possibly other types later) and
    -- the scheduler genuinely does not care which. The cost is no
    -- database-level referential integrity on these two columns; for a personal
    -- single-user tool that is an accepted trade. Do not "fix" this by adding
    -- real foreign keys without re-opening the discussion.
    content_type TEXT NOT NULL,           -- 'lexical_item' | 'sentence'
    content_id INTEGER NOT NULL,
    -- Learning-steps state machine, which sits IN FRONT OF FSRS rather than
    -- inside it. Pure FSRS interval maths handles brand-new and just-failed
    -- items badly, so real implementations (Anki, RemNote) layer short fixed
    -- delays before an item graduates to the long-term schedule. These two
    -- columns are that machine's state.
    -- CHECK constrained because this is a genuinely closed set, fixed by the
    -- state machine's design rather than by anything that might grow. Note the
    -- deliberate asymmetry with content_type above, which gets no CHECK: that
    -- one is meant to gain values, and SQLite cannot alter a CHECK constraint
    -- without rebuilding the whole table.
    state TEXT NOT NULL DEFAULT 'new'
        CHECK (state IN ('new', 'learning', 'review', 'relearning')),
    step_index INTEGER NOT NULL DEFAULT 0,
    -- FSRS memory model. Both NULL until the item graduates out of learning
    -- steps and FSRS starts scheduling it.
    stability REAL,
    difficulty REAL,
    due_at TEXT,
    last_reviewed_at TEXT,
    reps INTEGER NOT NULL DEFAULT 0,
    lapses INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (learner_id, content_type, content_id)
);

-- ---------------------------------------------------------------------------
-- The historian's view: append-only, never updated, never deleted.
--
-- This is the whole reason for choosing FSRS. FSRS's real advantage over SM-2
-- is that its parameters can be refit to an individual learner's actual review
-- history, which is only possible if that history is preserved rather than
-- overwritten. item_state answers "what is due now"; review_log answers "how
-- has this person actually been performing". They are queried in completely
-- different ways, which is why they are separate tables.
-- ---------------------------------------------------------------------------
CREATE TABLE review_log (
    id INTEGER PRIMARY KEY,
    learner_id INTEGER NOT NULL REFERENCES learners(id),
    -- Same polymorphic pair as item_state, same reasoning.
    content_type TEXT NOT NULL,
    content_id INTEGER NOT NULL,
    -- Which exercise produced this review. 'typing' is the only one built in
    -- the vertical slice; the column exists now so modality accuracy is
    -- answerable later without a migration.
    exercise_type TEXT NOT NULL,
    reviewed_at TEXT NOT NULL DEFAULT (datetime('now')),
    -- 1 again, 2 hard, 3 good, 4 easy. CHECK constrained because FSRS defines
    -- exactly these four ratings; the set is fixed by the algorithm, not by us,
    -- so it will never need to grow. Worth guarding on an append-only table
    -- where a bad value would sit in the history forever and skew any later
    -- parameter refit. exercise_type above deliberately gets no CHECK: three of
    -- the four exercise types do not exist yet.
    rating INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 4),
    -- The scheduler inputs as they stood BEFORE this review was applied.
    -- Storing the before-state is what makes the log replayable for parameter
    -- refitting; storing only the after-state would not be.
    stability_before REAL,
    difficulty_before REAL,
    elapsed_days REAL,
    scheduled_days REAL
);
