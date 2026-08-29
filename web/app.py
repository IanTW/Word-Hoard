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

from wordhoard import db, session

# Which learner and language this server is serving. A module constant rather
# than a login, because there is no authentication anywhere in this system by
# design: it runs on one machine for one household. The second learner arrives
# after the slice, and will arrive as a query parameter or a picker, not as an
# account.
LEARNER_NAME: str | None = None   # None means "the only learner, whoever that is"
LANGUAGE = "de"

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

    question = session.next_question(conn, learner_id, LANGUAGE, now=now)

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
