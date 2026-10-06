$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

$VenvPython = Join-Path $RepoRoot ".venv\Scripts\python.exe"
$Python = if (Test-Path $VenvPython) { $VenvPython } else { "python" }

$Sessions = @(
    "20260928T150531Z",
    "20260929T132027Z",
    "20261001T171601Z",
    "20261002T071041Z",
    "20261002T132739Z",
    "20261005T132049Z"
)

$BlockRoot = Join-Path $RepoRoot "data\prospective_4h"
$Output = Join-Path $RepoRoot "results\simulations\2026-10-06-v4_5-candidate-j-stage1-prospective"

Write-Host "Experiment 48 Stage-1 frozen six-block validation"
Write-Host "Sessions:"
$Sessions | ForEach-Object { Write-Host "  $_" }
Write-Host ""
Write-Host "This verifies all six manifests/hashes before evaluating D/H/J."
Write-Host "No external data. Final20 remains sealed."

& $Python "research/v4_5_candidate_j_stage1_staged_validation.py" `
    $BlockRoot @Sessions --output $Output
exit $LASTEXITCODE
