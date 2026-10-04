# Housekeeping

How this project stops its own documentation from going stale, and what to do
when it has. `tools/housekeeping.sh` is the mechanical half; this file is the
judgement half, which a script cannot do.

Adopted 2026-09-07, ported from the atc-game project on this machine; replaced
by the claude-admin kit's version 2026-10-04, keeping this project's own items
(the framework check and the `word-hoard.db` question). Its "known findings"
list went: one entry contradicted the user's 2026-10-03 ruling that archiving
is always proposed, and the kit script no longer reports the other.

## Two tiers, because docs and code go stale on different clocks

Documents go stale **a little every session**: the TODO grows, the DEVLOG falls
one entry behind, a closed item is left in place. Each is cheap to fix and most
are catchable by a machine. The truth of a document, and the code, go stale
**in lumps**: a paragraph that the code now contradicts, a tool that still runs
but measures something that no longer exists. Only a person reading end to end
sees those. (Promoted from atc-game, where an audit on 2026-09-06 found its
`CLAUDE.md` saying a document "is not written yet" sixteen days after it was
written.)

| Tier | When | What | Who decides |
|---|---|---|---|
| **1. The check** | every Wrap Up | `bash tools/housekeeping.sh`, and the archive and trim below | nobody; it takes seconds |
| **2. The pass** | a milestone closes, or the check reports 10 DEVLOG entries since the last pass | the checklist below, end to end | the user, offered it at Wrap Up |

A big finding from either tier, such as a file that needs splitting, is filed
as an ordinary TODO item with its own session. It is not done inside the pass.

## Two rules the mechanism obeys

**It reports and never blocks.** The script always exits 0. A Wrap Up that
could not finish because a document was stale would be worse than the stale
document, and a check that is wrong often gets switched off.

**It names what is due and the evidence.** "10 entries since the last pass on
2026-08-01" can be weighed and declined in one word. "It has been a while" is a
chore with nothing in it to decide.

## Tier 1: every Wrap Up

```bash
bash tools/housekeeping.sh
```

It checks: em and en dashes in tracked and new files; that the newest DEVLOG
entry is not older than the newest commit; closed items still in
`docs/TODO.md` and open items grown too long; how many DEVLOG entries have
passed since the last housekeeping pass; `requirements.txt` against `.venv`
when both exist; that `.claude/kit.json` and the shared hooks are in place; and
what is uncommitted. This project adds one check of its own: that nothing under
`wordhoard/` imports a web framework. Report the result in one line, "nothing
due" included.

### Archive and trim the TODO

`docs/TODO.md` holds open work, not history, and the session hook summarises it
at the start of every session, so a bloated TODO is paid for again each time.
Propose both in the Wrap Up report and act on a yes.

**Archive.** When the script reports closed items, list them and move each one
whole, with its close-date context, into the matching section of
`docs/TODO_archive.md`. Verbatim: never summarise or compress. Remove any TODO
subsection heading that empties.

**Trim.** When the script flags an open item as too long, propose a shorter one:

- a **bold headline** first (the session hook shows exactly that);
- the current status in a sentence or two;
- the next step, and what it waits on.

For every paragraph that comes out, say where it goes: into a DEVLOG entry, into
`docs/notes.md`, or nowhere because an existing entry already records it.
**Never delete detail that exists nowhere else.** A measurement that only lives
in a TODO item is still a measurement.

### Quick questions

- **Was a user-facing feature built without a `docs/TESTPLAN.md` section agreed
  first?** Say so plainly rather than backfilling the plan quietly.
- **Did the session close a milestone?** Then offer the pass.
- **Is anything in `word-hoard.db` now real?** Review data is disposable until
  the user says otherwise. Watch for them saying so, or for a `review_log`
  spread across many days rather than one burst. Once that flips, resets are
  off and the log is irreplaceable.

## Tier 2: the pass

Offered when a milestone closes or the check says it is due; done on the user's
yes. Work down the list. Most items will be nothing.

### Documentation

1. **`CLAUDE.md` is true.** Read it as if you had never seen the repository and
   check every factual claim against the tree. Its lines override default
   behaviour, so a false line there does the most harm.
2. **Every design or reference document describes what exists.** A resolved
   open question left open is worse than an unresolved one, because it will be
   planned against.
3. **`docs/DEVLOG.md` has an entry per substantive session.** The check catches
   a gap; only a person can write the entry.
4. **`docs/OVERVIEW.md`** against the refresh triggers in the global rules.
5. **`docs/TODO.md` Focus points at the present**, and every item's wording
   still matches the code.
6. **`docs/TESTPLAN.md`** has no plan marked agreed for work that was dropped,
   and no built feature still marked planned.
7. **Memory files in `memory/` still describe the present**, none repeats a
   global rule, and `MEMORY.md` indexes all of them.

### Code

8. **The tests pass**, run the way the project's `CLAUDE.md` says.
9. **`tools/` still runs and still measures the project as it is now.** This is
   the item most likely to be skipped and the most harmful when it is: a tool
   that fails loudly is harmless, a tool that prints a confident answer about
   an older version of the project is not.
10. **Dead code and stale comments.** Functions nothing calls, and comments
    predicting a future that has since arrived. Delete, or write down why it
    stays.
11. **Files that have grown a second job.** Ask the question; file a split as a
    TODO item rather than doing it here.

### Then

12. **Run `bash tools/housekeeping.sh` again.**
13. **Wrap Up as normal**, and put a `**Housekeeping pass:**` line in the DEVLOG
    entry saying what the pass found. The script counts from that line, and
    what was found tells the next pass where to look first.

## What the check cannot see

Named so nobody mistakes a quiet run for a clean project.

- **Whether a document is true.** It measures dates, sizes and counts. It
  cannot notice a paragraph the code contradicts.
- **Whether a comment still describes its function.**
- **Whether a test still tests anything.**
- **Whether a milestone closed.** The session has to say so.

Every one of those needs a person, which is what the pass is for.
