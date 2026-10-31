# Ralph loop for Bob-Shell: feed the same prompt to a fresh `bob` session until done.
#
# Usage: ./ralph.ps1 [-PromptFile PROMPT.md] [-MaxIterations 20] [-ChatMode code] [-SleepSeconds 2]
#
# Each iteration is a brand-new non-interactive session. State lives only in the
# workspace (files, git history, progress file), never in the conversation.
# The loop stops when Bob's output contains the line <promise>COMPLETE</promise>
# or when MaxIterations is reached.

param(
    [string]$PromptFile = "PROMPT.md",
    [int]$MaxIterations = 20,
    [string]$ChatMode = "",
    [int]$SleepSeconds = 2
)

$DoneMarker = "<promise>COMPLETE</promise>"
$LogDir = ".ralph/logs"

if (-not (Get-Command bob -ErrorAction SilentlyContinue)) {
    Write-Error "bob not found in PATH"
    exit 127
}
if (-not (Test-Path $PromptFile)) {
    Write-Error "prompt file not found: $PromptFile"
    exit 2
}

New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

$bobArgs = @("--yolo", "--hide-intermediary-output")
if ($ChatMode) { $bobArgs += "--chat-mode=$ChatMode" }

for ($i = 1; $i -le $MaxIterations; $i++) {
    $log = Join-Path $LogDir ("iteration-{0:D3}.log" -f $i)
    Write-Host "=== Ralph iteration $i/$MaxIterations ($(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')) ==="

    # Re-read the prompt every iteration so it can be edited while the loop runs.
    $prompt = Get-Content -Raw -Path $PromptFile
    & bob -p $prompt @bobArgs 2>&1 | Tee-Object -FilePath $log

    if (Select-String -Path $log -Pattern $DoneMarker -SimpleMatch -Quiet) {
        Write-Host "=== Completed at iteration $i ==="
        exit 0
    }
    Start-Sleep -Seconds $SleepSeconds
}

Write-Error "Reached max iterations ($MaxIterations) without completion"
exit 1
