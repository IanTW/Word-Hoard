"""Run a review session in the terminal.

Vertical slice step 5, and the first point at which this project is a usable
thing rather than a set of parts. Run:

    .venv/Scripts/python.exe scripts/review.py
    .venv/Scripts/python.exe scripts/review.py --limit 20

All the rules live in `wordhoard/session.py`. This file is only input and
output: prompts, typed answers, feedback and a closing summary. That split is
deliberate rather than tidy-minded. Step 6 puts a web interface on the same
loop, and if the rules lived here they would have to be written twice and would
then quietly disagree.
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

# Allow running this file directly. Same trick as the other scripts.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from wordhoard import db, session  # noqa: E402  (must follow the sys.path fix)

# Typed instead of an answer to leave the session. Not a bare empty line,
# because an empty line is a real answer meaning "I do not know", which is a
# legitimate and common thing to submit and which correctly rates as Again.
QUIT_COMMANDS = {":q", ":quit"}

# What each FSRS rating is called when reported back to the learner. The raw
# integers mean nothing to a person mid-session.
RATING_NAMES = {1: "again", 2: "nearly", 3: "good"}

# How many times a learner may retype a new word before the session moves on.
# A cap rather than an unbounded loop, so that a character the keyboard cannot
# produce never traps somebody on one word. Three is a guess, not a measurement.
MAX_COPY_ATTEMPTS = 3


def describe_interval(days: float) -> str:
    """Render a scheduled interval the way a person would say it."""
    minutes = days * 24 * 60
    if minutes < 90:
        return f"{minutes:.0f} min"
    if days < 1:
        return f"{minutes / 60:.0f} hours"
    if days < 60:
        return f"{days:.0f} days"
    return f"{days / 30.44:.0f} months"


def run_session(conn, learner_id: int, learner_name: str, language: str, limit: int | None) -> int:
    """Ask questions until the queue empties, the limit is hit, or the user quits.

    Returns the number of answers recorded, which is the honest measure of what
    the session did. A session that was quit after two answers has still written
    two rows to review_log, and those are permanent.
    """
    asked = 0
    introduced = 0
    tally = {1: 0, 2: 0, 3: 0}

    print(f"\nReviewing {language} as {learner_name}. Type :q to stop.\n")

    while limit is None or (asked + introduced) < limit:
        # The clock is read fresh each time rather than fixed at session start,
        # so an item on a one minute learning step really does come back inside
        # the session once that minute has passed.
        now = datetime.now(timezone.utc)

        question = session.next_question(conn, learner_id, language, now=now)
        if question is None:
            break

        # A brand-new item is taught, not tested. Everything after its first
        # encounter is a real test.
        handler = _introduce if question.is_new else _test
        result = handler(conn, learner_id, question, now)

        if result is None:      # the learner quit
            break
        if question.is_new:
            introduced += 1
        else:
            asked += 1
            tally[result] += 1

    _print_summary(conn, learner_id, language, asked, introduced, tally)
    return asked + introduced


def _read(prompt: str) -> str | None:
    """Read one line. None means the session should end.

    Ctrl+C and a closed stdin both end things cleanly rather than raising.
    Nothing is ever half-written, because each answer is committed as it is
    given, so an interrupted session keeps everything already answered.
    """
    try:
        typed = input(prompt)
    except (EOFError, KeyboardInterrupt):
        print()
        return None

    if typed.strip().lower() in QUIT_COMMANDS:
        # The prompt has already been printed, so without a newline the summary
        # appears to be the answer to it.
        print()
        return None
    return typed


def _test(conn, learner_id: int, question, now) -> int | None:
    """Ask a known item and grade it. Returns the rating, or None if quit."""
    typed = _read(f"  {question.prompt}\n  > ")
    if typed is None:
        return None

    grade, outcome = session.answer(conn, learner_id, question, typed, now=now)

    mark = "ok " if grade.correct else "no "
    print(f"  {mark}{grade.feedback}")
    print(
        f"     [{RATING_NAMES[grade.rating]}] next in "
        f"{describe_interval(outcome['interval_days'])}\n"
    )
    return grade.rating


def _introduce(conn, learner_id: int, question, now) -> int | None:
    """Teach a new item: show the answer, have it copied, then record it.

    The retry loop writes nothing. Copying from the screen is a typing test, not
    a memory test, so a mismatch earns another go rather than a row in an
    append-only log. Capped at MAX_COPY_ATTEMPTS so a stubborn umlaut or a
    keyboard the learner cannot produce never traps them in the loop.
    """
    print(f"  new   {question.prompt}")
    print(f"        {question.expected}")

    typed = ""
    for attempt in range(1, MAX_COPY_ATTEMPTS + 1):
        typed = _read("        type it: ")
        if typed is None:
            # Quitting mid-introduction records nothing, so the item stays 'new'
            # and gets introduced properly next session rather than being
            # silently counted as taught.
            return None

        if session.check(question, typed).correct:
            break

        if attempt < MAX_COPY_ATTEMPTS:
            print(f"        not quite, copy it exactly: {question.expected}")
        else:
            print(f"        moving on. it was {question.expected}")

    # Recorded exactly once, however many attempts it took. The retries are the
    # learner's business; the log records that the item was taught.
    _, outcome = session.introduce(conn, learner_id, question, typed, now=now)
    print(f"        learned. next in {describe_interval(outcome['interval_days'])}\n")
    return session.INTRODUCTION_RATING


def _print_summary(
    conn, learner_id: int, language: str, asked: int, introduced: int, tally: dict
) -> None:
    """Close the session by saying what happened and what is left.

    Reports the *reason* the queue is empty, because "nothing is due" and
    "nothing is due for another nine minutes because you just failed three
    words" are different situations and the learner deserves to know which.
    """
    # Introductions are reported separately from answers, and never folded into
    # the accuracy tally. They are not tests, and counting a taught word as a
    # correct answer would flatter the numbers.
    if introduced:
        print(f"  {introduced} new word{'s' if introduced != 1 else ''} learned.")
    if asked:
        print(f"  {asked} answered: {tally[3]} good, {tally[2]} nearly, {tally[1]} again.")
    if not asked and not introduced:
        print("  Nothing was due.\n")

    soonest = session.next_due_at(conn, learner_id, language)
    if soonest is None:
        print("  Queue empty. Nothing else is scheduled.\n")
        return

    minutes = (soonest - datetime.now(timezone.utc)).total_seconds() / 60
    if minutes < 60:
        print(f"  Next item due in {max(0, minutes):.0f} min.\n")
    else:
        print(f"  Next item due {soonest.strftime('%Y-%m-%d %H:%M')} UTC.\n")


def main() -> int:
    """Parse arguments, open the database, run one session."""
    # German content contains umlauts and the Windows console does not default
    # to UTF-8. Without this, printing 'die Bäckerei' either mangles it or
    # raises UnicodeEncodeError mid-session.
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass  # Not a reconfigurable stream, for instance when piped in a test.

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default=db.DEFAULT_DB_PATH,
                        help=f"Database file (default: {db.DEFAULT_DB_PATH.name})")
    parser.add_argument("--learner",
                        help="Learner display name. Optional when only one exists.")
    parser.add_argument("--language", default="de", help="Language code (default: de)")
    parser.add_argument("--limit", type=int,
                        help="Stop after this many answers. Default: until the queue empties.")
    args = parser.parse_args()

    db_path = Path(args.db)
    if not db_path.exists():
        print(f"error: {db_path} does not exist; run scripts/init_db.py first",
              file=sys.stderr)
        return 1

    conn = db.connect(db_path)
    try:
        learner_id, learner_name = db.find_learner(conn, args.learner)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    run_session(conn, learner_id, learner_name, args.language, args.limit)
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
