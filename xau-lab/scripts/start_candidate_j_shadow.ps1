param(
    [switch]$ConnectCheck,
    [string]$SessionId = ""
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

$VenvPython = Join-Path $RepoRoot ".venv\Scripts\python.exe"
$Python = if (Test-Path $VenvPython) { $VenvPython } else { "python" }

if ($ConnectCheck) {
    & $Python "scripts/live_shadow_candidate_j.py" --connect-check
    exit $LASTEXITCODE
}

$ArgsList = @("scripts/live_shadow_candidate_j.py")
if ($SessionId -ne "") {
    $ArgsList += @("--session-id", $SessionId)
}

Write-Host "Starting read-only Candidate D/H/J shadow..."
Write-Host "No broker orders will be sent."
& $Python @ArgsList
exit $LASTEXITCODE
