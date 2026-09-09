# Housekeeping

The checklist. `tools/housekeeping.sh` is the mechanical half and runs during
Wrap Up; this file is the judgement half, which a script cannot do.

Adopted 2026-09-07, ported from the atc-game project on this machine.

## The split, and why it is a split

A script can answer "is there an em dash in a tracked file". It cannot answer
"is `docs/OVERVIEW.md` still telling the truth". Putting both in one place makes
the judgement items feel automated, and they get skimmed. Keeping them apart
means the script's output is a short list of facts and this file is a short list
of questions.

The script **reports and never fails.** It always exits 0. A Wrap Up that could
not finish because a document was stale would be worse than the stale document.

## Run it

```bash
bash tools/housekeeping.sh
```

It checks, in order: em and en dashes in tracked and new files; that nothing under
`wordhoard/` imports a web framework; that the newest `docs/DEVLOG.md` entry is
not older than the newest commit; how many closed items are still sitting in
`docs/TODO.md`; whether `requirements.txt` still matches the venv; that the dash
hooks are still wired up; and what is uncommitted.

## What the script cannot check

Work through these by hand during Wrap Up.

- **Is `docs/OVERVIEW.md` still true?** Refresh only when the session changed
  architecture, methodology, the live source or component list, a
  project-stands milestone, or a named design principle. Most sessions skip it.
  Say which, either way, so the decision is visible.
- **Does `docs/TODO.md` still describe the code?** Not just whether items are
  ticked, but whether the wording still matches what was built. Several items
  were ticked with their original wording long after the plan behind them
  changed.
- **Did anything this session belong in `memory/`?** A durable rule, a
  correction, a constraint that is not derivable from the code or the git
  history. If yes, is there an existing file that should be updated rather than
  a new one created?
- **Did a learner-facing feature get built without a `docs/TESTPLAN.md`
  section agreed first?** If so, say it plainly in the wrap-up report rather
  than backfilling the plan quietly, because a check written after the code
  tends to check what the code happens to do.
- **Is anything in `word-hoard.db` now real?** Review data is disposable until
  the user says otherwise. Watch for them saying so, or for a `review_log`
  spread across many days rather than one burst. Once that flips, resets are
  off and the log is irreplaceable.

## Known findings that are not defects

The script will keep reporting these. They are decisions, not problems.

- **Closed items in `docs/TODO.md`.** Archiving happens when the user asks, not
  on close, so the count grows on purpose. The report exists to inform that
  request, not to prompt it. 30 closed items as of 2026-09-07.
- **An empty `docs/TESTPLAN.md` planned section.** Correct until the next
  learner-facing feature starts.
