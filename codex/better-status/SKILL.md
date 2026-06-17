---
name: better-status
description: Inspect and summarize useful metrics for the current Codex chat session. Use when the user asks for better status, session stats, chat metrics, token usage, message counts, turn count, elapsed work time, total working/wait time, or event counts for the active Codex conversation.
---

# Better Status

## Goal

Report practical metrics for the current Codex chat from the local session JSONL log. Prefer concise, user-facing summaries over raw logs.

Include:
- Total tokens used: input, cached input, output, reasoning output, total.
- Messages sent: user and assistant, distinguishing final assistant outputs from commentary when useful.
- Turn count.
- Total elapsed time from session creation to the latest parsed event.
- Total working time: sum of completed `task_complete.duration_ms` values, which approximates the time the user waited while Codex was thinking, using tools, and producing each answer.
- Event counts by top-level event type, plus `event_msg.payload.type` counts when available.

## Workflow

1. Locate the active session log.
   - Use `$env:CODEX_HOME` when set; otherwise use `$HOME\.codex`.
   - Search `sessions` recursively for recent `rollout-*.jsonl` files.
   - Prefer a file whose `session_meta.payload.cwd` equals the current working directory.
   - If no cwd match exists, use the most recently modified rollout file and say it is a fallback.

2. Parse the JSONL as structured events.
   - Do not estimate token usage from text length.
   - Use the latest `event_msg` where `payload.type == "token_count"` for token totals.
   - Use `turn_context` records for turn count.
   - Use `response_item` records with `payload.type == "message"` for message counts.

3. Count messages carefully.
   - User messages: `role == "user"` excluding synthetic environment/context messages such as text starting with `<environment_context>`.
   - Assistant messages: `role == "assistant"`.
   - Assistant final outputs: assistant messages where `payload.phase` is `final_answer` or `final`.
   - Assistant commentary/progress: assistant messages where `payload.phase` is `commentary`.
   - If the user asks what they can see in chat, report final outputs separately from commentary records.

4. Compute elapsed and working time.
   - Start with `session_meta.payload.timestamp` when present.
   - End at the latest event timestamp in the file.
   - Present local time using the session/user timezone when possible, and show elapsed as `hh:mm:ss`.
   - For total working time, sum `event_msg.payload.duration_ms` for events where `payload.type == "task_complete"`.
   - Also report completed task count. If there is a `task_started` without a matching `task_complete`, mention that the current in-progress turn is not included.
   - Clarify that elapsed time is wall-clock session time, while total working time is summed completed response duration.

5. Present the result nicely.
   - Lead with the numbers the user asked for.
   - Include a short note about the source file and any fallback.
   - Avoid dumping raw JSON unless requested.

## PowerShell Command

Run this from the current workspace. It prints a Markdown-ready status summary.

```powershell
$codexHome = if ($env:CODEX_HOME) { $env:CODEX_HOME } else { Join-Path $HOME ".codex" }
$sessionsDir = Join-Path $codexHome "sessions"
$cwd = (Get-Location).Path

$candidates = Get-ChildItem -Path $sessionsDir -Recurse -Filter "rollout-*.jsonl" -File |
  Sort-Object LastWriteTime -Descending |
  Select-Object -First 25

$selected = $null
$usedFallback = $false

foreach ($file in $candidates) {
  try {
    $first = Get-Content -Path $file.FullName -TotalCount 1 | ConvertFrom-Json
    if ($first.type -eq "session_meta" -and $first.payload.cwd -eq $cwd) {
      $selected = $file
      break
    }
  } catch {
    continue
  }
}

if (-not $selected) {
  $selected = $candidates | Select-Object -First 1
  $usedFallback = $true
}

if (-not $selected) {
  throw "No Codex session rollout JSONL files found under $sessionsDir"
}

$events = Get-Content -Path $selected.FullName | ForEach-Object {
  try { $_ | ConvertFrom-Json } catch { $null }
} | Where-Object { $_ -ne $null }

$meta = $events | Where-Object { $_.type -eq "session_meta" } | Select-Object -First 1
$turns = $events | Where-Object { $_.type -eq "turn_context" }
$messages = $events | Where-Object { $_.type -eq "response_item" -and $_.payload.type -eq "message" }
$tokenEvent = $events | Where-Object { $_.type -eq "event_msg" -and $_.payload.type -eq "token_count" } | Select-Object -Last 1
$taskStarts = $events | Where-Object { $_.type -eq "event_msg" -and $_.payload.type -eq "task_started" }
$taskCompletes = $events | Where-Object { $_.type -eq "event_msg" -and $_.payload.type -eq "task_complete" }

$userMessages = $messages | Where-Object {
  $_.payload.role -eq "user" -and
  ((($_.payload.content | ForEach-Object { $_.text }) -join " ") -notmatch "^<environment_context>")
}
$assistantMessages = $messages | Where-Object { $_.payload.role -eq "assistant" }
$assistantFinals = $assistantMessages | Where-Object { $_.payload.phase -in @("final_answer", "final") }
$assistantCommentary = $assistantMessages | Where-Object { $_.payload.phase -eq "commentary" }

$firstEvent = $events | Select-Object -First 1
$lastEvent = $events | Select-Object -Last 1
$start = if ($meta -and $meta.payload.timestamp) { [datetime]$meta.payload.timestamp } else { [datetime]$firstEvent.timestamp }
$end = [datetime]$lastEvent.timestamp
$elapsed = New-TimeSpan -Start $start -End $end
$completedDurationMs = ($taskCompletes | ForEach-Object { [double]$_.payload.duration_ms } | Measure-Object -Sum).Sum
if ($null -eq $completedDurationMs) { $completedDurationMs = 0 }
$working = [TimeSpan]::FromMilliseconds($completedDurationMs)
$openTaskCount = [Math]::Max(0, $taskStarts.Count - $taskCompletes.Count)

$eventCounts = $events | Group-Object type | Sort-Object Count -Descending
$eventMsgCounts = $events |
  Where-Object { $_.type -eq "event_msg" } |
  ForEach-Object { $_.payload.type } |
  Group-Object |
  Sort-Object Count -Descending

$tokens = if ($tokenEvent) { $tokenEvent.payload.info.total_token_usage } else { $null }

Write-Output "**Better Status**"
Write-Output ""
Write-Output "- Session: ``$($meta.payload.id)``"
Write-Output "- Source: ``$($selected.FullName)``$(if ($usedFallback) { ' (latest-file fallback)' } else { '' })"
Write-Output "- Workspace: ``$($meta.payload.cwd)``"
Write-Output "- Started: ``$($start.ToLocalTime().ToString('yyyy-MM-dd HH:mm:ss K'))``"
Write-Output "- Latest event: ``$($end.ToLocalTime().ToString('yyyy-MM-dd HH:mm:ss K'))``"
Write-Output "- Elapsed: ``$($elapsed.ToString('hh\:mm\:ss'))``"
Write-Output "- Total working time: ``$($working.ToString('hh\:mm\:ss'))`` across ``$($taskCompletes.Count)`` completed responses"
if ($openTaskCount -gt 0) {
  Write-Output "- In-progress responses not included in working time: ``$openTaskCount``"
}
Write-Output ""
Write-Output "**Tokens**"
if ($tokens) {
  Write-Output "- Total: ``$($tokens.total_tokens)``"
  Write-Output "- Input: ``$($tokens.input_tokens)``"
  Write-Output "- Cached input: ``$($tokens.cached_input_tokens)``"
  Write-Output "- Output: ``$($tokens.output_tokens)``"
  Write-Output "- Reasoning output: ``$($tokens.reasoning_output_tokens)``"
} else {
  Write-Output "- No token_count event found."
}
Write-Output ""
Write-Output "**Messages And Turns**"
Write-Output "- User messages: ``$($userMessages.Count)``"
Write-Output "- Assistant messages: ``$($assistantMessages.Count)``"
Write-Output "- Assistant final outputs: ``$($assistantFinals.Count)``"
Write-Output "- Assistant commentary/progress: ``$($assistantCommentary.Count)``"
Write-Output "- Turn count: ``$($turns.Count)``"
Write-Output ""
Write-Output "**Event Counts**"
foreach ($item in $eventCounts) {
  Write-Output "- ``$($item.Name)``: ``$($item.Count)``"
}
Write-Output ""
Write-Output "**Event Message Counts**"
foreach ($item in $eventMsgCounts) {
  Write-Output "- ``$($item.Name)``: ``$($item.Count)``"
}
Write-Output ""
Write-Output '_Elapsed time is wall-clock time from session creation to the latest logged event. Total working time sums completed response durations from `task_complete.duration_ms`; any current in-progress response may be excluded until it completes._'
```

## Output Guidance

If the user asks for a compact answer, summarize the command output instead of pasting every event count. If the user asks to audit or verify the numbers, include the source path and explain the counting rules.
