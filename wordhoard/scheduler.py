"""Spaced repetition scheduling for word-hoard.

Vertical slice step 3. This module owns the answer to two questions: what should
be reviewed now, and what happens to an item's memory state when it is answered.

Like the rest of `wordhoard/`, it imports no web framework. It also imports no
content tables. The scheduler refers to content only through the polymorphic
(content_type, content_id) pair, and deliberately does not know what a lexical
item is. That is what lets sentences, or anything else, become schedulable later
without touching this file.

## A design note that supersedes docs/OVERVIEW.md

The project's recorded plan was to write a learning-steps state machine in front
of FSRS, on the reasoning that raw FSRS interval maths handles a brand-new or
just-failed item badly and that Anki and RemNote both layer short fixed delays
ahead of the long-term schedule.

That reasoning still holds. What changed is that the `fsrs` library now does it
itself: `Scheduler` takes `learning_steps` and `relearning_steps`, and `Card`
carries the step index. Measured against fsrs 6.3.2, a fresh card rated Good
goes 1 minute, then 10 minutes, then graduates to a 2 day interval, and a failed
mature card drops to Relearning with a 10 minute step. That is precisely the
machine we were going to write.

So we do not write it. The project's standing rule is to depend on the FSRS
reference implementation rather than reimplement it, because a subtle
reimplementation bug would be invisible for months, and a hand-rolled state
machine sitting in front of a library that already has one is the same mistake
wearing a different hat. The step durations below are ours; the machine that
walks them is not.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone

from fsrs import Card, Rating, Scheduler, State

# Learning steps: the short fixed delays a brand-new item walks through before
# FSRS takes over long-term scheduling. These are the fsrs defaults, restated
# here rather than left implicit because they are a pedagogical choice this
# project owns, not an implementation detail of the library. One minute catches
# the item inside the same session; ten minutes catches it later in the same
# sitting. Neither number is measured. They are the Anki defaults, which is to
# say they are what a very large number of learners have found tolerable.
#
# A module constant rather than a settings table, per the decision recorded in
# docs/TODO.md: this is a two-person personal tool, and a settings UI for a
# number that changes once a year is machinery the project does not need.
LEARNING_STEPS = (timedelta(minutes=1), timedelta(minutes=10))

# Relearning steps: the same idea for an item that was known and has just been
# failed. Shorter, because the memory is damaged rather than absent.
RELEARNING_STEPS = (timedelta(minutes=10),)

# Ceiling on any scheduled interval, in days. One year.
#
# The fsrs default is 36500, a hundred years, which is effectively no ceiling.
# This file previously carried a comment claiming that leaving it uncapped was
# deliberate, on the grounds that clipping the output means distrusting the
# model. That reasoning was wrong and is retracted. The model is not being
# distrusted: it answers accurately when recall probability will fall to the
# retention target. Capping expresses a DIFFERENT OBJECTIVE from the one FSRS
# optimises, which is a legitimate thing to have.
#
# The objective here is that a language stays available rather than merely
# retrievable. Measured 2026-08-27 at the old retention of 0.9, an item answered
# correctly seven times running was scheduled 1348 days out, and by the ninth
# review over twenty years. Raising retention to 0.95 fixes the shape of that
# curve; this cap is the backstop that catches any individual word whose
# stability still runs away. It does nothing to the early curve, where every
# interval is well under a year.
MAXIMUM_INTERVAL_DAYS = 365

# Interval fuzzing spreads scheduled due dates by a small random amount so that
# a batch of items introduced on the same day does not come back as a single
# lump forever after. On, because this project imports vocabulary in batches,
# which is exactly the pattern that clumps.
ENABLE_FUZZING = True

# All timestamps are stored as UTC text in SQLite's own canonical format. Two
# reasons for text rather than a numeric epoch: it is readable when a human
# opens the database to work out what went wrong, and it sorts correctly as a
# string, which is what the due query relies on. UTC rather than local time
# because a review history that shifts by an hour twice a year is a history that
# cannot be replayed reliably.
DB_TIME_FORMAT = "%Y-%m-%d %H:%M:%S"

# Our item_state.state values against the library's State enum. Note the
# asymmetry: 'new' has no fsrs equivalent, because fsrs has no concept of a card
# that has never been seen. It creates a card at the moment of first review. Our
# schema needs the extra value because item_state rows are created at import
# time, long before any review, so that the due queue has something to offer.
STATE_TO_FSRS = {
    "learning": State.Learning,
    "review": State.Review,
    "relearning": State.Relearning,
}
FSRS_TO_STATE = {value: key for key, value in STATE_TO_FSRS.items()}


def to_db_time(moment: datetime) -> str:
    """Format an aware datetime for storage. Converts to UTC first."""
    return moment.astimezone(timezone.utc).strftime(DB_TIME_FORMAT)


def from_db_time(text: str | None) -> datetime | None:
    """Parse a stored timestamp back into an aware UTC datetime.

    Returns None for NULL, which is a meaningful value in this schema rather
    than missing data: a NULL due_at means an item has never been reviewed.
    """
    if text is None:
        return None
    return datetime.strptime(text, DB_TIME_FORMAT).replace(tzinfo=timezone.utc)


def scheduler_for(
    conn: sqlite3.Connection,
    learner_id: int,
    language_code: str,
) -> Scheduler:
    """Build the FSRS scheduler configured for one learner in one language.

    The desired retention comes from learner_languages.target_retention rather
    than from any literal here. This is slice item 3a, and it is the whole reason
    the column exists: retention is the one FSRS knob a learner has a real
    opinion about, since it trades daily workload against how much they forget.
    Hardcoding the default here would silently make the column decorative.
    """
    row = conn.execute(
        "SELECT target_retention FROM learner_languages "
        "WHERE learner_id = ? AND language_code = ?",
        (learner_id, language_code),
    ).fetchone()

    if row is None:
        raise ValueError(
            f"learner {learner_id} is not enrolled in {language_code!r}; "
            f"no target_retention to schedule against"
        )

    return Scheduler(
        desired_retention=row["target_retention"],
        learning_steps=LEARNING_STEPS,
        relearning_steps=RELEARNING_STEPS,
        maximum_interval=MAXIMUM_INTERVAL_DAYS,
        enable_fuzzing=ENABLE_FUZZING,
    )


def card_from_row(row: sqlite3.Row) -> Card:
    """Rebuild the FSRS card from a stored item_state row.

    A row in state 'new' becomes a fresh Card, which is how fsrs represents an
    item at the start of its life: state Learning, step 0, no stability or
    difficulty yet. Everything else is reconstructed field for field.
    """
    if row["state"] == "new":
        return Card()

    state = STATE_TO_FSRS[row["state"]]

    # fsrs uses step=None to mean "not walking the steps", which is the case for
    # a graduated item in Review. Our column is NOT NULL, so 0 is stored in that
    # case and translated back to None here. Passing 0 instead would put a
    # Review card back onto the first learning step.
    step = None if state is State.Review else row["step_index"]

    return Card(
        state=state,
        step=step,
        stability=row["stability"],
        difficulty=row["difficulty"],
        due=from_db_time(row["due_at"]),
        last_review=from_db_time(row["last_reviewed_at"]),
    )


def review(
    conn: sqlite3.Connection,
    learner_id: int,
    content_type: str,
    content_id: int,
    exercise_type: str,
    rating: int,
    reviewed_at: datetime | None = None,
) -> dict:
    """Apply one review: append to review_log, then update item_state.

    Returns a summary dict describing what changed, so callers can report
    honestly rather than assuming the write landed as expected.

    The ordering inside the transaction matters. The before-state is captured
    from the row as it stands, written to review_log, and only then is
    item_state overwritten. review_log is append-only and is the irreplaceable
    asset here: item_state can be rebuilt by replaying the log, but nothing can
    rebuild the log. See memory/review-log-is-append-only.md.
    """
    if rating not in (1, 2, 3, 4):
        raise ValueError(f"rating must be 1 to 4, got {rating!r}")

    now = reviewed_at or datetime.now(timezone.utc)

    row = conn.execute(
        "SELECT * FROM item_state WHERE learner_id = ? "
        "AND content_type = ? AND content_id = ?",
        (learner_id, content_type, content_id),
    ).fetchone()

    if row is None:
        raise ValueError(
            f"no item_state row for learner {learner_id}, "
            f"{content_type} {content_id}; it was never scheduled"
        )

    scheduler = scheduler_for(conn, learner_id, row["language_code"])
    card = card_from_row(row)

    # Capture the scheduler inputs as they stood BEFORE this review. This is the
    # part that makes the log replayable for FSRS parameter refitting later;
    # storing only the resulting state would not be enough to reconstruct what
    # the model was asked to predict.
    last_review = from_db_time(row["last_reviewed_at"])
    due_before = from_db_time(row["due_at"])

    # Days actually elapsed since the previous review, and days that had been
    # scheduled between those two points. Both NULL on a first review, which is
    # correct rather than zero: no time has elapsed since a review that never
    # happened, and nothing was scheduled.
    elapsed_days = None
    scheduled_days = None
    if last_review is not None:
        elapsed_days = (now - last_review).total_seconds() / 86400
        if due_before is not None:
            scheduled_days = (due_before - last_review).total_seconds() / 86400

    updated_card, _ = scheduler.review_card(
        card, Rating(rating), review_datetime=now
    )

    # A lapse is failing an item that had graduated, not failing one that is
    # still being learned. Getting a brand-new word wrong on its second minute
    # is the learning process working, and counting it as a lapse would inflate
    # the number that is supposed to flag genuinely troublesome items.
    is_lapse = rating == 1 and row["state"] == "review"

    new_state = FSRS_TO_STATE[updated_card.state]
    new_step = 0 if updated_card.step is None else updated_card.step

    with conn:
        conn.execute(
            """
            INSERT INTO review_log (
                learner_id, content_type, content_id, exercise_type,
                reviewed_at, rating,
                stability_before, difficulty_before, elapsed_days, scheduled_days
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                learner_id, content_type, content_id, exercise_type,
                to_db_time(now), rating,
                row["stability"], row["difficulty"], elapsed_days, scheduled_days,
            ),
        )

        conn.execute(
            """
            UPDATE item_state
               SET state = ?, step_index = ?, stability = ?, difficulty = ?,
                   due_at = ?, last_reviewed_at = ?,
                   reps = reps + 1, lapses = lapses + ?
             WHERE learner_id = ? AND content_type = ? AND content_id = ?
            """,
            (
                new_state, new_step, updated_card.stability, updated_card.difficulty,
                to_db_time(updated_card.due), to_db_time(now),
                1 if is_lapse else 0,
                learner_id, content_type, content_id,
            ),
        )

    return {
        "state_before": row["state"],
        "state_after": new_state,
        "step_index": new_step,
        "stability": updated_card.stability,
        "difficulty": updated_card.difficulty,
        "due_at": to_db_time(updated_card.due),
        "interval_days": (updated_card.due - now).total_seconds() / 86400,
        "was_lapse": is_lapse,
    }


def introduced_today(
    conn: sqlite3.Connection,
    learner_id: int,
    language_code: str,
    now: datetime,
) -> int:
    """Count items whose very first review happened today, in UTC.

    This is what the daily new limit is actually capping. Counting today's
    reviews instead would be wrong twice over: it would count repeat reviews of
    the same new item, and it would count reviews of long-familiar items.
    """
    start_of_day = to_db_time(now.astimezone(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    ))

    return conn.execute(
        """
        SELECT count(*) FROM (
            SELECT r.content_id, min(r.reviewed_at) AS first_seen
              FROM review_log r
              JOIN item_state s
                ON s.learner_id = r.learner_id
               AND s.content_type = r.content_type
               AND s.content_id = r.content_id
             WHERE r.learner_id = ? AND s.language_code = ?
             GROUP BY r.content_type, r.content_id
        ) WHERE first_seen >= ?
        """,
        (learner_id, language_code, start_of_day),
    ).fetchone()[0]


def due_queue(
    conn: sqlite3.Connection,
    learner_id: int,
    language_code: str,
    now: datetime | None = None,
    extra_new_allowance: int = 0,
) -> list[sqlite3.Row]:
    """Build the review queue: everything overdue, then new items up to the cap.

    Returns item_state rows. Turning those into something a person can answer is
    the exercise layer's job, not this one's, which is why nothing here joins to
    lexical_items.

    Ordering is deliberate and slightly awkward. Due items come first and in due
    order, because the most overdue item is the one closest to being forgotten.
    New items follow, ordered only by content_id. It is tempting to order them
    by frequency rank so common words are learned first, and that ordering is a
    real improvement, but it belongs to whatever assembles a study session: this
    module cannot see frequency_rank without joining a content table, and the
    moment it does that it stops working for sentences.
    """
    now = now or datetime.now(timezone.utc)
    now_text = to_db_time(now)

    # Overdue items. A single-table query against item_state, which is why
    # language_code is denormalized onto it: this runs on every app launch.
    due = conn.execute(
        """
        SELECT * FROM item_state
         WHERE learner_id = ? AND language_code = ?
           AND state != 'new' AND due_at IS NOT NULL AND due_at <= ?
         ORDER BY due_at
        """,
        (learner_id, language_code, now_text),
    ).fetchall()

    limit_row = conn.execute(
        "SELECT daily_new_limit FROM learner_languages "
        "WHERE learner_id = ? AND language_code = ?",
        (learner_id, language_code),
    ).fetchone()

    if limit_row is None:
        raise ValueError(
            f"learner {learner_id} is not enrolled in {language_code!r}"
        )

    # Remaining allowance for today. max(0, ...) because the limit can be
    # lowered between sessions, which would otherwise produce a negative LIMIT.
    #
    # extra_new_allowance is added rather than replacing the limit, and it is
    # the caller's business how it was earned. Today the only caller that passes
    # a non-zero value is the browser's "go again" control, which grants one
    # further daily allowance when the queue is otherwise empty, so a learner
    # who wants to keep going can. It is deliberately NOT unlimited: 60 unseen
    # words introduced in one sitting would all come back over the following
    # days, and the learner would be punished tomorrow for enthusiasm today by a
    # mechanism invisible to them at the moment they chose it.
    #
    # It is a per-call argument rather than stored state, so it cannot outlive
    # the session that granted it or leak into the terminal runner.
    remaining = max(
        0,
        limit_row["daily_new_limit"]
        + extra_new_allowance
        - introduced_today(conn, learner_id, language_code, now),
    )

    new_items: list[sqlite3.Row] = []
    if remaining:
        new_items = conn.execute(
            """
            SELECT * FROM item_state
             WHERE learner_id = ? AND language_code = ? AND state = 'new'
             ORDER BY content_id
             LIMIT ?
            """,
            (learner_id, language_code, remaining),
        ).fetchall()

    return list(due) + list(new_items)
