# Journaling Contract Guide

Phase 016 introduces a versioned contract for enriched journaling payloads. The
contract covers two primary artifacts emitted by the Brain orchestrator:

1. `completed_trades.json` – array of enriched `CompletedTrade` records that
   include deterministic hash signatures and embedded fill metadata.
2. `aggregates.json` – single `JournalingAggregate` document summarising
   expectancy, checklist adherence, risk distribution, and variance metrics per
   run.

The authoritative schema lives at
`alphaforge-brain/contracts/journaling_contract.schema.json` with an accompanying
example in `alphaforge-brain/contracts/journaling_contract.example.json`.

## Validating Artifacts Locally

To validate artifacts emitted by a run, point the contract test module at the
artifacts directory. The quickest way is to run the contract-focused pytest:

```powershell
poetry run pytest alphaforge-brain/tests/contracts/test_journaling_contract.py
```

The test constructs representative artifacts and validates both the aggregate
and each completed trade against the JSON Schema using `jsonschema>=4`.

For manual validation, load both files and feed them through the schema:

```python
from json import load
from pathlib import Path
from jsonschema import validate

schema = load(open("alphaforge-brain/contracts/journaling_contract.schema.json", "r", encoding="utf-8"))
aggregate = load(open("zz_artifacts/journaling/<run_id>/aggregates.json", "r", encoding="utf-8"))
completed_trades = load(open("zz_artifacts/journaling/<run_id>/completed_trades.json", "r", encoding="utf-8"))

# Validate aggregate
validate(instance=aggregate, schema={"$schema": schema["$schema"], "$ref": "#/$defs/JournalingAggregate", "$defs": schema["$defs"]})

# Validate individual trades
trade_schema = {"$schema": schema["$schema"], "$ref": "#/$defs/CompletedTradeRecord", "$defs": schema["$defs"]}
for record in completed_trades:
    validate(instance=record, schema=trade_schema)
```

Replace `<run_id>` with the actual run identifier you want to inspect.

## Regenerating Artifacts

When running a Brain orchestrator flow, the journaling phase now emits three
files by default:

- `completed_trades.json` – enriched trades with `hash_signature` per record.
- `aggregates.json` – run-level aggregate metrics.
- `snapshots/` – per-trade context snapshots (if available).

To regenerate artifacts for a specific run:

1. Execute the run via the orchestrator or CLI (for example the integration
   deterministic replay fixture).
2. Inspect `RunOrchestrator.journaling_result` for the artifact locations and
   canonical hashes recorded.
3. Use the contract test above to confirm schema adherence.

## Expected Consumers

- **Governance Steward**: uses `aggregates.json` to track checklist adherence and
  risk distribution.
- **Frontend (Mind)**: consumes both the aggregate file and the enriched trades
  to populate dashboards once the contract is promoted.
- **Retention Automation**: leverages the `source_artifacts` field in the
  aggregate to pin related evidence during sweeps.

## Change Management

All changes to the contract must:

- Bump `schema_version` in the relevant models.
- Update `journaling_contract.schema.json` and the example payload.
- Document the change in `changelog/fragments/016-journaling-contract.md` (see
  Phase 016 polish tasks) and reference the change in the Quickstart guide for
  this feature.
