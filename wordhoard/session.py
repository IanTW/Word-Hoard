"""The review session: the loop that joins content, grading and scheduling.

Vertical slice step 5. This is the seam where the three previous steps meet.
`scheduler.py` says what is due but knows nothing about words. `exercises.py`
grades a word but knows nothing about the database. This module holds the one
piece neither of them may hold: turning a scheduler row into something a person
can be asked, and putting the resulting judgement back.

It contains no input, no output and no framework. Everything here takes
arguments and returns values, so that the terminal runner in `scripts/review.py`
and the web interface in step 6 can share every line of it rather than each
growing their own copy of the rules.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone

from wordhoard import exercises, scheduler


# Recorded as the exercise_type for the first encounter with an item, where the
# answer is shown rather than demanded. A separate value so that a later
# accuracy-by-modality report can exclude introductions, which are not tests and
# whose ratings mean something different from every other row in the log.
#
# This is exactly what review_log.exercise_type was left unconstrained for: a
# new value costs nothing, where a CHECK constraint would have cost a table
# rebuild on an append-only log.
INTRODUCTION_EXERCISE_TYPE = "introduction"

# What an introduction records. Always Good, never the grade of the typing.
#
# The learner is copying a word displayed on the screen in front of them, so a
# mismatch is a typo rather than a memory failure, and recording Again for it
# would put a false lapse into an append-only log. The measured reason this
# exists at all: the first real session on 2026-08-27 produced 9 Again ratings
# out of 17 reviews, every one of them an item the app had never shown before
# demanding it back. That 53% measured nothing except the absence of this step.
INTRODUCTION_RATING = 3


@dataclass(frozen=True)
class Question:
    """One thing to ask, fully resolved and ready to display."""

    content_type: str
    content_id: int
    prompt: str       # shown to the learner, in English
    expected: str     # what a correct answer looks like, for feedback
    item: dict        # the full content row, which the grader needs
    # True when the learner has never seen this item. It is presented as an
    # introduction (answer shown, copy it) rather than as a test, because a
    # scheduler schedules the REVIEW of something already learned and nothing in
    # this system was doing the learning.
    is_new: bool = False


def _load_lexical_item(conn: sqlite3.Connection, content_id: int) -> dict | None:
    """Fetch one vocabulary row as a plain dict."""
    row = conn.execute(
        "SELECT * FROM lexical_items WHERE id = ?", (content_id,)
    ).fetchone()
    return dict(row) if row else None


# Content type to loader. This dispatch table is the single place the
# polymorphic (content_type, content_id) pair is resolved back to real content,
# and it is deliberately HERE rather than in the scheduler. The scheduler stays
# ignorant of what it is scheduling, which is what will let sentences become
# schedulable in step 2f by adding one entry below and nothing else.
CONTENT_LOADERS = {
    "lexical_item": _load_lexical_item,
}


def build_question(
    conn: sqlite3.Connection,
    content_type: str,
    content_id: int,
    is_new: bool = False,
) -> Question | None:
    """Resolve a scheduler row into a displayable question.

    Returns None when the content cannot be shown, which is a real possibility
    rather than a defensive flourish: item_state has no foreign key onto the
    content tables by design, so a row can outlive what it points at. Returning
    None lets the caller skip it instead of crashing a review session over one
    orphaned row.
    """
    loader = CONTENT_LOADERS.get(content_type)
    if loader is None:
        return None

    item = loader(conn, content_id)
    if item is None:
        return None

    # The English prompt. A drillable item without one is unanswerable, and the
    # import script refuses to create scheduler rows for such items, so reaching
    # this branch means something bypassed the import. Skip rather than show a
    # blank prompt and record a lapse that the learner had no chance to avoid.
    prompt = item.get("translation_en")
    if not prompt:
        return None

    return Question(
        content_type=content_type,
        content_id=content_id,
        prompt=prompt,
        expected=exercises.expected_answer(item),
        item=item,
        is_new=is_new,
    )


def next_question(
    conn: sqlite3.Connection,
    learner_id: int,
    language_code: str,
    now: datetime | None = None,
    extra_new_allowance: int = 0,
) -> Question | None:
    """The next thing to ask, or None when there is nothing due.

    Re-queries the scheduler on every call rather than caching a list at session
    start. That matters because answering changes the queue: an item failed a
    moment ago is on a one minute learning step and genuinely is due again
    within the same sitting, which is the entire purpose of learning steps.
    A cached list would silently drop that behaviour.
    """
    now = now or datetime.now(timezone.utc)

    for row in scheduler.due_queue(conn, learner_id, language_code, now=now,
                                   extra_new_allowance=extra_new_allowance):
        question = build_question(
            conn,
            row["content_type"],
            row["content_id"],
            # 'new' is this project's own state, meaning imported and scheduled
            # but never once reviewed. It is precisely the set that needs
            # teaching before testing.
            is_new=row["state"] == "new",
        )
        if question is not None:
            return question
        # An unresolvable row is skipped and the loop moves on. It is not
        # deleted: item_state may carry real review history, and this project
        # suppresses rather than deletes.
    return None


def summarise(
    conn: sqlite3.Connection,
    learner_id: int,
    language_code: str,
    since: datetime,
    now: datetime | None = None,
) -> dict:
    """Describe what happened in a session, read back out of `review_log`.

    **Every number here is derived from the log rather than counted alongside
    it.** That is the whole point of the function. A summary kept in a counter
    can drift from the history it claims to describe, and the drift is invisible
    because both numbers look plausible. Reading the log means the summary
    cannot disagree with what actually happened, and it means losing the
    session marker to a server restart costs the boundary of the session and
    never a count.

    `since` is the session boundary, supplied by the caller. This module has no
    opinion about what starts a session: the terminal has one notion, the
    browser another, and both are presentation.

    Introductions are reported separately from answers and never folded into the
    tally. An introduction is a word being taught, recorded at a fixed rating
    because a typo copied off the screen is not evidence about memory. Counting
    it as a correct answer would flatter the numbers.

    Deliberately absent: streaks, totals across sessions, accuracy percentages,
    records, personal bests. This is the exact screen where a tool like this
    reinvents the gamification it was built to avoid, so the omissions are the
    feature. See memory/no-gamification.md.
    """
    now = now or datetime.now(timezone.utc)

    # review_log carries no language_code, so the join to item_state is what
    # scopes the summary to the language being studied. It is a join rather than
    # a denormalized column because review_log is append-only history: adding a
    # column there would mean deciding what to write into every existing row.
    rows = conn.execute(
        """
        SELECT r.exercise_type, r.rating
          FROM review_log r
          JOIN item_state s
            ON s.learner_id = r.learner_id
           AND s.content_type = r.content_type
           AND s.content_id = r.content_id
         WHERE r.learner_id = ?
           AND s.language_code = ?
           AND r.reviewed_at >= ?
        """,
        (learner_id, language_code, scheduler.to_db_time(since)),
    ).fetchall()

    # Tally only the real tests. Ratings are counted by the names the learner
    # was shown during the session, so the summary and the feedback agree.
    tally = {1: 0, 2: 0, 3: 0, 4: 0}
    answered = 0
    introduced = 0
    for row in rows:
        if row["exercise_type"] == INTRODUCTION_EXERCISE_TYPE:
            introduced += 1
            continue
        answered += 1
        if row["rating"] in tally:
            tally[row["rating"]] += 1

    return {
        "answered": answered,
        "introduced": introduced,
        "tally": tally,
        "next_due_at": next_due_at(conn, learner_id, language_code, now=now),
        "since": since,
    }


def next_due_at(
    conn: sqlite3.Connection,
    learner_id: int,
    language_code: str,
    now: datetime | None = None,
) -> datetime | None:
    """When the soonest not-yet-due item becomes available, or None.

    Used to end a session honestly. "Nothing is due" and "nothing is due for
    another nine minutes because you just failed three words" are different
    situations, and a learner staring at an empty screen deserves to be told
    which one they are in.
    """
    now = now or datetime.now(timezone.utc)

    row = conn.execute(
        """
        SELECT min(due_at) AS soonest FROM item_state
         WHERE learner_id = ? AND language_code = ?
           AND state != 'new' AND due_at IS NOT NULL AND due_at > ?
        """,
        (learner_id, language_code, scheduler.to_db_time(now)),
    ).fetchone()

    return scheduler.from_db_time(row["soonest"]) if row["soonest"] else None


def answer(
    conn: sqlite3.Connection,
    learner_id: int,
    question: Question,
    typed: str,
    exercise_type: str = "typing",
    now: datetime | None = None,
) -> tuple[exercises.Grade, dict]:
    """Grade a typed answer and commit the consequences.

    Returns the grade (what to tell the learner) alongside the scheduler result
    (what happened to the item). Both are returned because the caller needs
    both and neither can be recomputed from the other.

    Note the order of operations, which is the whole point of this function:
    grade first, then schedule from the resulting rating. The grader decides
    what a right-word-wrong-gender answer is worth, and the scheduler applies
    it without opinion. Neither module can be changed into disagreeing with the
    other, because only one of them decides.
    """
    now = now or datetime.now(timezone.utc)

    grade = exercises.grade(question.item, typed)

    outcome = scheduler.review(
        conn,
        learner_id=learner_id,
        content_type=question.content_type,
        content_id=question.content_id,
        exercise_type=exercise_type,
        rating=grade.rating,
        reviewed_at=now,
    )

    return grade, outcome


def check(question: Question, typed: str) -> exercises.Grade:
    """Grade a typed answer WITHOUT recording anything.

    Exists so the introduction can let a learner retype a mis-copied word
    without each attempt becoming a row in an append-only log. Callers that
    want the answer recorded use answer() or introduce() instead.
    """
    return exercises.grade(question.item, typed)


def introduce(
    conn: sqlite3.Connection,
    learner_id: int,
    question: Question,
    typed: str,
    now: datetime | None = None,
) -> tuple[exercises.Grade, dict]:
    """Record a first encounter, where the answer was shown rather than asked.

    Grades the typing so the caller can tell the learner whether they copied it
    correctly, but always schedules at INTRODUCTION_RATING regardless. The two
    are deliberately decoupled: the grade is feedback, the rating is history,
    and a typo while copying from the screen is not evidence about memory.

    The item leaves 'new' here, so it is introduced exactly once and every
    encounter after this one is a real test.
    """
    now = now or datetime.now(timezone.utc)

    grade = exercises.grade(question.item, typed)

    outcome = scheduler.review(
        conn,
        learner_id=learner_id,
        content_type=question.content_type,
        content_id=question.content_id,
        exercise_type=INTRODUCTION_EXERCISE_TYPE,
        rating=INTRODUCTION_RATING,
        reviewed_at=now,
    )

    return grade, outcome
