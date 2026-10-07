param(
    [string]$SessionId = ""
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

$VenvPython = Join-Path $RepoRoot ".venv\Scripts\python.exe"
$Python = if (Test-Path $VenvPython) { $VenvPython } else { "python" }

# Candidate M inherits Candidate L's CONTINUITY_SEC=1800s. Keep the raw >5s
# continuity reset unchanged; only remove the older Candidate-J 90m over-gate.
$ArgsList = @(
    "tools/capture_m_acceptance_shadow_4h_block.py",
    "--warmup-minutes", "30",
    "--duration-hours", "4"
)
if ($SessionId -ne "") {
    $ArgsList += @("--session-id", $SessionId)
}

Write-Host "Starting Experiment 58 fresh M-acceptance shadow block..."
Write-Host "30 minutes Candidate-M causal continuity + 4 hours fresh raw MT5 ticks."
Write-Host "No broker orders and no strategy P&L during capture."
& $Python @ArgsList
$CaptureExit = $LASTEXITCODE

if ($CaptureExit -ne 0) {
    Write-Host ""
    Write-Host "Capture did not start. Running read-only MT5 warmup diagnostic..."
    & $Python "scripts/diagnose_candidate_j_warmup.py" --symbol XAUUSD --required-minutes 30 --lookback-hours 24 --gap-sec 5
    Write-Host ""
    Write-Host "No Experiment-58 block was started by the failed attempt."
}

exit $CaptureExit
