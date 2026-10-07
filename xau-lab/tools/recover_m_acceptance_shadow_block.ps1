param(
    [Parameter(Mandatory=$true)]
    [string]$SessionId
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

$VenvPython = Join-Path $RepoRoot ".venv\Scripts\python.exe"
$Python = if (Test-Path $VenvPython) { $VenvPython } else { "python" }

Write-Host "Recovering Experiment 58 block from the exact frozen MT5 wall-clock interval..."
Write-Host "Session: $SessionId"
Write-Host "No broker orders. Frozen start/end will not move."

& $Python "tools/recover_m_acceptance_shadow_block.py" $SessionId
exit $LASTEXITCODE
