param(
    [string]$Only,
    [string]$ReportDir = "artifacts/trust_gates/reports",
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

$root = Resolve-Path "$PSScriptRoot\..\.." | Select-Object -ExpandProperty Path
Set-Location $root

if (-not (Test-Path $ReportDir)) {
    New-Item -ItemType Directory -Path $ReportDir | Out-Null
}

$pythonPath = Join-Path $root 'alphaforge-brain\src'
if ($env:PYTHONPATH) {
    $env:PYTHONPATH = "$pythonPath$([System.IO.Path]::PathSeparator)$($env:PYTHONPATH)"
} else {
    $env:PYTHONPATH = $pythonPath
}

$cmd = @("run", "python", "-m", "cli.trust_gates", "--report-dir", $ReportDir)
if ($Only) {
    $cmd += @("--only", $Only)
}
if ($DryRun) {
    $cmd += "--dry-run"
}

Write-Host "[trust-gates] invoking: poetry $($cmd -join ' ')"
poetry @cmd

if ($LASTEXITCODE -ne 0) {
    Write-Error "Trust gates execution failed with exit code $LASTEXITCODE"
    exit $LASTEXITCODE
}

Write-Host "[trust-gates] suite completed successfully."
