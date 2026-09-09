# Stop hook: refuse to end a turn whose reply contains an em dash or an en dash.
#
# CLAUDE.md bans both in prose, and states the reason the ban needs enforcing:
# "a prompt rule alone will not hold a model's habit, so pair every such rule
# with a mechanical check." This is that check. It was ported on 2026-09-07 from
# the atc-game project on this machine, where it has run since 2026-08-18.
#
# It has to be a Stop hook. Nothing else in the hook set can see assistant prose:
# PreToolUse and PostToolUse only ever see tool calls, and a reply that contains
# no tool call is invisible to them. Stop fires when the turn ends, receives the
# transcript path, and can refuse to let the turn finish by exiting 2. The stderr
# text comes back to the model as the reason to carry on and fix it.
#
# Exits 0 (silently allow) on anything unexpected. A hook that blocks the turn
# because it could not parse its own input would be worse than no hook at all.

$ErrorActionPreference = 'Stop'

# Read stdin as UTF-8 explicitly rather than via [Console]::In.ReadToEnd(), which
# decodes using the console input encoding. See the same comment in
# no_dashes_file.ps1 for the measurement: under the OEM codepage an em dash
# arrives as three bytes, decodes to three unrelated characters, and the check
# silently passes the text it exists to catch.
$reader = New-Object System.IO.StreamReader(
    [Console]::OpenStandardInput(), (New-Object System.Text.UTF8Encoding $false))
$raw = $reader.ReadToEnd()
if ([string]::IsNullOrWhiteSpace($raw)) { exit 0 }

try { $payload = $raw | ConvertFrom-Json } catch { exit 0 }

# Already blocked once this turn. Without this the model can be held in a loop it
# has no way to satisfy, which is why the harness supplies the flag.
if ($payload.stop_hook_active) { exit 0 }

$transcript = $payload.transcript_path
if ([string]::IsNullOrWhiteSpace($transcript)) { exit 0 }
if (-not (Test-Path -LiteralPath $transcript)) { exit 0 }

# Only the tail: the reply being judged is the last assistant entry, and reading a
# long session's whole transcript on every single turn is a cost paid for nothing.
# 400 lines is the value carried over from atc-game, where it has never missed.
try { $lines = Get-Content -LiteralPath $transcript -Tail 400 -Encoding UTF8 } catch { exit 0 }

$text = $null
for ($i = $lines.Count - 1; $i -ge 0; $i--) {
    if ([string]::IsNullOrWhiteSpace($lines[$i])) { continue }
    try { $entry = $lines[$i] | ConvertFrom-Json } catch { continue }
    if ($entry.type -ne 'assistant') { continue }

    $parts = @()
    foreach ($block in $entry.message.content) {
        if ($block.type -eq 'text' -and $block.text) { $parts += $block.text }
    }
    # An assistant entry holding only tool calls has no prose to judge; keep
    # walking back to the one that does.
    if ($parts.Count -gt 0) { $text = ($parts -join "`n"); break }
}

if ([string]::IsNullOrWhiteSpace($text)) { exit 0 }

# Code is exempt, and this is not a loophole: quoting a file, a diff or a log line
# that already contains a dash is reporting what is there, not writing prose.
$prose = [regex]::Replace($text, '(?s)```.*?```', ' ')
$prose = [regex]::Replace($prose, '`[^`]*`', ' ')

# Referenced by code point rather than written literally, so this script does not
# trip the very check it implements when something greps the repository for dashes.
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
    "CLAUDE.md forbids em and en dashes in prose, and your reply contains an " +
    ($found -join ' and ') + ". Rewrite the offending sentences using a full stop, " +
    "comma, colon or semicolon, recasting where none of those fit, then finish the " +
    "turn. Hyphens in compound words are fine, and text inside backticks is exempt. " +
    "First offending line: " + $sample.Trim()
)
exit 2
