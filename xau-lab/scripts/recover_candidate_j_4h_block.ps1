param(
    [Parameter(Mandatory=$true)]
    [string]$SessionId
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

$VenvPython = Join-Path $RepoRoot ".venv\Scripts\python.exe"
$Python = if (Test-Path $VenvPython) { $VenvPython } else { "python" }

Write-Host "Recovering exact frozen Candidate J 4-hour block from MT5 history..."
Write-Host "No broker orders will be sent."
& $Python "scripts/recover_candidate_j_4h_block.py" $SessionId
exit $LASTEXITCODE
