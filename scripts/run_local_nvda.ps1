<#
.SYNOPSIS
  Canonical local NVDA run helper (T041).

.DESCRIPTION
  Executes a deterministic NVDA backtest run via the FastAPI app using the in-process runner.
  Produces (or reuses) a run hash, prints key artifact paths, and optionally dumps summary JSON.

.PARAMETER Start
  ISO start date (default: 2024-01-01)

.PARAMETER End
  ISO end date (default: 2024-01-10)

.PARAMETER Timeframe
  Timeframe string (default: 1m)

.PARAMETER Output
  Optional path to write run detail JSON.

.EXAMPLE
  pwsh ./scripts/run_local_nvda.ps1 -Start 2024-01-01 -End 2024-01-10 -Output run.json

.NOTES
  Requires: poetry install; runs with 'poetry run'
  Idempotent: re-running prints same run_hash if inputs + dataset unchanged.
#>

param(
  [string]$Start = "2024-01-01",
  [string]$End = "2024-01-10",
  [string]$Symbol = "NVDA",
  [string]$Timeframe = "1m",
  [string]$Output = ""
)

function Invoke-Run {
  param($Body)
  $json = $Body | ConvertTo-Json -Depth 10 -Compress
  $py = @'
import json,sys
from api.app import create_app
from fastapi.testclient import TestClient
from domain.schemas.run_config import RunConfig, IndicatorSpec, StrategySpec, RiskSpec, ValidationSpec, ExecutionSpec

body = json.loads(sys.stdin.read())
app = create_app()
client = TestClient(app)

r = client.post('/runs', json=body)
if r.status_code not in (200,201):
    print(f"ERROR run creation: {r.status_code} {r.text}", file=sys.stderr)
    sys.exit(1)
run_hash = r.json()['run_hash']
detail = client.get(f'/runs/{run_hash}', params={'include_anomalies':'true'})
print(json.dumps({'run_hash':run_hash,'detail':detail.json()}, separators=(',',':')))
@'
  $proc = Start-Process -FilePath poetry -ArgumentList @('run','python','-c',$py) -NoNewWindow -PassThru -RedirectStandardInput pipe -RedirectStandardOutput pipe -RedirectStandardError pipe
  $sw = New-Object System.IO.StreamWriter($proc.StandardInput.BaseStream)
  $sw.Write($json)
  $sw.Close()
  $stdout = $proc.StandardOutput.ReadToEnd()
  $stderr = $proc.StandardError.ReadToEnd()
  $proc.WaitForExit()
  if($proc.ExitCode -ne 0){
    Write-Error "Run failed: $stderr"
    exit $proc.ExitCode
  }
  return $stdout
}

$payload = @{
  start = $Start; end = $End; symbol = $Symbol; timeframe = $Timeframe;
  indicators = @(
    @{ name = 'sma'; params = @{ window = 5 } },
    @{ name = 'sma'; params = @{ window = 15 } }
  );
  strategy = @{ name = 'dual_sma'; params = @{ fast = 5; slow = 15 } };
  risk = @{ model = 'fixed_fraction'; params = @{ fraction = 0.1 } };
  execution = @{ mode = 'sim'; slippage_bps = 0; fee_bps = 0; borrow_cost_bps = 0 };
  validation = @{ permutation = @{ trials = 5 } };
  seed = 123
}

Write-Host "[NVDA] Submitting deterministic run ($($payload.symbol) $($payload.start)->$($payload.end) tf=$Timeframe)" -ForegroundColor Cyan
$out = Invoke-Run -Body $payload | ConvertFrom-Json
$runHash = $out.run_hash
Write-Host "Run hash: $runHash" -ForegroundColor Green
$artDir = Join-Path -Path "artifacts" -ChildPath $runHash
$manifest = Join-Path $artDir 'manifest.json'
Write-Host "Artifacts: $artDir" -ForegroundColor Yellow
if(Test-Path $manifest){ Write-Host "Manifest: $manifest" }
if($Output){
  $out.detail | ConvertTo-Json -Depth 12 | Out-File -FilePath $Output -Encoding UTF8
  Write-Host "Detail written to $Output" -ForegroundColor Magenta
}
Write-Host "Anomaly counters:" ($out.detail.summary.anomaly_counters | ConvertTo-Json -Compress)

exit 0
