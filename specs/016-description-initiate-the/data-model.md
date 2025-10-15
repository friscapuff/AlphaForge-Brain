# Data Model Draft — Enriched Journaling (Phase 016)

Version: 2025-10-15 (pre-implementation)

This document captures the canonical schemas that Phase 016 will implement.
Downstream code must treat these contracts as authoritative and additive-only.
All examples use JSON-like notation and assume serialization through
`hash_canonical` prior to hashing.

## CompletedTrade v2

| Field | Type | Description |
| --- | --- | --- |
| `id` | `str` | Stable identifier (existing). |
| `schema_version` | `str` | New. Defaults to `"2025.10.16"`. Breakage requires increment. |
| `symbol` | `str` | Trading symbol. |
| `entry_ts` | `datetime` | Entry timestamp (ISO8601). |
| `exit_ts` | `datetime` | Exit timestamp (ISO8601). |
| `entry_price` | `float` | VWAP-derived, ≥ 0. |
| `exit_price` | `float` | VWAP-derived, ≥ 0. |
| `quantity` | `float` | Signed position size. |
| `pnl` | `float` | Realized profit/loss. |
| `return_pct` | `float` | Directional return proportion. |
| `holding_period_secs` | `float` | Duration in seconds, ≥ 0. |
| `signal_id` | `str` | Strategy-level identifier for the decision that spawned the trade. |
| `signal_strength` | `float` | Normalized signal magnitude (–1.0 to 1.0). |
| `decision_ts` | `datetime` | Timestamp when strategy emitted the trade signal. |
| `mae` | `float` | Maximum adverse excursion from entry; ≥ 0. |
| `mfe` | `float` | Maximum favorable excursion from entry; ≥ 0. |
| `r_multiple` | `float` | Risk-adjusted return (pnl ÷ predefined risk unit). |
| `expectancy_bucket` | `str` | One of `{"negative", "neutral", "positive"}` based on expectancy heuristics. |
| `checklist_status` | `str` | Checklist outcome: `{"passed", "waived", "failed"}` (Decision 2 ties to governance manifests). |
| `risk_flag` | `str | None` | Optional: `{"elevated_position", "volatility_spike", ...}`. |
| `context_snapshot_id` | `str` | Foreign key to `TradeContextSnapshot.id`. |
| `fills` | `list[Fill] \| None` | Optional embedded fills (existing field). |

### Example

```json
{
  "id": "trade-9b2f",
  "schema_version": "2025.10.16",
  "symbol": "AAPL",
  "entry_ts": "2025-10-14T14:30:10Z",
  "exit_ts": "2025-10-14T15:45:05Z",
  "entry_price": 185.12,
  "exit_price": 186.02,
  "quantity": 200,
  "pnl": 180.0,
  "return_pct": 0.004863,
  "holding_period_secs": 4500.0,
  "signal_id": "mean_revert_v3",
  "signal_strength": 0.72,
  "decision_ts": "2025-10-14T14:29:55Z",
  "mae": 0.42,
  "mfe": 1.24,
  "r_multiple": 1.5,
  "expectancy_bucket": "positive",
  "checklist_status": "passed",
  "risk_flag": null,
  "context_snapshot_id": "ctx-9b2f",
  "fills": [
    {
      "ts": "2025-10-14T14:30:10Z",
      "order_id": "ord-001",
      "size": 200,
      "price": 185.12,
      "run_id": "run-123",
      "stop_id": "stop-mean",
      "target_id": "target-mean",
      "risk_tier": "moderate",
      "expectancy_inputs": {
        "risk_unit": 120.0,
        "spread_bps": 3.1
      }
    }
  ]
}
```

## Fill (extended)

| Field | Type | Description |
| --- | --- | --- |
| `ts` | `datetime` | Execution timestamp (existing). |
| `order_id` | `str` | Logical order identifier (existing). |
| `size` | `float` | Signed quantity (existing). |
| `price` | `float` | Execution price, ≥ 0 (existing). |
| `run_id` | `str \| None` | Optional parent run linkage (existing). |
| `stop_id` | `str \| None` | New. Identifier of associated protective stop. |
| `target_id` | `str \| None` | New. Identifier of profit target or exit heuristic. |
| `risk_tier` | `Literal["conservative", "moderate", "aggressive"]` | New. Categorizes position size v. risk budgets. |
| `expectancy_inputs` | `dict[str, float] \| None` | New. Numeric inputs that feed expectancy computation (spread, fees, risk unit). |

All new attributes default to `None` when upstream adapters cannot supply them.
Upstream writers must avoid partial dictionaries—omit the field entirely if no
values exist to preserve deterministic hashing.

## TradeContextSnapshot (new)

| Field | Type | Description |
| --- | --- | --- |
| `id` | `str` | Primary key; referenced by `CompletedTrade.context_snapshot_id`. |
| `schema_version` | `str` | Defaults to `"2025.10.16"`. |
| `trade_id` | `str` | CompletedTrade identifier. |
| `collected_at` | `datetime` | Timestamp of the snapshot capture. |
| `market_symbol` | `str` | Symbol context (allows cross-asset future use). |
| `bid` | `float \| None` | Latest bid price if available. |
| `ask` | `float \| None` | Latest ask price if available. |
| `spread_bps` | `float \| None` | Bid/ask spread in basis points. |
| `volatility_score` | `float \| None` | Normalized 0–1 volatility percentile. |
| `volume_window` | `float \| None` | Rolling volume over 5-minute window. |
| `checklist` | `dict[str, str]` | Checklist outcomes keyed by rule, value ∈ {`"passed"`, `"failed"`, `"waived"`}. |
| `indicators` | `dict[str, float]` | Ad-hoc normalized signal metrics (e.g., RSI). |
| `notes` | `str \| None` | Optional free-form note for audit waivers. |

Snapshots are persisted under `zz_artifacts/journaling/snapshots/` using file
name `trade-{trade_id}.json`. Missing market data should populate `notes` with
reason codes (e.g., "market_data_timeout").

## JournalingAggregate (new)

| Field | Type | Description |
| --- | --- | --- |
| `run_id` | `str` | Run identifier (primary grouping key). |
| `schema_version` | `str` | Defaults to `"2025.10.16"`. |
| `generated_at` | `datetime` | Artifact timestamp. |
| `artifact_hash` | `str` | Deterministic hash computed via `hash_canonical`. |
| `context_version` | `str` | Version of the journaling enrichment context and calculators. |
| `expectancy_by_strategy` | `dict[str, float]` | Mean expectancy per `signal_id`. |
| `checklist_adherence` | `dict[str, float]` | Percentage of checklist rules satisfied (0.0–1.0). |
| `risk_distribution` | `dict[str, int]` | Count of trades per `risk_tier`. |
| `mae_mfe_stats` | `dict[str, float]` | Aggregated MAE/MFE figures (mean, max). |
| `breach_flags` | `list[str]` | Any retention/governance breaches detected during generation. |
| `source_artifacts` | `list[str]` | Relative paths to component artifacts (trades, snapshots). |

Aggregates live at `zz_artifacts/journaling/manifest-{run_id}.json`. They drive
retention enforcement (Decision 2) and governance manifests. Whenever a breach
is detected, append a descriptive slug to `breach_flags` and ensure retention
policy logs include the run identifier.

## Hashing Contract

- All journaling payloads (fills, trades, snapshots, aggregates) must feed into
  `services.hashing.journaling_signature.hash_enriched_journaling_payload()` (T005).
- Inputs must be sorted canonically (dict key order, list ordering by trade id).
- The resulting hash is stored alongside artifacts and referenced by trust gates.

## Compatibility & Migration Notes

1. Existing `CompletedTrade` consumers must tolerate the additional fields; all
   new attributes are additive and never remove historical ones.
2. Historical artifacts retain schema version `2025.09.x`; serialization logic
   must branch on version when computing hashes to avoid drift.
3. Trade context snapshots and aggregates are new artifacts; retention jobs must
   classify them as full-run assets with `policy_version = 2025.10.13` (T007).
4. Documentation updates in `CONFIG_CHANGELOG.md` must mention the new budgets
   and schema versions to satisfy governance auditors.
