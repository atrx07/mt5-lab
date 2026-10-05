param(
    [string]$SessionId = ""
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

$VenvPython = Join-Path $RepoRoot ".venv\Scripts\python.exe"
$Python = if (Test-Path $VenvPython) { $VenvPython } else { "python" }

$ArgsList = @(
    "scripts/capture_candidate_j_4h_block.py",
    "--warmup-minutes", "90",
    "--duration-hours", "4"
)

if ($SessionId -ne "") {
    $ArgsList += @("--session-id", $SessionId)
}

Write-Host "Starting prospective Candidate J 4-hour block..."
Write-Host "The script backfills 90 minutes of MT5 history as context, then scores 4 hours from launch."
Write-Host "No broker orders will be sent."
& $Python @ArgsList
$CaptureExit = $LASTEXITCODE

if ($CaptureExit -ne 0) {
    Write-Host ""
    Write-Host "Capture did not start. Running read-only MT5 warmup diagnostic..."
    & $Python "scripts/diagnose_candidate_j_warmup.py" --symbol XAUUSD --required-minutes 90 --lookback-hours 24 --gap-sec 5
    Write-Host ""
    Write-Host "No scored block was started by the failed attempt."
}

exit $CaptureExit
