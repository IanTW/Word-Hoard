#!/usr/bin/env bash
#
# Mechanical half of the housekeeping checklist. See docs/HOUSEKEEPING.md for the
# judgement half, which a script cannot do.
#
# Installed by the /new-project skill. Generalised from word-hoard's copy
# (2026-09-07), itself ported from atc-game: a checklist for what a person has to
# decide, a script for what a machine can just answer.
#
# THIS SCRIPT REPORTS AND NEVER FAILS. It always exits 0, deliberately. It runs
# during Wrap Up, and a Wrap Up that cannot finish because a doc is stale would
# be worse than the stale doc.
#
# Run from anywhere:
#   bash tools/housekeeping.sh

# Resolve the repository root from this script's own location, so it works
# regardless of the caller's working directory.
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT" || exit 0

findings=0

# Print a finding and count it. The summary line at the end is the part a reader
# actually looks at, so every finding must reach the count.
note() {
    printf '  [!] %s\n' "$1"
    findings=$((findings + 1))
}

ok() {
    printf '  [ok] %s\n' "$1"
}

echo "housekeeping: $ROOT"
echo

# Not a git repository yet: most checks below need one. Say so once, plainly,
# rather than letting each check print its own confusing failure.
if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    note "not a git repository, so the dash sweep, DEVLOG freshness and working tree checks are skipped"
    IS_GIT=0
else
    IS_GIT=1
fi
echo

# ---------------------------------------------------------------------------
# 1. Em and en dashes in tracked and newly added files.
#
# The global rules ban both in prose. The hooks stop new ones written through
# Claude's Write and Edit tools, but anything arriving by hand, by script or via
# a spreadsheet round trip bypasses them. This sweep is the backstop.
#
# Only NEW dashes are listed: those on lines added since the newest DEVLOG
# entry's date, which is the last session, because Wrap Up runs this script
# before it writes today's entry. Files holding only older dashes are counted
# in one line instead. Why: four projects carried 59 to 75 files with dashes
# from before the rule (measured 2026-10-04), so a listing of every file buried
# the one new dash it exists to catch. A dash on an untouched line of an edited
# file is old, not new, so lines are judged, never whole files. With no dated
# DEVLOG entry there is no "since", and every file is listed as before.
# ---------------------------------------------------------------------------
echo "dashes in tracked and new files"
# Built from code points so this script never reports itself.
EM_DASH="$(printf '\xe2\x80\x94')"
EN_DASH="$(printf '\xe2\x80\x93')"

# Print the files given a unified diff on stdin that ADD a line holding a dash.
# A "+++ b/<path>" line names the file only inside a diff header (between
# "diff --git" and the first "@@"), so an added line that happens to start with
# "++" is never mistaken for a file name. Binary files have no "+" lines in a
# diff, so they can never be listed here.
added_dash_files() {
    awk -v em="$EM_DASH" -v en="$EN_DASH" '
        /^diff --git / { header = 1; file = ""; next }
        header && /^\+\+\+ b\// { file = substr($0, 7); next }
        /^@@/ { header = 0; next }
        !header && file != "" && /^\+/ && (index($0, em) || index($0, en)) { print file }
    '
}

if [ "$IS_GIT" -eq 1 ]; then
    # Every text file holding a dash now. --cached AND --others
    # --exclude-standard: plain ls-files misses brand new untracked files,
    # which is exactly when a dash is most likely.
    # grep -I skips binary files (any holding a NUL byte). Without it, 11 .ogg
    # sound files in atc-game were reported as prose with dashes on
    # 2026-10-04, because their bytes happened to contain the sequence.
    dash_hits="$(git ls-files -z --cached --others --exclude-standard 2>/dev/null \
        | xargs -0 grep -lI "[${EM_DASH}${EN_DASH}]" 2>/dev/null)"

    # The newest dated DEVLOG heading. Entries are newest first, so the first
    # match is the last session; the template's "## YYYY-MM-DD" example has
    # no digits and never matches.
    since="$(grep -m1 -oE '^## [0-9]{4}-[0-9]{2}-[0-9]{2}' docs/DEVLOG.md 2>/dev/null | cut -c4-)"

    if [ -z "$dash_hits" ]; then
        ok "none"
    elif [ -z "$since" ]; then
        # No date to measure from: list every file, as before 2026-10-04.
        while IFS= read -r f; do
            [ -n "$f" ] && note "em or en dash in $f"
        done <<< "$dash_hits"
    else
        # Files that gained a dash since that day, from three places:
        # commits since its start (-U0: added lines only, no context lines,
        # --no-renames so the new path is always on the "+++ b/" line), the
        # staged and unstaged work against HEAD, and untracked files read
        # whole, since every line of a new file is new.
        new_hits="$( {
            git log --since="$since 00:00" --format= -p -U0 --no-color --no-renames 2>/dev/null \
                | added_dash_files
            git diff HEAD -U0 --no-color --no-renames 2>/dev/null | added_dash_files
            git ls-files -z --others --exclude-standard 2>/dev/null \
                | xargs -0 grep -lI "[${EM_DASH}${EN_DASH}]" 2>/dev/null
        } | sort -u)"
        # Keep only files that still hold a dash: one added and later removed
        # in the same window is gone, and listing it would be a false alarm.
        if [ -n "$new_hits" ]; then
            new_hits="$(printf '%s\n' "$new_hits" | grep -Fxf <(printf '%s\n' "$dash_hits"))"
        fi
        new_count=0
        if [ -n "$new_hits" ]; then
            while IFS= read -r f; do
                [ -n "$f" ] && note "em or en dash in $f" && new_count=$((new_count + 1))
            done <<< "$new_hits"
        else
            ok "none added since $since"
        fi
        # The rest are older dashes: counted, deliberately not a finding,
        # so they never reach the summary count.
        all_count="$(printf '%s\n' "$dash_hits" | grep -c .)"
        old_count=$((all_count - new_count))
        if [ "$old_count" -gt 0 ]; then
            printf '  %s other file(s) hold older dashes, from before %s, not listed\n' "$old_count" "$since"
        fi
    fi
fi
echo

# ---------------------------------------------------------------------------
# 2. DEVLOG freshness.
#
# Exists because of a real failure in word-hoard: four sessions landed with no
# DEVLOG entry, recorded nowhere but TODO bullets and commit messages. Comparing
# the newest entry date with the newest commit date says so in one line.
# ---------------------------------------------------------------------------
echo "DEVLOG freshness"
devlog_date="$(grep -m1 -oE '^## [0-9]{4}-[0-9]{2}-[0-9]{2}' docs/DEVLOG.md 2>/dev/null | cut -d' ' -f2)"
if [ "$IS_GIT" -eq 1 ]; then
    commit_date="$(git log -1 --format=%ad --date=short 2>/dev/null)"
    if [ -z "$devlog_date" ]; then
        note "could not read a dated entry heading in docs/DEVLOG.md"
    elif [ -z "$commit_date" ]; then
        ok "newest entry $devlog_date, no commits yet"
    elif [ "$devlog_date" \< "$commit_date" ]; then
        note "newest DEVLOG entry is $devlog_date, newest commit is $commit_date"
    else
        ok "newest entry $devlog_date, newest commit $commit_date"
    fi
fi
echo

# ---------------------------------------------------------------------------
# 3. TODO archive and trim.
#
# docs/TODO.md holds open work, not history, and the session hook summarises it
# at the start of every session, so bloat is paid for again each time. The
# global rules say to PROPOSE archiving and trimming at every Wrap Up; this
# check supplies the list. It still only reports: moving or shortening an item
# happens on the user's yes.
#
# Why these thresholds, measured on telegram-channel's TODO on 2026-09-14
# (76,582 bytes): 34 closed items made up 36,551 characters, nearly half the
# file, because archiving had waited for the user to ask. So ANY closed item is
# a finding. Open items had a median of 610 characters and a maximum of 5,395;
# 1,500 flagged 6 of 39, a handful per Wrap Up rather than a wall.
# ---------------------------------------------------------------------------
TRIM_CHARS=1500
echo "TODO archive and trim"
# grep -c prints 0 AND exits 1 on no match, so an "|| echo 0" fallback would
# print the number twice. Default an empty string instead.
closed="$(grep -c '^- \[[xX]\]' docs/TODO.md 2>/dev/null)"
open_items="$(grep -c '^- \[ \]' docs/TODO.md 2>/dev/null)"
closed="${closed:-0}"
open_items="${open_items:-0}"
echo "  $closed closed and $open_items open items, $(wc -c < docs/TODO.md 2>/dev/null || echo 0) bytes"
if [ "$closed" -gt 0 ]; then
    note "$closed closed item(s) to propose moving to docs/TODO_archive.md"
else
    ok "no closed items waiting"
fi

# An open item's length is its checkbox line plus the indented and blank lines
# under it, up to the next unindented line. Printed as the bold headline where
# the item opens with one, since that is how the session hook names it too.
# Lengths come from awk and are approximate for non-ASCII text, which is fine
# for a threshold this coarse.
long_items="$(awk -v limit="$TRIM_CHARS" '
    function flush() {
        if (title != "" && len > limit) printf "%d chars: %s\n", len, title
        title = ""; len = 0
    }
    /^- \[ \] / {
        flush()
        title = $0; sub(/^- \[ \] /, "", title)
        if (match(title, /^\*\*[^*]+\*\*/)) title = substr(title, 3, RLENGTH - 4)
        title = substr(title, 1, 70); len = length($0)
        next
    }
    /^[ \t]/ || /^$/ { if (title != "") len += length($0) + 1; next }
    { flush() }
    END { flush() }
' docs/TODO.md 2>/dev/null)"
if [ -n "$long_items" ]; then
    while IFS= read -r line; do
        [ -n "$line" ] && note "open item over $TRIM_CHARS chars, propose a trim: $line"
    done <<< "$long_items"
else
    ok "no open item over $TRIM_CHARS chars"
fi
echo

# ---------------------------------------------------------------------------
# 4. Is the housekeeping pass due?
#
# The global Wrap Up offers the full checklist in docs/HOUSEKEEPING.md (the
# pass) when a milestone closes, or after PASS_FLOOR sessions without one. A
# milestone close is the session's to notice; this counts the floor, because a
# floor written down with nothing counting it is a rule that will not hold.
#
# A pass is recorded by a DEVLOG line that STARTS with **Housekeeping pass:**.
# A mention mid sentence, or inside a fenced code block (an entry quoting the
# rule), does not count, so quoting the rule never resets the count. The
# DEVLOG is newest first, so the entries counted are the dated headings above
# the newest entry holding the line.
#
# It names the evidence (how many entries, since which pass) rather than
# saying an interval elapsed, so the offer can be weighed and declined.
# ---------------------------------------------------------------------------
# 10 sessions: atc-game's floor for its full pass, set 2026-09-06 and promoted
# to the global Wrap Up 2026-09-16 (claude-admin audit review, finding 10).
PASS_FLOOR=10
echo "housekeeping pass"
if [ -f docs/DEVLOG.md ]; then
    # Prints "<entries newer than the last pass> <date of that pass or none>".
    # Headings use [0-9] runs rather than {4}, which not every awk accepts.
    pass_state="$(awk '
        /^```/ { fence = !fence; next }
        fence { next }
        /^## [0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]/ {
            entries++; date = substr($0, 4, 10); next
        }
        /^\*\*Housekeeping pass:\*\*/ {
            if (entries > 0) { print entries - 1, date; found = 1; exit }
        }
        END { if (!found) print entries + 0, "none" }
    ' docs/DEVLOG.md 2>/dev/null)"
    since="${pass_state%% *}"
    last_pass="${pass_state#* }"
    since="${since:-0}"
    if [ "$last_pass" = "none" ] || [ -z "$last_pass" ]; then
        if [ "$since" -ge "$PASS_FLOOR" ]; then
            note "no housekeeping pass recorded, $since DEVLOG entries; offer the pass"
        else
            ok "no housekeeping pass recorded yet, $since DEVLOG entries, due at $PASS_FLOOR"
        fi
    elif [ "$since" -ge "$PASS_FLOOR" ]; then
        note "$since DEVLOG entries since the last housekeeping pass ($last_pass); offer the pass"
    else
        ok "$since DEVLOG entries since the last housekeeping pass ($last_pass), due at $PASS_FLOOR"
    fi
else
    ok "no docs/DEVLOG.md, nothing to count"
fi
echo

# ---------------------------------------------------------------------------
# 5. requirements.txt against the venv, only when both exist.
#
# A pin that has silently drifted from what is installed is worse than no pin.
# Projects without a Python venv skip this without a finding.
#
# Each line of requirements.txt is asked two questions, by the venv's own
# Python: is that package installed, and does its version satisfy the line?
# (claude-admin docs/TESTPLAN.md, "Requirements check: test what is listed,
# not the whole freeze", agreed 2026-10-04.) This replaced a line-by-line diff
# against the full `pip freeze`, which gave one false note per indirect
# dependency and read every ranged entry (streamlit>=1.49, pytest==8.*) as
# missing: 17 false notes in code-optimiser on 2026-09-29, 54 in habit-tracker
# on 2026-10-04.
#
# Deliberately gone: "installed but not listed". A file of top-level packages
# cannot be told from a stale full freeze without guessing, and that direction
# produced every false note measured.
#
# The Python lives here as a heredoc so the kit stays one file per project. It
# reads specifiers with `packaging`, falling back to the copy pip carries, so
# no project needs a new dependency. It prints one "NOTE <text>" line per
# finding and never fails the script.
# ---------------------------------------------------------------------------
VENV_PY=".venv/Scripts/python.exe"
if [ -f requirements.txt ] && [ -x "$VENV_PY" ]; then
    echo "requirements.txt against the venv"
    req_out="$("$VENV_PY" - 2>&1 <<'PY'
import re
from importlib.metadata import distributions

# Specifier parsing: the real package if the venv has it, else pip's copy.
try:
    from packaging.requirements import InvalidRequirement, Requirement
except ImportError:
    try:
        from pip._vendor.packaging.requirements import InvalidRequirement, Requirement
    except ImportError:
        print("NOTE the venv has neither packaging nor pip, so requirements.txt was not checked")
        raise SystemExit(0)


def canonical(name):
    """PEP 503 name: pip_system_certs, Pip-System-Certs and pip.system.certs match."""
    return re.sub(r"[-_.]+", "-", name).lower()


# Installed versions keyed by canonical name. A distribution with broken
# metadata has no name; skip it rather than crash.
installed = {}
for dist in distributions():
    name = dist.metadata["Name"]
    if name:
        installed[canonical(name)] = dist.version

found = 0
with open("requirements.txt", encoding="utf-8-sig") as handle:
    for number, raw in enumerate(handle, 1):
        # pip treats " #" as the start of a comment, even after a requirement.
        line = raw.split(" #")[0].strip()
        # Blank lines, comments, and option lines (-r, -e, --index-url) are
        # not requirements of this venv.
        if not line or line.startswith("#") or line.startswith("-"):
            continue
        try:
            req = Requirement(line)
        except InvalidRequirement:
            print(f"NOTE requirements.txt line {number} could not be read: {line}")
            found += 1
            continue
        # A marker that is false here (sys_platform == "linux" on Windows)
        # means the line does not apply to this venv.
        if req.marker is not None and not req.marker.evaluate():
            continue
        have = installed.get(canonical(req.name))
        if have is None:
            print(f"NOTE listed but not installed: {line}")
            found += 1
        elif req.specifier and not req.specifier.contains(have, prereleases=True):
            print(f"NOTE installed {req.name} {have} does not satisfy {line}")
            found += 1

if not found:
    print("OK every listed package is installed and satisfies its line")
PY
)"
    req_status=$?
    # Each NOTE line becomes a counted finding. Anything else the Python
    # printed (a traceback) is surfaced as one note rather than lost.
    if [ "$req_status" -ne 0 ]; then
        note "the requirements check crashed (exit $req_status): $(echo "$req_out" | tail -1)"
    else
        while IFS= read -r line; do
            # Windows Python ends printed lines with CRLF; drop the CR so it
            # never reaches the note text.
            line="${line%$'\r'}"
            case "$line" in
                "NOTE "*) note "${line#NOTE }" ;;
                "OK "*) ok "${line#OK }" ;;
            esac
        done <<< "$req_out"
    fi
    echo
fi

# ---------------------------------------------------------------------------
# 6. The shared hooks can reach this project.
#
# The session recap and both dash guards are shared hooks in ~/.claude/hooks/,
# deployed from claude-admin (its docs/TESTPLAN.md, "Shared hooks", 2026-09-15).
# They find this project by its docs/DEVLOG.md or .claude/kit.json, and read its
# exceptions from .claude/kit.json. A missing kit.json means no exceptions, not
# a broken hook, but the kit creates one so the place for an exception is plain.
# Whether this project still registers its own copy of a shared hook is judged
# by the audit and by verify.py, which ask the hooks' own helper
# (kit_common.ps1) rather than guessing from file names here.
#
# Which hooks are shared is read from ~/.claude/hooks/shared_hooks.txt, the one
# list every check uses (claude-admin docs/TESTPLAN.md, "Shared hook list",
# 2026-10-04). This loop used to name three hooks itself, and missed the fourth
# when no_inline_backslashes.ps1 was added on 2026-10-03.
# ---------------------------------------------------------------------------
echo "shared hooks"
if [ -f .claude/kit.json ]; then
    ok ".claude/kit.json present"
else
    note ".claude/kit.json is missing, so there is nowhere to record an exception to the shared hooks"
fi
hook_list="$HOME/.claude/hooks/shared_hooks.txt"
if [ -f "$hook_list" ]; then
    # Columns: kit name, script, event. The CR strip guards a list saved with
    # CRLF endings: a blank line would then read as a hook named CR, with an
    # empty script, reported missing (claude-admin test_shared_hooks.py check
    # 24 failed exactly so with the strip removed, 2026-10-04).
    while read -r _name script _event; do
        case "$_name" in ''|'#'*) continue ;; esac
        if [ -f "$HOME/.claude/hooks/$script" ]; then
            ok "shared hook $script deployed"
        else
            note "shared hook ~/.claude/hooks/$script is missing, so its check is not running here; deploy it from claude-admin"
        fi
    done < <(tr -d '\r' < "$hook_list")
else
    note "~/.claude/hooks/shared_hooks.txt is missing, so the shared hooks cannot be checked; deploy it from claude-admin"
fi
echo

# ---------------------------------------------------------------------------
# PROJECT-SPECIFIC CHECKS
#
# Add checks that only make sense for this project here, in the same shape: a
# heading echo, then note() for a finding or ok() for a pass. word-hoard's
# example is a grep proving the domain package never imports a web framework.
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Framework isolation.
#
# The one architectural rule: nothing under wordhoard/ imports a web framework.
# This is the grep that step 6 ran by hand, made repeatable, because a rule
# checked once is a rule that holds until the next time somebody is in a hurry.
# Moved here unchanged from this project's own script on 2026-10-04, when the
# rest of the script was replaced by the claude-admin kit's.
# ---------------------------------------------------------------------------
echo "framework isolation under wordhoard/"
leaks="$(grep -rn 'fastapi\|uvicorn\|starlette\|jinja2' --include='*.py' wordhoard/ 2>/dev/null)"
if [ -n "$leaks" ]; then
    while IFS= read -r line; do
        [ -n "$line" ] && note "web framework referenced: $line"
    done <<< "$leaks"
else
    ok "clean, 0 hits"
fi
echo

# ---------------------------------------------------------------------------
# 7. Uncommitted work. Informational: Wrap Up proposes a commit next.
# ---------------------------------------------------------------------------
if [ "$IS_GIT" -eq 1 ]; then
    echo "working tree"
    dirty="$(git status --porcelain 2>/dev/null)"
    if [ -n "$dirty" ]; then
        echo "$dirty" | sed 's/^/  /'
    else
        ok "clean"
    fi
    echo
fi

echo "----------------------------------------"
if [ "$findings" -eq 0 ]; then
    echo "housekeeping: nothing to report"
else
    echo "housekeeping: $findings thing(s) to look at"
fi
echo "This check reports only. It never fails a Wrap Up."
exit 0
