# Data Model: Unified Trade & Equity Consistency

Feature: 008-trade-model-proliferation
Spec: specs/008-trade-model-proliferation/spec.md
Plan: specs/008-trade-model-proliferation/plan.md
Research: specs/008-trade-model-proliferation/research.md

## 1. Canonical Entities
| Entity | Purpose | Key Fields | Notes | Hash Participation |
|--------|---------|-----------|-------|--------------------|
| Fill | Atomic execution event (position delta) | ts, symbol, side, quantity, price, fees?, slippage?, run_id?, strategy_id | Replaces mixed legacy Trade usages | Included via run pipeline (indirect) |
| CompletedTrade | Aggregated round-trip summary | entry_ts, exit_ts, side, qty, entry_price, exit_price, pnl, return_pct, holding_period_bars | Derived; not all fills form a completed trade | Metrics & hashing may ignore direct; derived metrics only |
| EquityBar | Per-bar portfolio snapshot | ts, nav, peak_nav, drawdown, gross_exposure, net_exposure, trade_count_cum | Same validation except external epsilon | Direct equity hash input |
| MetricsSummary (logical) | Aggregated scalar performance measures | sharpe, max_drawdown, trade_count, win_rate, exposure_pct, turnover | Not a persisted table; serialized in API | metrics_signature |
| ValidationResult | Statistical validation per metric | metric_name, observed_value, p_value, caution_threshold | Caution gating uses p_value | Not hashed into run_hash (separate artifact) |
| RunManifest (extended) | Provenance & version info | config_signature, trade_model_version, feature_flags_active | Added trade_model_version metadata | Hashed except trade_model_version excluded |

## 2. Legacy → Canonical Mapping
| Legacy Construct | New Mapping | Adapter Strategy | Removal Phase |
|------------------|-------------|------------------|---------------|
| models.trade.Trade (fill semantics) | Fill | Thin wrapper export | Phase 7 |
| domain.execution.state.Trade (dataclass round-trip) | CompletedTrade | Materialize via builder | Phase 7 |
| ORM trades table (mixed fields) | Fill (core) + Derived CompletedTrade (in-memory) | No schema rewrite initially | Later migration optional |
| services.equity.EquityState | Internal accumulator only | Keep internal | Persist as EquityBar only |
| metrics_hash.equity_curve_hash variants | hashes.equity_signature | Deprecation shim | Phase 7 |

## 3. Field Specifications
### Fill
| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| ts | datetime (UTC) | required | Source bar close time |
| symbol | str | non-empty | Single-symbol currently |
| side | enum(BUY,SELL) | required | Direction of position delta |
| quantity | float | >0 | Positive absolute trade size |
| price | float | >0 | Execution price |
| fees | float | >=0 optional | Basis points converted or absolute; spec refine later |
| slippage | float | optional | Modeled cost |
| run_id | str | optional | Linked after run persisted |
| strategy_id | str | required | Strategy provenance |

### CompletedTrade
| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| entry_ts | datetime | required | First fill timestamp |
| exit_ts | datetime | required | Final fill closing position |
| side | enum(LONG,SHORT) | required | Net direction |
| qty | float | >0 | Net absolute size |
| entry_price | float | >0 | VWAP entry (simplified here) |
| exit_price | float | >0 | VWAP exit |
| pnl | float | any | Realized profit/loss |
| return_pct | float | any | (exit-entry)/entry normalized |
| holding_period_bars | int | >=0 | Derived from bar count |

### EquityBar
No schema change; add config-driven epsilon for drawdown validation.

## 4. Hashing Inputs Standardization
| Signature | Input Order | Exclusions |
|-----------|-------------|------------|
| equity_signature | list[EquityBar] sorted by ts | None (except internal epsilon not hashed) |
| metrics_signature | sorted(metric_key=value) stable serialization | Exclude volatile debug counters |

## 5. Contract Changes (API)
| Payload Section | Change | Backward Compatible? | Flag |
|-----------------|--------|----------------------|------|
| backtest.validation_caution | New boolean | Yes (additive) | always (no flag) |
| backtest.optimization_mode | New enum | Yes (additive) | optimization warn feature |
| backtest.advanced.warnings[] | New list | Yes | optimization warn feature |

Implementation Status (2025-10-01):
- Fields `validation_caution` & `optimization_mode` now present in `GET /api/v1/backtests/{run_id}` with default `null` values (Phase 1 placeholder; logic arrives in T040+ and T050+ respectively).
- `advanced.warnings` key is injected as an empty list when the `advanced` object is supplied in the submission payload, locking the nested contract shape early (supports forthcoming warning emission T051).
- No hashing impact: run_hash, metrics_hash, equity_curve_hash remain unchanged because new fields are excluded from hash calculations and are `None` / empty.

## 6. Drawdown Epsilon Config
`settings/determinism.py` centralizes the tolerance:
```
DRAWNDOWN_EPSILON  # parsed once; env override AF_DRAWNDOWN_EPSILON; default 1e-9
```
EquityBar currently still uses a literal 1e-9; future patch (T013 follow-up) will swap to this constant when normalization work lands to avoid dual moving parts.

## 7. Migration Strategy
- Schema: No immediate DB column rename (risk containment). Future optional rename migration.
- Adapters: Provide translation functions `legacy_trade_to_fill()`, `fills_to_completed_trades()`.
- Manifest: Add `trade_model_version = 2` (excluded from run hash by policy) & `feature_flags_active` list.
- Rollback: Disable feature flags; adapters still intact until Phase 7.

## 8. Rejection Log (Simpler Alternatives)
| Alternative | Reason Rejected |
|------------|-----------------|
| Rename ORM table now | Increases migration risk early; low ROI initially |
| Include trade_model_version in hash | Breaks historical comparability |
| Per-run epsilon | Unjustified complexity; determinism should be global |

## 9. Open Issues (to watch)
| Issue | Trigger Condition |
|-------|------------------|
| Need multi-symbol extension | When multi-symbol strategies introduced |
| Need VWAP accuracy improvements | If entry/exit price aggregation error > tolerance |

## 10. Feature Flags (Planned)
| Flag | Purpose | Default |
|------|---------|---------|
| AF_UNIFIED_TRADES | Emit canonical Fill / CompletedTrade & equity adapter | off |
| AF_EQUITY_NORMALIZER_V2 | Remove legacy NAV scaling (unscaled nav side-by-side) | off |

## 11. Additional Clarifications
- CompletedTrade canonical implementation uses `holding_period_secs` (seconds) instead of legacy `holding_period_bars` for finer resolution. Mapping logic will compute both during transition; only seconds persist in canonical model.
- EquityBar `nav` is already treated as unscaled here; normalization flag will enable dual-run comparison to legacy scaled path for regression tests.
- Fill model intentionally omits strategy_id / symbol fields in first pass (present in legacy concept table) to minimize ripple; symbol lives at run context until multi-symbol expansion.

## 12. Completion Criteria (Phase 1 Data Model)
- Canonical models (Fill, CompletedTrade, EquityBar doc update) implemented
- Determinism settings module added
- Adapters specified (implementation pending T017)
- API additive fields documented
- Feature flag plan enumerated
