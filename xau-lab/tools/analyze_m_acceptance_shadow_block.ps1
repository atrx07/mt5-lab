param(
    [Parameter(Mandatory=$true)]
    [string]$SessionId,
    [switch]$CountOnly
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

$VenvPython = Join-Path $RepoRoot ".venv\Scripts\python.exe"
$Python = if (Test-Path $VenvPython) { $VenvPython } else { "python" }
$SessionDir = Join-Path $RepoRoot ("data\prospective_m_acceptance_shadow\" + $SessionId)

$ArgsList = @(
    "research/v4_5_m_acceptance_discrimination.py",
    "--session-dir", $SessionDir
)
if ($CountOnly) {
    $ArgsList += "--count-only"
    Write-Host "Experiment 58 count-only mode: entry counts only; outcome labels are not written."
} else {
    Write-Host "Experiment 58 full extraction: causal features + explicitly separated label_* columns."
}

& $Python @ArgsList
exit $LASTEXITCODE
