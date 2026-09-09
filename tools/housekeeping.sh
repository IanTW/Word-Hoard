#!/usr/bin/env bash
#
# Mechanical half of the housekeeping checklist. See docs/HOUSEKEEPING.md for the
# judgement half, which a script cannot do.
#
# Ported 2026-09-07 from the atc-game project on this machine, where the same
# split has run since 2026-08-18: a checklist for what a person has to decide,
# a script for what a machine can just answer.
#
# THIS SCRIPT REPORTS AND NEVER FAILS. It always exits 0, deliberately. It runs
# during Wrap Up, and a Wrap Up that cannot finish because a doc is stale would
# be worse than the stale doc. Every finding is printed for a human to act on or
# to ignore with reasons.
#
# Run from anywhere:
#   bash tools/housekeeping.sh

# Resolve the repository root from this script's own location, so the script
# works regardless of the caller's working directory.
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT" || exit 0

findings=0

# Print a finding and count it. Counting matters because the summary line at the
# end is the part a reader actually looks at.
note() {
    printf '  [!] %s\n' "$1"
    findings=$((findings + 1))
}

ok() {
    printf '  [ok] %s\n' "$1"
}

echo "housekeeping: $ROOT"
echo

# ---------------------------------------------------------------------------
# 1. Em and en dashes in tracked and newly added files.
#
# CLAUDE.md bans both in prose. The .claude/ hooks stop new ones being written,
# but they only see writes made through Claude's Write and Edit tools: anything
# arriving by hand, by script, or through a spreadsheet round trip bypasses them
# entirely. This sweep is the backstop for that gap.
# ---------------------------------------------------------------------------
echo "dashes in tracked and new files"
# Built from code points rather than written literally, so this script does not
# report itself every time it runs. The PowerShell hooks use the same trick.
EM_DASH="$(printf '\xe2\x80\x94')"
EN_DASH="$(printf '\xe2\x80\x93')"
# --cached AND --others --exclude-standard, not plain ls-files. The first run of
# this script on 2026-09-07 reported "none" while three brand new files sat in
# the working tree unchecked, because plain ls-files sees only tracked paths and
# a new file is untracked until it is staged. A new file is exactly when a dash
# is most likely, so the sweep has to reach it. --exclude-standard keeps the
# venv and other gitignored paths out.
dash_hits="$(git ls-files -z --cached --others --exclude-standard 2>/dev/null \
    | xargs -0 grep -l "[${EM_DASH}${EN_DASH}]" 2>/dev/null)"
if [ -n "$dash_hits" ]; then
    while IFS= read -r f; do
        [ -n "$f" ] && note "em or en dash in $f"
    done <<< "$dash_hits"
else
    ok "none"
fi
echo

# ---------------------------------------------------------------------------
# 2. Framework isolation.
#
# The one architectural rule: nothing under wordhoard/ imports a web framework.
# This is the grep that step 6 ran by hand, made repeatable, because a rule
# checked once is a rule that holds until the next time somebody is in a hurry.
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
# 3. DEVLOG freshness.
#
# This check exists because of a real failure. On 2026-09-07 the DEVLOG held one
# entry, dated 2026-08-23, while four sessions had landed since; the scheduler,
# the interval ceiling, the typing exercise, the introduction pass and the whole
# web interface were recorded nowhere but in TODO bullets and commit messages.
# Comparing the newest entry date against the newest commit date would have said
# so in one line.
# ---------------------------------------------------------------------------
echo "DEVLOG freshness"
devlog_date="$(grep -m1 -oE '^## [0-9]{4}-[0-9]{2}-[0-9]{2}' docs/DEVLOG.md 2>/dev/null | cut -d' ' -f2)"
commit_date="$(git log -1 --format=%ad --date=short 2>/dev/null)"
if [ -z "$devlog_date" ] || [ -z "$commit_date" ]; then
    note "could not read a DEVLOG date or a commit date"
elif [ "$devlog_date" \< "$commit_date" ]; then
    note "newest DEVLOG entry is $devlog_date, newest commit is $commit_date"
else
    ok "newest entry $devlog_date, newest commit $commit_date"
fi
echo

# ---------------------------------------------------------------------------
# 4. Closed items still sitting in TODO.md.
#
# Reported, never acted on. CLAUDE.md is explicit that archiving happens when the
# user asks, not proactively, so this is a count to inform that decision rather
# than a defect. A large number simply means the file is getting noisy.
# ---------------------------------------------------------------------------
echo "TODO archive pressure"
# grep -c prints a count and still exits 1 when the count is zero, so a
# "|| echo 0" fallback here would print the number twice and break the
# arithmetic below. Take the output and default an empty string instead.
closed="$(grep -c '^- \[x\]' docs/TODO.md 2>/dev/null)"
open_items="$(grep -c '^- \[ \]' docs/TODO.md 2>/dev/null)"
closed="${closed:-0}"
open_items="${open_items:-0}"
echo "  $closed closed and $open_items open items in docs/TODO.md"
if [ "$closed" -gt 20 ]; then
    note "$closed closed items are candidates for docs/TODO_archive.md, ask before moving them"
else
    ok "archive pressure is low"
fi
echo

# ---------------------------------------------------------------------------
# 5. requirements.txt against what is actually installed.
#
# A guessed pin looks authoritative and is not, which is why this file was left
# unpinned until the first real install. The same reasoning says a pin that has
# silently drifted from the venv is worse than no pin, so compare them.
#
# Names are normalised: pip freeze prints pip-system-certs where the file says
# pip_system_certs, and a hyphen against an underscore is not a drift.
# ---------------------------------------------------------------------------
echo "requirements.txt against the venv"
VENV_PY=".venv/Scripts/python.exe"
if [ ! -x "$VENV_PY" ]; then
    note "no venv at $VENV_PY, skipping the comparison"
else
    normalise() {
        grep -v '^\s*#' | grep -v '^\s*$' | tr 'A-Z_' 'a-z-' | sort
    }
    pinned="$(normalise < requirements.txt)"
    installed="$("$VENV_PY" -m pip freeze 2>/dev/null | normalise)"
    if [ -z "$installed" ]; then
        note "pip freeze produced nothing, skipping the comparison"
    else
        drift="$(diff <(echo "$pinned") <(echo "$installed") | grep '^[<>]')"
        if [ -n "$drift" ]; then
            while IFS= read -r line; do
                case "$line" in
                    "<"*) note "pinned but not installed: ${line#< }" ;;
                    ">"*) note "installed but not pinned: ${line#> }" ;;
                esac
            done <<< "$drift"
        else
            ok "pins match the venv exactly"
        fi
    fi
fi
echo

# ---------------------------------------------------------------------------
# 6. The dash hooks are still wired up.
#
# The hook paths in .claude/settings.json are absolute, so moving or renaming the
# repository silently disables them. Nothing announces that; the checks just stop
# happening. Confirm the three files still exist.
# ---------------------------------------------------------------------------
echo "dash hook wiring"
for f in .claude/settings.json \
         .claude/hooks/no_dashes_response.ps1 \
         .claude/hooks/no_dashes_file.ps1; do
    if [ -f "$f" ]; then
        ok "$f present"
    else
        note "$f is missing, the mechanical check is not running"
    fi
done
if [ -f .claude/settings.json ] && ! grep -q "$(basename "$ROOT")" .claude/settings.json 2>/dev/null; then
    note ".claude/settings.json does not mention this directory name, check the absolute hook paths"
fi
echo

# ---------------------------------------------------------------------------
# 7. Uncommitted work.
#
# Informational. Wrap Up proposes a commit, so knowing what is outstanding before
# that step saves a round trip.
# ---------------------------------------------------------------------------
echo "working tree"
dirty="$(git status --porcelain 2>/dev/null)"
if [ -n "$dirty" ]; then
    echo "$dirty" | sed 's/^/  /'
else
    ok "clean"
fi
echo

# ---------------------------------------------------------------------------
echo "----------------------------------------"
if [ "$findings" -eq 0 ]; then
    echo "housekeeping: nothing to report"
else
    echo "housekeeping: $findings thing(s) to look at"
fi
echo "This check reports only. It never fails a Wrap Up."
exit 0
