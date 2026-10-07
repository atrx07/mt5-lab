param(
    [string]$SessionId = ""
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

$VenvPython = Join-Path $RepoRoot ".venv\Scripts\python.exe"
$Python = if (Test-Path $VenvPython) { $VenvPython } else { "python" }

$ArgsList = @(
    "scripts/capture_m_acceptance_shadow_4h_block.py",
    "--warmup-minutes", "90",
    "--duration-hours", "4"
)
if ($SessionId -ne "") {
    $ArgsList += @("--session-id", $SessionId)
}

Write-Host "Starting Experiment 58 fresh M-acceptance shadow block..."
Write-Host "90 minutes causal warmup + 4 hours fresh raw MT5 ticks."
Write-Host "No broker orders and no strategy P&L during capture."
& $Python @ArgsList
$CaptureExit = $LASTEXITCODE

if ($CaptureExit -ne 0) {
    Write-Host ""
    Write-Host "Capture did not start. Running read-only MT5 warmup diagnostic..."
    & $Python "scripts/diagnose_candidate_j_warmup.py" --symbol XAUUSD --required-minutes 90 --lookback-hours 24 --gap-sec 5
    Write-Host ""
    Write-Host "No Experiment-58 block was started by the failed attempt."
}

exit $CaptureExit
