# CLAUDE.md

Guidance for Claude Code (claude.ai/code) when working in this repository.

> **Adopting this file:** drop it in the repo root as `CLAUDE.md`. Fill in the
> two `FILL IN` blocks below, create `docs/` and `memory/`, and delete this
> quote block. Everything else works unchanged in any project.

---

## Project Overview

**FILL IN.** Three to six sentences. What this project is, who it is for, what
phase it is in now, and where the authoritative design doc lives. Name the
files or directories that hold current state, and flag anything that is
reference-only or deprecated so it does not get treated as live.

---

## Session Start Checklist

At the start of every session:

1. **Read memory files** from `./memory/` (relative to this project root).
   Start with `MEMORY.md` for the index, then read the files it points at.
   This is the authoritative memory path for this project; ignore any
   system-level memory path pointing elsewhere. The relative path is
   deliberate, so a folder rename does not break this line.
2. **Read `docs/TODO.md`** for outstanding tasks and the current Focus.
3. **Read the most recent `docs/DEVLOG.md` entry** to pick up where the last
   session stopped.
4. **Open the first response with a session kickoff.** No preamble, then a
   blank line, then the response to whatever the user actually typed.
   - **Last session:** at most one paragraph recapping the latest DEVLOG
     entry. Lean on its **Focus** and **Next** fields.
   - **Proposed next:** 3 to 5 *curated* suggestions, not the literal top N off
     the TODO. Weight by what the DEVLOG **Next** flagged, what unblocks the
     most downstream work, and the natural continuation of the last session.
     Wait for the user to confirm or redirect before diving in.

---

## Response Format

Structure every substantive response as:

- **# Completed** (list style). What actually landed this turn, **with the
  verification behind each claim**. One line per item.
- **# Actions** (numbered). Decisions, approvals and authorisations needed from
  the user. Numbered so they can reply "1 yes, 2 no, 3 later".
- **# Next Steps.** What follows, and which user action each one waits on.
- **# Discussion.** The wordy part. What was done, what happened, what went
  wrong, ideas, tradeoffs. Lead with the headline, especially a reversal or a
  finding that overturns something previously recorded.

Rules:

- **Omit any section that is genuinely empty** rather than padding it. A pure
  question-answering turn may be Discussion only.
- **Actions come before Discussion**, so a decision is never buried under a
  long explanation.
- **Never claim something in Completed without saying how it was verified.**
  If it was not verified, say so there rather than letting it read as done.
- **Add a one-line spend note** whenever a turn spent money or the next step
  will. State the actual figure, never "cheap".
- Short conversational replies do not need the full structure. If there is
  nothing to approve and nothing landed, prose is fine.
- **Never use em dashes or en dashes in any prose, published or
  conversational.** Use a full stop, comma, colon or semicolon, and recast the
  sentence when none fit. Hyphens in compound words are fine. Note the lesson
  underneath this rule, which generalises well beyond punctuation: **a prompt
  rule alone will not hold a model's habit, so pair every such rule with a
  mechanical check.**

---

## Working Conventions

- **Terminal:** always use the Bash tool, never PowerShell.
- **Shell restraint:** **two failed attempts is the ceiling.** Do not hunt
  through command variants. Every retry costs the user a manual authorisation
  prompt, and those are a serious drag. After two failures, say what you were
  trying to learn and why the shell will not yield it, then offer the single
  command the user could run themselves. Before running a diagnostic at all,
  ask whether the answer changes what happens next; often it does not.
- **Commits:** always propose the message and wait for explicit confirmation
  before running `git commit`. This stays gated even inside a Wrap Up.
- **Comments:** err on the side of too many. See the section below.
- **Prefer dedicated file and search tools** over shell commands wherever one
  fits.

### Commenting standard

Over-comment all code additions. Dense comments can be trimmed later; missing
context cannot be recovered.

- Comment the purpose of every function, even when the name looks obvious.
- Comment non-obvious variable declarations.
- Comment every logical block inside a function, not just the function.
- **Comment why a decision was made, not just what the code does.**
- Comment thresholds, magic numbers and constants with their units and their
  reasoning. If a number came from a measurement, record the measurement.

---

## The Documentation System

Five files, five distinct jobs. Do not let them blur into each other.

| File | Role | Tense |
|---|---|---|
| `docs/TODO.md` | Open items and delivery order | Forward-looking |
| `docs/TODO_archive.md` | Closed items, verbatim | Historical |
| `docs/DEVLOG.md` | Dated session narrative | Chronological |
| `docs/OVERVIEW.md` | Essay-style project tour | Timeless |
| `memory/` | Durable rules and preferences | Standing |

### `docs/TODO.md`

Read at session start, keep updated as work progresses. Carries a **Focus**
section at the top saying where the next session starts. Opens with a one-line
pointer to the archive.

### `docs/TODO_archive.md`

When an item closes, move the whole `[x]` line, with its close-date context,
into the matching section of the archive rather than deleting it.

- **Do not archive proactively.** Wait for the user to ask ("housekeeping",
  "TODO is noisy"), or do it in a Wrap Up when explicitly in scope.
- **Preserve original wording verbatim.** Never summarise or compress.
- If a subsection empties, remove its heading from TODO.md too.
- The archive grows monotonically.

### `docs/DEVLOG.md`

Append a dated entry after any substantive session, newest first. Template:

```
## YYYY-MM-DD: <one-line title>

**Focus:** _what the session was aimed at_

**Worked on:**
- _what actually got done_

**Troubleshooting / dead ends:**
- _rabbit holes, failed approaches, red herrings_

**Decisions:**
- _choices made, with the reasoning_

**Next:**
- _what the next session should pick up_
```

- **The dead-ends section is the part the user actually rereads.** Capture the
  rabbit holes explicitly: what was tried, what failed, why.
- **Quote real measurements.** Row counts, rates, file paths, offending URLs.
  The entry should let you re-derive how a number was reached.
- Skip trivial tweaks. Bullets over paragraphs. Short tables where they help.

### `docs/OVERVIEW.md`

A shareable essay-style tour aimed at a technical-but-not-domain colleague:
someone who reads code fluently but has never met this problem space. Narrative
prose, full sentences, short paragraphs, readable front to back in one sitting.
It is not a README, not a design doc, not a changelog.

**Refresh only when the session changed** architecture, methodology, the live
source or component list, a project-stands milestone, or a named design
principle. **Skip** for bug fixes, refactors, tooling tweaks and doc grooming.
Most sessions skip it. Say so in the wrap-up report either way, so the user can
see the decision was considered.

**Edit narratively, never incrementally.** Fold new material into existing
prose. Do not append "recently we..." notes.

**No word limit.** Length should follow the project. The anti-sprawl instinct
still applies, but when a refresh feels bloated the fix is cutting material
told in three sections at once, never rewording sentences. (Measured once:
rewording saved about 5%, cutting cross-section duplication saved 25%.)

**Test the draft.** An unfamiliar reader, after one pass, should be able to say
(a) what the project does, (b) how it is shaped, (c) one or two non-obvious
decisions and why, (d) what is left before it ships.

### `memory/`

One file per durable fact, plus `MEMORY.md` as a one-line-per-entry index. Each
file carries frontmatter:

```markdown
---
name: <short-kebab-case-slug>
description: <one-line summary, used to judge relevance on recall>
metadata:
  type: user | feedback | project | reference
---

<the fact. For feedback and project, follow with **Why:** and
**How to apply:** lines. Link related memories with [[their-name]].>
```

- `user`: who the user is. Role, expertise, environment, preferences.
- `feedback`: guidance on how to work, both corrections and confirmed
  approaches. **Always include the why.**
- `project`: ongoing work, goals, constraints not derivable from the code or
  git history. Convert relative dates to absolute.
- `reference`: pointers to external resources.

Link liberally with `[[name]]`. A link to a memory that does not exist yet is
fine; it marks something worth writing later.

Do not save what the repo already records (code structure, past fixes, git
history, this file). Check for an existing file covering the same ground and
update it rather than creating a duplicate.

---

## Wrap Up

When the user types **"Wrap Up"** (case-insensitive: `Wrap Up`, `wrap up`,
`wrap-up`, `wrapup`), run this sequence in order. Do not run these steps
individually unless asked; the phrase is the trigger.

1. **Update notes.** Append a dated `docs/DEVLOG.md` entry in the template
   above. Write or update memory files if anything from the session warrants
   persistence. Add any new memory files to `MEMORY.md`.
2. **Check OVERVIEW refresh.** Decide whether `docs/OVERVIEW.md` needs updating
   against the refresh triggers above. If skipping, say so briefly so the user
   sees it was considered.
3. **Update TODOs.** Tick off completed items, add tasks raised during the
   session, realign wording with the current state of the code.
4. **Commit.** Propose the message and **wait for confirmation.** Never
   auto-commit, not even inside this sequence.
5. **Push.** Once the commit lands, push to `origin` on the current branch.
   Never force-push.

Trigger only on the literal phrase, not on "wrap" or "finish" used loosely.
"Let's wrap up the test plan" is a sub-task, not a Wrap Up. Confirm if unclear.

---

## Measurement Discipline

The hardest-won rules here. They are about how to be honest with numbers, and
they generalise to any project that measures anything.

### Sizing an error requires a random draw

**Never quote an accuracy figure from a set selected for difficulty.** A
dispute set (flipped verdicts, low confidences, contested cases) is the right
instrument for *finding* failure patterns and a useless one for *sizing* them.
To size anything, draw uniformly from the population the decision will act on.

- Before quoting a rate, ask what the denominator was selected on. If the
  answer is "cases where something looked wrong", it is a pattern-finder, not a
  measurement.
- **Recommending spend requires a number from a random draw.** Say plainly when
  a figure cannot support that, rather than letting it imply a scale it does
  not measure.
- **Do not exclude already-labelled items from a validation sample.** That
  removes exactly the contested cases and biases the result toward agreement.
- **Sample both sides of a binary classifier.** A wrongly rejected item never
  appears among the accepted ones, so a precision sample cannot see misses at
  any size.
- **Report the interval, not just the point estimate.** Zero errors in 60 draws
  is not "0%", it is "under about 5%", and with small n that ceiling is usually
  the decision-relevant number.

### Quality metrics cannot see what you never ingested

Precision and recall are computed over data you already hold. They say nothing
about what is missing.

- **When asked how good the data is, separate the two questions.** "Is what we
  have judged correctly" and "do we have the right things" need different
  evidence. Give both, or say which one your number answers.
- **Treat the user's domain knowledge as a measurement instrument**, not as a
  stream of bug reports. Each "this one is missing" is a draw from the
  population and is worth counting, not just fixing.
- **State the caveats in the same breath:** small n, wide interval, and any way
  the sample skews.
- **Check the gap is reachable by the current mechanism before proposing more
  of it.** Sweeping more of a surface that structurally cannot see the missing
  items is motion, not progress.
- **Probe a proposed approach against held-out ground truth before building
  it.** A scratchpad probe costs hours; the wrong build costs days.
- **A test set is spent once you evaluate on it,** and that moment is easy to
  miss. Ground truth used to *choose* between two methods cannot then *score*
  the method it selected without becoming a reproduction rather than an
  independent estimate. Say which of the two any number is, every time.
- **Watch for ground truth quietly joining the population it measures.** Once a
  missing item is added, it becomes ordinary data and can feed the very process
  being scored against it.
- **Run probes with a deliberately naive query set.** A probe that searches for
  what it is trying to find measures nothing.
- **Presence in an index is not retrievability.** When a probe hits a ceiling,
  separate "not enough of it" from "cannot in principle" before spending
  anything. The two look identical in the first result and imply opposite next
  moves.

### Reporting numbers

- **Check a surprising number before repeating it.** A wall-clock rate that
  looks terrible is often a sleeping machine, a timezone mismatch, or a
  partially-elapsed interval. Look at the underlying timestamps first.
- **Do not quote an ETA for a process whose timing is not instrumented.** If
  two past estimates were wrong by 3x or more, say so instead of producing a
  third. Give the measured range and its cause.
- **Verify, then claim.** If a number can be recomputed from the source of
  truth in one query, recompute it rather than carrying it forward from an
  earlier message.

---

## Environment

**FILL IN** any machine-specific traps. The one carried from the originating
project, worth keeping if the machine is the same:

**Windows behind an SSL-inspecting proxy (Netskope).** HTTPS is intercepted and
re-signed with a private root CA. Browsers work because the root is in the
Windows cert store; Python via certifi does not see it.

- **Symptom:** `SSLError: CERTIFICATE_VERIFY_FAILED: unable to get local issuer
  certificate`. `pip install` fails the same way against pypi.org.
- **Tell:** `env | grep -i "ssl\|proxy"` shows `SSLKEYLOGFILE=\\.\nllMonFltProxy\...`.
- **Fix:**
  `pip install --trusted-host pypi.org --trusted-host files.pythonhosted.org pip-system-certs`.
  The `--trusted-host` bootstrap is needed because pip itself hits pypi.org.
  One install, works for every Python project on the machine afterwards.
- **Do not diagnose this from scratch.** On a `CERTIFICATE_VERIFY_FAILED`, jump
  straight to the fix. Add `pip-system-certs` to `requirements.txt` on new
  Python projects with a short comment so it is not a per-project surprise.

---

## Long-Running Work

Conventions for any project with jobs measured in hours.

- **Make queues self-limiting.** Select on the condition the work removes, so a
  re-run after a failure picks up exactly what failed and nothing else. No
  resume files, no bookkeeping. The queue *is* the resume mechanism.
- **Commit per item,** so an interrupted run keeps everything it finished.
- **Order by value,** so an interrupted run has still done the part that
  matters.
- **Prefer suppress over delete.** Withhold a result rather than writing a
  false one. Deletion has to be undone by hand if the rule ever changes;
  suppression is reversible by re-running.
- **Absent metadata means "not stated", never the negative.** Do not sweep
  records out on a missing field.
- **A dry run that predicts volume must model the write path.** If the real run
  updates an index that the dry run skips, the dry run will over-count, and
  that number is what a human uses to authorise hours of work.
- **One list, one definition.** When two stages both need to know something
  (which sources are already resolved, which formats are supported), import the
  constant rather than restating it. Restating it is how the two silently
  drift, and the drift shows up as work that looks like healthy progress.
