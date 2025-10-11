param(
    [string[]]$Only,
    [string]$ReportDir = "artifacts/trust_gates/reports",
    [string]$ToleranceProfile,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

$root = Resolve-Path "$PSScriptRoot\..\.." | Select-Object -ExpandProperty Path
Push-Location $root

$originalPythonPath = $env:PYTHONPATH
$exitCode = 0

try {
    $reportDirPath = if ([System.IO.Path]::IsPathRooted($ReportDir)) {
        $ReportDir
    } else {
        Join-Path $root $ReportDir
    }

    if (-not (Test-Path $reportDirPath)) {
        New-Item -ItemType Directory -Path $reportDirPath -Force | Out-Null
    }

    $pythonPath = Join-Path $root 'alphaforge-brain\src'
    if ($env:PYTHONPATH) {
        $env:PYTHONPATH = "$pythonPath$([System.IO.Path]::PathSeparator)$($env:PYTHONPATH)"
    } else {
        $env:PYTHONPATH = $pythonPath
    }

    $cmd = @("run", "python", "-m", "cli.trust_gates", "--report-dir", $reportDirPath)

    if ($Only) {
        $normalizedOnly = (
            $Only |
            ForEach-Object {
                if ($_ -ne $null) { $_.ToString().Trim() }
            } |
            Where-Object { $_ }
        ) -join ","
        if ($normalizedOnly) {
            $cmd += @("--only", $normalizedOnly)
        }
    }

    if ($PSBoundParameters.ContainsKey('ToleranceProfile') -and $ToleranceProfile) {
        $cmd += @("--tolerance-profile", $ToleranceProfile.Trim())
    }

    if ($DryRun) {
        $cmd += "--dry-run"
    }

    Write-Host "[trust-gates] invoking: poetry $($cmd -join ' ')"
    poetry @cmd

    if ($LASTEXITCODE -ne 0) {
        $exitCode = $LASTEXITCODE
        throw "Trust gates execution failed with exit code $LASTEXITCODE"
    }

    Write-Host "[trust-gates] suite completed successfully."
}
catch {
    Write-Error $_
    if ($exitCode -eq 0) {
        $exitCode = if ($LASTEXITCODE -ne 0) { $LASTEXITCODE } else { 1 }
    }
}
finally {
    if ($null -eq $originalPythonPath) {
        Remove-Item Env:PYTHONPATH -ErrorAction SilentlyContinue
    } else {
        $env:PYTHONPATH = $originalPythonPath
    }
    Pop-Location
}

if ($exitCode -ne 0) {
    exit $exitCode
}
