# PostToolUse hook: catch em and en dashes written into prose files.
#
# The companion to no_dashes_response.ps1. That one guards what is said to the
# user; this guards what is written into files, which is where most prose in this
# project actually ends up: DEVLOG entries, TODO items, memory files, schema
# comments and the dense code comments the commenting standard asks for.
#
# Ported on 2026-09-07 from the atc-game project on this machine, with ONE
# deliberate difference. There, the scope was .md and .txt only, because every
# GDScript comment predated the rule and a new comment in a new style would have
# read as an inconsistency rather than as a standard. That argument does not
# apply here: on 2026-09-07 a sweep of every tracked file in this repository
# found zero em dashes and zero en dashes, so there is no legacy prose to sit
# beside. The scope is therefore widened to the source files as well, which is
# where CLAUDE.md's "any prose" reading points once nothing is grandfathered in.
#
# Verified before widening:
#   git ls-files -z | xargs -0 grep -l $'[em][en]'   ->   no matches
#
# Only ever inspects the text being WRITTEN, never the file's existing contents,
# so an edit that merely sits next to an offending line is never blamed for it.
#
# Exits 0 on anything unexpected, for the same reason the Stop hook does.

$ErrorActionPreference = 'Stop'

# Widened from atc-game's ('.md', '.txt') because this repository has no
# pre-existing dashes anywhere. Narrowing it again is a one-line change.
$PROSE_EXTENSIONS = @('.md', '.txt', '.py', '.sql', '.html')

# Read stdin as UTF-8 explicitly rather than via [Console]::In.ReadToEnd().
#
# This is a FIX ON THE PORT, not a stylistic change. [Console]::In decodes using
# the console input encoding, which on this machine is an OEM codepage, not
# UTF-8. The em dash arrives as the three bytes E2 80 94, gets decoded as three
# unrelated characters, and the Contains() test below never matches. Measured
# 2026-09-07: with [Console]::In, a payload whose new_string held a real em dash
# exited 0 and printed nothing, so the hook silently passed exactly the text it
# exists to catch. Four other payload shapes behaved correctly, which is what
# made the failure hard to see. The same bug is present in the atc-game copy.
$reader = New-Object System.IO.StreamReader(
    [Console]::OpenStandardInput(), (New-Object System.Text.UTF8Encoding $false))
$raw = $reader.ReadToEnd()
if ([string]::IsNullOrWhiteSpace($raw)) { exit 0 }

try { $payload = $raw | ConvertFrom-Json } catch { exit 0 }

$input_data = $payload.tool_input
if ($null -eq $input_data) { exit 0 }

$path = $input_data.file_path
if ([string]::IsNullOrWhiteSpace($path)) { exit 0 }

$extension = [System.IO.Path]::GetExtension($path).ToLower()
if ($PROSE_EXTENSIONS -notcontains $extension) { exit 0 }

# Write carries `content`; Edit carries `new_string`. Anything else is not a text
# write and has nothing here to judge.
$written = $null
if ($input_data.PSObject.Properties.Name -contains 'content') {
    $written = $input_data.content
} elseif ($input_data.PSObject.Properties.Name -contains 'new_string') {
    $written = $input_data.new_string
}
if ([string]::IsNullOrWhiteSpace($written)) { exit 0 }

# Fenced code and inline code are exempt, matching the Stop hook: a document
# quoting a log line or a TSV row is reporting, not writing prose.
$prose = [regex]::Replace($written, '(?s)```.*?```', ' ')
$prose = [regex]::Replace($prose, '`[^`]*`', ' ')

# Referenced by code point rather than written literally, so this script does not
# trip the very check it implements.
$em = [char]0x2014
$en = [char]0x2013

$found = @()
if ($prose.Contains($em)) { $found += 'em dash' }
if ($prose.Contains($en)) { $found += 'en dash' }
if ($found.Count -eq 0) { exit 0 }

$sample = $prose -split "`n" |
    Where-Object { $_.Contains($em) -or $_.Contains($en) } |
    Select-Object -First 1
if ($sample.Length -gt 220) { $sample = $sample.Substring(0, 220) + '...' }

[Console]::Error.WriteLine(
    "CLAUDE.md forbids em and en dashes in prose, and the text just written to " +
    (Split-Path -Leaf $path) + " contains an " + ($found -join ' and ') + ". The write " +
    "has already happened, so fix it with a follow-up edit: use a full stop, comma, " +
    "colon or semicolon, and recast the sentence where none of those fit. Only the " +
    "text you just wrote is being judged, not the file's older prose. " +
    "First offending line: " + $sample.Trim()
)
exit 2
