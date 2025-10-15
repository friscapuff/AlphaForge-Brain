# Quickstart — Enriched Journaling Contracts (Phase 016)

This guide walks through generating enriched journaling artifacts, validating
them against the published contract, and exporting the resulting aggregates for
downstream consumers.

## 1. Environment Prerequisites

- Poetry-managed Python 3.11 environment (activate with `poetry shell`).
- AlphaForge Brain dependencies installed (`poetry install`).
- Latest journaling feature branch (`016-description-initiate-the`).

## 2. Generate Enriched Journaling Artifacts

Run any deterministic backtest or use the regression fixtures to emit enriched
artifacts. The orchestrator automatically writes to
`zz_artifacts/journaling/<run_id>/`.

```powershell
poetry run pytest alphaforge-brain/tests/integration/journaling/test_completed_trade_enrichment.py -k run-journaling-001
```

On success the directory will contain:

- `completed_trades.json`
- `aggregates.json`
- `snapshots/` (per-trade context snapshots when available)
- `reasons.json` (only when diagnostics are emitted)

## 3. Validate Contracts

Use the contract-focused pytest to validate both the aggregate and the per-trade
payloads against `journaling_contract.schema.json`:

```powershell
poetry run pytest alphaforge-brain/tests/contracts/test_journaling_contract.py
```

Manual validation snippet (replace `<run_id>` with the actual run identifier):

```python
from json import load
from pathlib import Path
from jsonschema import validate

schema = load(open("alphaforge-brain/contracts/journaling_contract.schema.json", "r", encoding="utf-8"))
aggregate = load(open(f"zz_artifacts/journaling/<run_id>/aggregates.json", "r", encoding="utf-8"))
completed_trades = load(open(f"zz_artifacts/journaling/<run_id>/completed_trades.json", "r", encoding="utf-8"))

aggregate_schema = {"$schema": schema["$schema"], "$ref": "#/$defs/JournalingAggregate", "$defs": schema["$defs"]}
trade_schema = {"$schema": schema["$schema"], "$ref": "#/$defs/CompletedTradeRecord", "$defs": schema["$defs"]}

validate(instance=aggregate, schema=aggregate_schema)
for record in completed_trades:
    validate(instance=record, schema=trade_schema)
```

## 4. Export or Share Artifacts

To package the artifacts for downstream teams (e.g., Mind), copy the entire
`zz_artifacts/journaling/<run_id>/` directory. The aggregate document contains a
`source_artifacts` field that enumerates every file required for retention
pinning and contract verification.

## 5. Troubleshooting

- **Schema validation failures**: ensure `poetry install` pulled `jsonschema>=4`
and confirm the schema version matches `2025.10.16`.
- **Missing aggregates**: the writer skips aggregates when no trades are present.
  Verify the run produced trades and that journaling is enabled.
- **Retention checks**: run `poetry run python alphaforge-brain/scripts/retention_cli.py sweep --evidence zz_artifacts/retention_audit.log`
after generating artifacts to confirm the new files honor policy budgets.
