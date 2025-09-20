Param(
  [int]$Port = 8000,
  [switch]$Reload,
  [int]$Workers = 1,
  [string]$BindHost = "0.0.0.0"
)

Write-Host ("[dev] Launching API on http://{0}:{1} (workers={2} reload={3})" -f $BindHost,$Port,$Workers,$Reload.IsPresent) -ForegroundColor Cyan

# Ensure we are inside poetry shell (fallback to poetry run)
function Invoke-OrPoetry {
  param([string]$Cmd)
  if ($env:VIRTUAL_ENV) { Invoke-Expression $Cmd } else { poetry run $Cmd }
}

if ($Reload.IsPresent) { $reloadFlag = "--reload" } else { $reloadFlag = "" }

$cmd = "uvicorn api.app:app --host $BindHost --port $Port --workers $Workers $reloadFlag"
Invoke-OrPoetry $cmd
