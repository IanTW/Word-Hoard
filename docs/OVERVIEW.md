# word-hoard: project overview

## What this is

word-hoard is a personal language learning tool. It runs locally, it is used by
two people, and it exists because commercial language apps bundle a decent
learning engine with an engagement product nobody asked for. The starting
language is German. Dutch is planned as a second language, but only once the
German path works end to end.

The four learning modes worth keeping from that prior art are typing, reading,
listening and speaking. Everything else that usually comes attached, the
streaks, the experience points, the leaderboards, the mascot, the animations, is
explicitly out of scope. This is not a matter of taste to be revisited later. It
is the reason the project exists, and it shapes what gets built: the effort goes
into honest progression tracking rather than into anything designed to make a
person come back tomorrow.

Being a two-person local tool has one useful consequence. There are no accounts,
no login, no sessions and no authentication anywhere in the system. A `learners`
table exists for exactly one purpose: telling whose review history is whose.

## How it is shaped

The system breaks into seven blocks, though only some of them exist yet.

**Language content** is where words and sentences come from. The first batch
comes from an unexpected place: the learner kept FreeMind mindmaps of German and
Dutch vocabulary while studying, and those turned out to be a better source than
any published wordlist. They are already at the right level, already carry
English glosses and example sentences, and above all they are what this
particular person actually studied. Frequency lists, the obvious first instinct,
are a poor fit at this size, because the top of any German frequency list is
function words and "the" cannot be drilled when it has three German answers.
They are useful later for backfilling frequency rank. Beyond the mindmaps lie
wordlists, the Tatoeba corpus for sentence pools, and selectively LLM-generated
sentences built around a specific word being drilled.

**Language processing** is the tagging of that content with part of speech,
grammatical concepts, frequency rank and audio. For now this lives inside
ingestion scripts rather than behind any per-language adapter interface. In
practice it currently means one parser that turns a mindmap into a reviewable
table, and one hand-authored correction pass on top of it.

Keeping that informal is deliberate. A multi-language abstraction designed
against a single language is a guess about where the variation will be, and the
guess is usually wrong. The
abstraction gets built when Dutch content actually arrives and the real points
of variation become visible. Until then the only concession to multi-language is
that `language_code` is present everywhere in the schema.

**Data model and storage** is a single SQLite database, defined authoritatively
in `schema.sql`. This block was designed first because everything else depends
on it, and it carries most of the project's non-obvious decisions. They are
discussed below.

**Learner profiles** is the minimal pair of tables described above, plus
per-learner scheduling settings: a daily cap on new items, and a target
retention figure.

**Progression tracking** is a spaced repetition scheduler implementing FSRS.
This is the heart of the tool.

**Learning material generation** turns a due item from the scheduler into an
actual exercise. Typing first, the other three modes later. The grading rules
live apart from both the database and the scheduler, so that what counts as a
correct answer can be argued about in one file and tested without a database at
all. That matters more here than it usually would, for a reason given at the
end of this document.

**The interface** is plain and functional. Function over form, no polish, no
animation. It is FastAPI serving one server-rendered page with no JavaScript,
and a terminal runner that drives exactly the same logic. Both are thin by
construction: every rule they apply comes from a session module that neither of
them owns, so the two cannot drift into disagreeing about what a right answer
is.

## The decisions worth explaining

### FSRS rather than SM-2

Most homemade spaced repetition tools, and old versions of Anki, use SM-2: on
each review the current interval is multiplied by an ease factor which drifts up
or down depending on how well the answer went. It works, but it conflates two
things that behave differently. How hard an item intrinsically is for a
particular person, and how durably it is currently held in memory, are not the
same quantity, and SM-2 has only one number for both.

FSRS models them separately as difficulty and stability, and from those predicts
the probability of successful recall at any future moment. That prediction is
what lets the scheduler aim at a target retention rate rather than at an
arbitrary interval multiplier. Reference implementations exist; `py-fsrs` from
the open-spaced-repetition project is the sensible thing to study or depend on,
rather than reimplementing the algorithm from the paper.

### The web framework is kept at the edge, on purpose

FastAPI was chosen, but the more important half of that decision is that nothing
in `wordhoard/` imports it. The scheduler, the schema and the review history are
the parts of this project with a long life ahead of them; the routing layer is
the part most likely to be replaced. Letting a framework into the core would
make the framework's lifespan the project's lifespan.

This also matters for how the thing gets built. Slice steps 3 to 5 produce a
working scheduler with no interface at all, so they can be written and tested
without any web framework being installed, which means the framework question
never blocked work that did not depend on it.

FastAPI earned the pick for two specific reasons rather than for being modern,
which it is not particularly: it is from 2018. First, it generates a live
interactive documentation page from the endpoint signatures, which is a usable
interface during a build phase whose real interface is deliberately last.
Second, Pydantic validates at the edge exactly those fields the database
deliberately leaves unconstrained.

### Some values are constrained in the database, and some deliberately are not

Four columns hold what look like enumerated values: `state`, `rating`,
`content_type` and `exercise_type`. Only the first two carry a CHECK constraint.

The split follows whether the set can ever grow. FSRS defines exactly four
ratings and the learning-steps machine has exactly four states, both fixed by
design rather than by convenience. The other two are meant to gain values:
polymorphic content references exist precisely so a new content type needs no
scheduler change, and `exercise_type` was put on the review log before three of
the four exercises existed. Constraining those would reintroduce the migration
the design paid to avoid, and SQLite charges heavily for it, since a CHECK can
only be removed by rebuilding the table and copying the data across. On an
append-only log that grows for years, that is not a small thing.

The two open columns are validated in Python instead, at the edge, where adding
a value is a one-line change.

### What the learner types is not always the dictionary form

German nouns are learned with their article attached. The unit is `das Haus`,
never `Haus`, because the gender is the hard part and accepting a bare noun
quietly excuses the learner from it. Family members go further and are learned
with a possessive: `mein Bruder`, not `der Bruder`.

So `lexical_items` carries both a `lemma`, which is the bare dictionary form
that joins and frequency lookups key on, and an `answer_form`, which is what the
learner is expected to produce. The second is null for verbs and adjectives,
where the lemma already is the answer.

It is tempting to derive the answer form from the gender instead of storing it.
That handles `der Tisch` perfectly and cannot express `mein Bruder` at all,
where the determiner is a possessive rather than an article, and both patterns
are in genuine use in the source material.

### A scheduler schedules review, so something else has to do the teaching

This one was not designed. It was found, three minutes into the first real
session, and it is the most useful thing the project has learned about itself.

The tool worked exactly as built: it took the ten highest-priority new words,
asked for each in English, and recorded what came back. Nine of the first
seventeen answers were failures. Not because the words were hard, but because
the application had never once shown them. A spaced repetition scheduler
assumes it is scheduling the *review* of something already learned, and nothing
in the system was doing the learning. Anki gets away with the same shape only
because its users write their own cards and have therefore already met the
material; here a script built the cards from a mindmap the learner had not
opened in months.

So a new item is now introduced rather than tested. Its answer is displayed, the
learner types it to fix it in place, and only from the second encounter onward
is it a real question. Those introductions are recorded with their own exercise
type and a fixed rating, because a word copied off the screen says nothing about
memory and grading it would put false failures into a log that can never be
edited.

Two things are worth drawing out. The first is that no test could have caught
this, because every test supplied the answers from the same database the grader
was checking against; only a human meeting a prompt they had never been taught
could see it. The second is that the schema absorbed the fix for free. The
exercise type column was left deliberately unconstrained back at the beginning,
on the reasoning that three of the four planned exercises did not exist yet, and
that decision, made for an unrelated reason, is what allowed a new kind of
recorded event to appear on an append-only table at no cost.

### The review log is append-only, and that is the point

The database holds two tables that at first glance overlap. `item_state` holds
current mutable scheduling state, one row per learner per item, and answers
"what is due right now". `review_log` is an append-only record of every single
review event that has ever happened, and answers "how has this person actually
been performing".

The split exists because FSRS's real advantage only pays out if the raw history
survives. Its parameters can be refit to an individual learner's genuine review
record, which turns a generic scheduler into a personal one, and that refit is
impossible if each review overwrites the last. So `review_log` rows are never
updated and never deleted, and each row stores the scheduler inputs as they
stood before that review was applied, which is what makes the history
replayable.

### Learning steps are configured, not built

FSRS interval mathematics handles a mature item well and a brand-new or
just-failed item badly. Every real implementation solves this the same way, by
layering short fixed delays in front of the long-term schedule: see this again
in one minute, then in ten minutes, and only then let the real scheduler take
over. Anki and RemNote both do this.

The project planned to write that small state machine by hand, ahead of the
FSRS call, which is what the `state` and `step_index` columns on `item_state`
were designed to hold. Building it turned out to be unnecessary. The `fsrs`
library implements the steps itself from version 6: the scheduler takes
`learning_steps` and `relearning_steps` as configuration, and the card carries
its own step index. Measured against 6.3.2, a fresh card answered correctly goes
ten minutes, then graduates to two days, and a failed mature card drops back to
a ten minute step. That is exactly the machine that was going to be written.

So the durations remain this project's choice and live as a module constant,
while the machine that walks them belongs to the library. The two schema columns
still earn their place, because the card has to be persisted between sessions
and those are the fields that carry it. The general lesson is worth stating
plainly: a dependency's feature set is a fact to be checked at the moment of
use, not inherited from whatever was true when the design was written.

### One memory state per item, not one per exercise type

Recognising a German word in a multiple choice list does not prove it can be
produced from memory by typing. Those really are different skills, and a purist
design would track them separately. The purist design also runs four independent
schedulers over every word, quadruples the due queue, and becomes hard to reason
about very quickly.

The compromise: one FSRS state per item, but every review records which exercise
type produced it. Accuracy by modality stays fully reportable as a diagnostic,
it just does not drive scheduling.

### Content references are polymorphic, deliberately

`item_state` and `review_log` both refer to content through a `content_type` and
`content_id` pair rather than a foreign key into a specific table. A schedulable
thing might be a lexical item or a sentence today, and something else later, and
the scheduler genuinely does not care which. The cost is that the database
cannot enforce referential integrity on those two columns. For a personal tool
run by the person who wrote it, that is an accepted trade rather than an
oversight, and it should not be quietly converted into real foreign keys.

### `language_code` is denormalized on purpose

The same column appears on `item_state` even though it could be derived by
joining out to the content tables. `item_state` is read on every app launch to
build the due queue, and that needs to stay a single fast query against one
table. This is intentional denormalization on a hot read path.

### Backups are plain text, not the database file

SQLite files diff terribly. A small logical change rewrites large stretches of
the binary, so committing the live `.db` file would produce a repository history
that is large and tells you nothing. The plan instead is a periodic export of
the review log and current state to newline-delimited JSON, which is small,
diffs cleanly, can be read by a human, and can be rebuilt back into SQLite. The
export is the versioned artifact. The database file is not.

## Where this has got to

The build order was a single vertical slice, taken end to end before anything
widened, and that slice is now complete. The database is built from the schema
and holds a hand-corrected batch of German. The scheduler runs. One exercise
type exists, typing, prompting in English and expecting the German back. It is
wired to read due items, grade the answer, append to the review log and update
scheduler state. A minimal interface sits on top: what is due, answer it, next
item, nothing more.

Typing was chosen as the first exercise for two reasons. It is a stronger signal
of real recall than multiple choice, and unlike listening or speaking it needs
no audio pipeline and no speech recognition to get started.

Nothing else was allowed to begin until that loop had been used for real, and
the rule earned its keep. The first three minutes of use overturned a design
assumption that months of reasoning had not, and the first daily session asked
for something no one had planned: a way to stop, and a way to go again when the
queue runs dry. The browser now has both. The summary it shows at the end is
read straight back out of the review log rather than counted alongside it, so it
cannot disagree with the history, and it carries no streak, score or percentage,
because a session summary is one step away from the gamification this project
exists to avoid. Going again grants exactly one more day's allowance of new
words, not an unlimited supply, because every word introduced today comes back
over the following days.

Real use also made the log irreplaceable, so the first thing built after the
slice was the backup: every answer in the browser rewrites a plain-text export
that lives in the repository, with a natural key on every row so a restore does
not depend on database ids landing the same way twice.

The largest known gap is simply volume. Seventy-four drillable words is about a
week of new material at ten a day, which is a test harness rather than a course.
The target is six hundred, roughly the size of an A1 wordlist, then thirteen
hundred. Scaling is a data task rather than a code task, but it waits on a
verification pass, because generating entries the learner cannot check would
manufacture unverified claims at speed. That pass has two legs that fail
differently: a dictionary and a separate model acting as auditor. The dictionary
leg has its source, German Wiktionary queried live, and a probe against every
noun already held agreed on all 42 genders it could read, caught all 20 genders
corrupted on purpose, and found the three Dutch errors recorded weeks earlier by
hand.

One decision remains genuinely open: whether speech recognition gets built at
all. Decent German and Dutch recognition is a lot of complexity to carry for a
personal tool, and it sits below the other three modes in priority.

A quieter constraint runs underneath all of the content work. The person
building this does not speak German, and will not speak Dutch either, so he
cannot check generated vocabulary for correctness the way he could check code.
A wrong gender here is expensive in a way a wrong variable name is not: it gets
drilled until it is memorised, and the false reviews it produces settle
permanently into an append-only log that the scheduler later fits its parameters
against. The working answer is to check mechanically everything that can be
checked mechanically, and to surface every single change made to source material
so review can be aimed at the judgement calls rather than at re-reading
everything. A proper verification pass against an independent source is on the
list and not yet built.
