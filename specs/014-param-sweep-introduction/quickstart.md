# Quickstart – Param Sweep Introduction

## Prerequisites
- Poetry environment installed (`poetry install` already provisioned for AlphaForge Brain)
- Benchmark artifacts refreshed (`poetry run pytest tests/ci/test_perf_gates_script.py`)
- Ensure `AF_OPTIMIZATION_MAX_COMBINATIONS` is set to an appropriate cap (e.g., `20` for local testing)

## Running a Sweep Locally
1. **Activate environment**
   ```powershell
   poetry shell
   ```
2. **Submit a sweep request** using the existing backtest CLI or REST client:
   ```powershell
   poetry run python scripts/cli/backtests.py submit-sweep --payload payloads/dual_sma_sweep.json
   ```
   Example payload fragment:
   ```json
   {
     "strategy": {
       "name": "dual_sma",
       "parameters": {
         "fast": {"mode": "list", "values": [5, 8, 13]},
         "slow": {"mode": "range", "range": {"start": 30, "stop": 61, "step": 15}}
       }
     }
   }
   ```
    Multi-ticker payloads extend the schema with a `tickers` array. Each ticker references the same strategy definition and optional overrides:
    ```json
    {
       "tickers": [
          {"symbol": "AAPL"},
          {"symbol": "MSFT", "overrides": {"fast": {"mode": "single", "value": 10}}}
       ],
       "strategy": {
          "name": "dual_sma",
          "parameters": {
             "fast": {"mode": "list", "values": [5, 8, 13]},
             "slow": {"mode": "range", "range": {"start": 30, "stop": 61, "step": 15}}
          }
       }
    }
    ```
    The backend normalizes each ticker separately—no cartesian cross-products occur. If any ticker exceeds the combination cap, its section is rejected with `cap_status=hit` while others continue only when a waiver is recorded.
3. **Monitor status**
   ```powershell
   curl http://127.0.0.1:8000/api/v1/sweeps/<sweep_id>
   ```
4. **Inspect artifacts**
   - Parent manifest: `zz_artifacts/sweeps/<sweep_id>/manifest.json`
   - Per-ticker manifests: `zz_artifacts/sweeps/<sweep_id>/<ticker>/manifest.json`
   - Child runs: standard run directories keyed by `run_hash`
      - Review each per-ticker manifest for `variance_metrics` (PNL, drawdown, trade count) to confirm ≤0.1% deltas versus baseline single runs. A `data_quality_status` of `review` indicates the threshold failed and requires follow-up.
5. **Capture telemetry evidence**
   - Audit log entries are appended to `zz_artifacts/governance_audit.log` with `sweep.checkpoint` and `sweep.guardrail` events documenting `cap_status`, `data_quality_status`, and `recorded_at` timestamps.
   - Prometheus metrics `sweep_checkpoint_latency_seconds`, `sweep_combinations_total`, and `sweep_guardrail_events_total` are labelled by `sweep_id`, `ticker`, and guardrail state—scrape `/metrics` or tail the snapshot emitted by CI to validate values.

## Governance Checklist
- Confirm sweep rejected when combinations exceed `AF_OPTIMIZATION_MAX_COMBINATIONS`
- Verify parent manifest lists every child run and aggregates (total, succeeded, failed)
- Review per-ticker manifest entries for `data_quality_status` across checkpoints (payload, normalization, orchestrator, manifest)
- Ensure monitoring dashboard reflects sweep metrics (counts, durations, cap hits, data-quality alerts) within 60 seconds; `sweep_checkpoint_latency_seconds` should register the latest checkpoints
- Confirm `cap_status` and `data_quality_status` telemetry fields appear in Prometheus and `zz_artifacts/governance_audit.log`, distinguishing data-quality failures from cap rejections; latency metrics per checkpoint should demonstrate SC-002/SC-004 compliance
- Run `poetry run pytest tests/perf/test_sweep_rejection_latency.py` to verify cap rejection completes in <2 seconds, `poetry run pytest tests/governance/test_sweep_telemetry_latency.py` to validate telemetry arrival (<60 s), and `poetry run pytest tests/governance/test_sweep_data_quality_variance.py` for SC-006 variance coverage
- Update `docs/operations/trust_gates.md` with sweep-specific audit instructions and per-ticker evidence links

## Troubleshooting
- **Validation error**: Check payload for overlapping list/range definitions producing duplicates; deduplicate inputs.
- **Cap hit**: Increase `AF_OPTIMIZATION_MAX_COMBINATIONS` cautiously and document waiver if exceeding governance default.
- **Telemetry missing**: Confirm monitoring exporter is running and sweep emits audit log entries under `zz_artifacts/governance_audit.log`.
