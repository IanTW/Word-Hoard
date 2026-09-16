"""Minimal due-queue web interface.

Vertical slice step 6, and the last item in the slice. What is due, answer it,
next item. No statistics, no dashboard, no settings screen.

This package is the ONLY place in the project that imports a web framework.
Nothing under `wordhoard/` imports FastAPI, and nothing should. The schema, the
review history and the scheduler are the long-lived assets here; the routing
layer is the part most likely to be thrown away. Every rule this interface
applies comes from `wordhoard.session`, which the terminal runner in
`scripts/review.py` also uses, so the two cannot drift into disagreeing about
what a correct answer is.

Run it:

    .venv/Scripts/python.exe scripts/serve.py

FastAPI's generated documentation at /docs is a genuine second interface during
a build phase, and it comes free.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode

from fastapi import Depends, FastAPI, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from wordhoard import backup, db, scheduler, session

# Which learner and language this server is serving. A module constant rather
# than a login, because there is no authentication anywhere in this system by
# design: it runs on one machine for one household. The second learner arrives
# after the slice, and will arrive as a query parameter or a picker, not as an
# account.
LEARNER_NAME: str | None = None   # None means "the only learner, whoever that is"
LANGUAGE = "de"

# Browser session state, and the only mutable module-level state in this app.
#
# It lives here rather than in wordhoard/ on purpose. A session is presentation:
# the terminal runner has its own notion of one, this has another, and neither
# belongs in the domain layer. Nothing in wordhoard/ should learn what a browser
# session is.
#
# A plain dict rather than cookies or a store because there is one learner on
# one machine with no authentication anywhere by design. The cost of being wrong
# is small and bounded: `started_at` is only a boundary for reading review_log,
# so losing it to a server restart resets what counts as "this session" and
# never loses a single recorded answer. Every number in the summary comes out of
# the log, not out of here.
_SESSION = {
    # When the current session began. Answers logged at or after this point are
    # what the summary describes.
    "started_at": datetime.now(timezone.utc),
    # Extra new-word allowance granted by "go again" this session, on top of
    # learner_languages.daily_new_limit. Reset whenever a session starts, so a
    # grant can never outlive the sitting that asked for it.
    "extra_new": 0,
}


def _start_session(now: datetime) -> None:
    """Begin a new session: move the boundary, drop any granted allowance."""
    _SESSION["started_at"] = now
    _SESSION["extra_new"] = 0

TEMPLATES = Jinja2Templates(directory=str(Path(__file__).resolve().parent / "templates"))

app = FastAPI(title="word-hoard", docs_url="/docs")


def get_conn() -> sqlite3.Connection:
    """One SQLite connection per request, closed when the request ends.

    A connection per request rather than one shared across the app because
    sqlite3 connections are not safe to use from multiple threads by default,
    and because connect() applies the foreign-key pragma per connection.
    """
    conn = db.connect()
    try:
        yield conn
    finally:
        conn.close()


def _queue_counts(conn: sqlite3.Connection, learner_id: int, now: datetime) -> dict:
    """How much work is waiting, split into the two kinds.

    Shown because a bare prompt with no sense of how much is left is
    disorienting, and because "3 left" and "3 left of 40" are different
    experiences. This is not the statistics dashboard, which stays out of scope:
    it is the size of the pile in front of you.
    """
    rows = session.scheduler.due_queue(conn, learner_id, LANGUAGE, now=now)
    return {
        "due": sum(1 for row in rows if row["state"] != "new"),
        "new": sum(1 for row in rows if row["state"] == "new"),
        "total": len(rows),
    }


@app.get("/")
def index(request: Request, conn: sqlite3.Connection = Depends(get_conn)):
    """Show the next thing to answer, or say why there is nothing.

    Feedback from the previous answer arrives in the query string rather than in
    server-side state. That is what makes the answer route a
    post-then-redirect-then-get: refreshing this page cannot re-submit an
    answer, and a stray reload therefore cannot write a second row into an
    append-only log.
    """
    learner_id, learner_name = db.find_learner(conn, LEARNER_NAME)
    now = datetime.now(timezone.utc)

    question = session.next_question(conn, learner_id, LANGUAGE, now=now,
                                     extra_new_allowance=_SESSION["extra_new"])

    context = {
        "learner_name": learner_name,
        "question": question,
        "counts": _queue_counts(conn, learner_id, now),
        # Feedback carried over from the last answer, if any.
        "feedback": request.query_params.get("msg"),
        "feedback_ok": request.query_params.get("ok") == "1",
        "next_in": request.query_params.get("next_in"),
    }

    if question is None:
        soonest = session.next_due_at(conn, learner_id, LANGUAGE, now=now)
        context["soonest"] = soonest
        context["soonest_minutes"] = (
            (soonest - now).total_seconds() / 60 if soonest else None
        )

    # Starlette 1.x takes the request as the first argument. The older
    # signature, which passed "request" inside the context dict, fails here with
    # an unhelpful "unhashable type: 'dict'" from the Jinja template cache.
    return TEMPLATES.TemplateResponse(request, "index.html", context)


@app.get("/finish")
def finish(request: Request, conn: sqlite3.Connection = Depends(get_conn)):
    """End the session and show what happened. Reads, never writes.

    A GET rather than a POST because finishing changes nothing: it queries
    review_log for the rows logged since the session began and renders them.
    That is also why refreshing it is harmless, which matters on a page whose
    whole neighbourhood is built around not letting a reload write a second row
    into an append-only log.

    The session boundary is not moved here. A learner who finishes and then
    presses back into the queue is still in the same session, and their summary
    still describes all of it. Only "go again" starts a new one.
    """
    learner_id, learner_name = db.find_learner(conn, LEARNER_NAME)
    now = datetime.now(timezone.utc)

    summary = session.summarise(
        conn, learner_id, LANGUAGE, since=_SESSION["started_at"], now=now)

    soonest = summary["next_due_at"]
    return TEMPLATES.TemplateResponse(request, "finished.html", {
        "learner_name": learner_name,
        "summary": summary,
        "soonest": soonest,
        "soonest_minutes": (soonest - now).total_seconds() / 60 if soonest else None,
        "counts": _queue_counts(conn, learner_id, now),
    })


@app.post("/again")
def again(conn: sqlite3.Connection = Depends(get_conn)):
    """Start a fresh session, granting more new words only if none are due.

    A POST because it mutates session state, and so that a refresh of the page
    it redirects to cannot silently grant another allowance.

    **The grant is conditional and bounded, and both halves matter.**
    Conditional: an allowance is added only when the queue is genuinely empty,
    which is exactly what was asked for. Granting one whenever the button was
    pressed would quietly inflate the daily new count on ordinary sessions where
    the learner simply wanted to carry on.

    Bounded: one further daily allowance per press, not an unlimited cap. There
    are around sixty unseen words; introducing all of them in one sitting would
    hand every one of them back over the following days, and the learner would
    be punished tomorrow for enthusiasm today by a mechanism they could not see
    when they chose it. Pressing again grants another.
    """
    learner_id, _ = db.find_learner(conn, LEARNER_NAME)
    now = datetime.now(timezone.utc)

    # Asked with NO allowance, deliberately: the question is whether there is
    # work under the ordinary daily rules, not whether a previous grant is still
    # unspent. Asking with the current grant conflates the two, and the first
    # version of this function did exactly that: pressing the button twice
    # revoked the allowance it had just given, so a word appeared and then
    # vanished. Caught by the plan's own "not cumulative" check.
    still_due = session.next_question(
        conn, learner_id, LANGUAGE, now=now, extra_new_allowance=0) is not None

    _start_session(now)
    if not still_due:
        # The invariant is "one daily allowance of new words is available from
        # now", not "add ten to a counter". Setting the extra to the number
        # already introduced today makes the scheduler's arithmetic
        #     remaining = daily_limit + extra - introduced_today
        # come out at exactly daily_limit, however many have already been
        # learned today. Without this the grant silently does nothing the second
        # time: introduced_today has grown past the raised cap, and remaining
        # falls back to zero.
        #
        # It also cannot compound. However many times the button is pressed, at
        # most one allowance is ever available at once.
        _SESSION["extra_new"] = scheduler.introduced_today(
            conn, learner_id, LANGUAGE, now)

    return RedirectResponse("/", status_code=303)


@app.post("/answer")
def answer(
    content_type: str = Form(...),
    content_id: int = Form(...),
    is_new: str = Form("0"),
    typed: str = Form(""),
    conn: sqlite3.Connection = Depends(get_conn),
):
    """Record one answer, then redirect back to the queue.

    The posted content_id is trusted as the item that was on screen rather than
    re-derived from the queue. Re-deriving would be wrong: between rendering and
    submitting, the queue can legitimately change (a learning step elapses), and
    grading the typed answer against whatever is at the head of the queue *now*
    would score it against a different word entirely.
    """
    learner_id, _ = db.find_learner(conn, LEARNER_NAME)
    now = datetime.now(timezone.utc)

    question = session.build_question(conn, content_type, content_id)
    if question is None:
        # The content vanished between render and submit. Nothing to record;
        # send them back to the queue rather than failing the request.
        return RedirectResponse("/", status_code=303)

    if is_new == "1":
        grade, outcome = session.introduce(conn, learner_id, question, typed, now=now)
    else:
        grade, outcome = session.answer(conn, learner_id, question, typed, now=now)

    # Back up immediately, before the redirect. The row just written to
    # review_log is append-only history that nothing can reconstruct, and the
    # database file is gitignored, so until this runs the only copy of that
    # answer is on one disk in one file.
    #
    # Exporting on every single answer rather than on some interval or at a
    # session end, for two reasons. There is no notion of a session in this
    # interface yet, which is TODO 6b and M2. And the cost is genuinely
    # negligible: the whole export is a few hundred kilobytes at the current 74
    # items and stays small at the 1300 target, so per-answer is affordable and
    # means a crash can never lose more than zero reviews.
    #
    # export_quietly, never export. A backup failure must not turn a successful
    # review into a 500 and cost the learner the answer they just gave. The
    # answer is already committed by this point; the worst case here is a stale
    # backup, and the loud path (scripts/export_backup.py) is how that gets
    # noticed.
    # Defaults, because get_conn() above calls db.connect() with defaults too:
    # this app always serves the project database. If that ever becomes
    # configurable, both call sites change together or the backup silently
    # starts protecting the wrong file.
    backup.export_quietly()

    # 303 rather than 302, so the browser reliably turns the POST into a GET.
    params = urlencode({
        "msg": grade.feedback,
        "ok": "1" if grade.correct else "0",
        "next_in": _describe_interval(outcome["interval_days"]),
    })
    return RedirectResponse(f"/?{params}", status_code=303)


def _describe_interval(days: float) -> str:
    """Render a scheduled interval the way a person would say it.

    Duplicated in scripts/review.py, and deliberately not shared. It is
    presentation, and the terminal and the browser are entitled to word things
    differently. The moment they must agree, it moves into wordhoard.
    """
    minutes = days * 24 * 60
    if minutes < 90:
        return f"{minutes:.0f} min"
    if days < 1:
        return f"{minutes / 60:.0f} hours"
    if days < 60:
        return f"{days:.0f} days"
    return f"{days / 30.44:.0f} months"
