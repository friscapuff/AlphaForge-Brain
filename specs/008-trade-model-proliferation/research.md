# Research: Unified Trade & Equity Consistency Initiative (Phase 0)

Feature: 008-trade-model-proliferation
Date: 2025-10-01
Spec: specs/008-trade-model-proliferation/spec.md
Plan: specs/008-trade-model-proliferation/plan.md

## 1. Model & Representation Inventory
| Concept | File(s) (current) | Type | Notes | Planned Canonical Mapping |
|---------|-------------------|------|-------|---------------------------|
| Trade (execution record) | src/models/trade.py | Pydantic | Atomic fill-like event (has price/qty) | Fill |
| Trade dataclass (round-trip) | src/domain/execution/state.py | dataclass | Aggregated entry/exit w/ pnl | CompletedTrade |
| ORM Trade row | src/infra/orm/models.py (Trade) | SQLAlchemy ORM | Mixed semantics (fill + position_after + pnl) | Fill (persist) + derive CompletedTrade in-memory |
| EquityBar | src/models/equity_bar.py | Pydantic | Per-trade bar (not per time bar) currently | EquityBar (unchanged semantics; later may bar-align) |
| EquityState | src/services/equity.py | dataclass | Mutable accumulation (nav, peak, position, trade_count) | Internal only (no direct canonical exposure) |
| PositionState | src/services/execution.py | dataclass | Holding current position for delta generation | Internal (adapter hidden) |
| _infer_trades (builder) | src/domain/execution/state.py | function | Converts fills dataframe -> derived trades DataFrame | Will be replaced by CompletedTrade builder on Fill list |
| build_equity | src/services/equity.py | function + EquityState | Applies 1_000_000 scale heuristic | Will call DeterministicEquityNormalizer (FR-003) |
| metrics.compute_metrics | src/services/metrics.py | function | Consumes EquityBar list | Merged into metrics_core (FR-005) |
| metrics_hash.equity_curve_hash | src/services/metrics_hash.py | function | Legacy equity hashing variants | Consolidate into services/hashes.py (FR-008) |

(Will expand with automated grep results; commit T001.)
Status: Populated via automated grep scan (T001 complete). Remaining expansion only if new constructs discovered later.

## 2. Baseline Determinism Hashes (Target Artifact: artifacts/baseline_hashes_v1.json)
Placeholder until T002 executed.
```
{
  "strategies": [
    {"id": "sma_fast_slow", "seed": 123, "run_hash": "<pending>", "metrics_hash": "<pending>", "equity_hash": "<pending>"},
    {"id": "sma_single", "seed": 123, "run_hash": "<pending>", "metrics_hash": "<pending>", "equity_hash": "<pending>"},
    {"id": "sma_noise", "seed": 456, "run_hash": "<pending>", "metrics_hash": "<pending>", "equity_hash": "<pending>"}
  ],
  "created_at": "<timestamp>"
}
```
Implementation Script: `scripts/baseline_capture.py` (added) will generate the above manifest upon execution.

## 3. Performance Baseline (Target Artifact: artifacts/perf_baseline.json)
Methodology: run backtest CLI (or orchestrator API call) 5 times on 10k bars (synthetic dataset) collecting wall-clock seconds & memory peak (RSS if available).
Metric: median wall-clock; acceptance threshold future phases < +5% (alert ≥3%).

Placeholder sample table:
| Run | Wall Clock (s) | Peak RSS (MB) |
|-----|----------------|---------------|
| 1 | <pending> | <pending> |
| 2 | <pending> | <pending> |
| 3 | <pending> | <pending> |
| 4 | <pending> | <pending> |
| 5 | <pending> | <pending> |
| Median | <pending> | <pending> |

## 4. Metric Key Inventory
Collected via grep across `src/` (services.metrics, domain.metrics.calculator, validation, API).

```
current_metric_keys: [
  "sharpe", "max_drawdown", "trade_count", "return", "total_return",
  "sharpe_mean", "sharpe_min", "sharpe_max"
]
legacy_or_alt_forms: ["max_dd" (validation summaries), "return_pct" (trade-level, not aggregated), "pnl"]
validation_distributions_keys: ["observed_metric", "distribution"]
source_files: [
  "src/services/metrics.py",
  "src/domain/metrics/calculator.py",
  "src/domain/validation/runner.py",
  "src/domain/validation/walk_forward.py",
  "src/domain/validation/monte_carlo.py",
  "src/api/routes/v1_backtests.py"
]
collisions_or_aliases: [
  { "alias": "max_dd", "canonical":"max_drawdown", "action": "Preserve alias only in validation internal, canonical outward remains max_drawdown" },
  { "alias": "return", "canonical": "total_return", "action": "Document total_return as API-facing; internal calculators may output return" }
]
normalization_decisions:
  - Preserve existing outward keys (Decision #4) and add new only if needed
  - Provide translation map in metrics_core for alias -> canonical for hashing stability
hashing_implication:
  - metrics_signature must use canonical ordering of: max_drawdown, sharpe, total_return (if present), trade_count, then any extended keys sorted alphabetically
```
Status: Populated (T004 complete). Remaining step: implement alias resolution in consolidation phase (T021).

## 5. Risk Register
| Risk | Category | Impact | Likelihood | Mitigation | Owner | Trigger Task |
|------|----------|--------|------------|------------|-------|--------------|
| Hash drift after consolidation | Determinism | High | Medium | Dual-run diff tests (T023,T072,T080) | Dev | T020 |
| Precision loss removing scaling | Numerical | Medium | Medium | Dual-run equity diff harness (T031) | Dev | T030 |
| Adapter removal too early | Migration | High | Low | Keep shims until Phase 7, flag gating | Dev Lead | T070 |
| Performance regression >5% | Performance | High | Low | Early alert at 3% (T081) | Perf | T030 |
| Retention logic misclassifies caution | Business Logic | Medium | Low | Dedicated tests (T041,T082) | QA | T040 |
| Optimization warning ignored | UX | Low | Medium | Prominent UI badge (T052) | Frontend | T050 |
| Metric alias inconsistency (max_dd vs max_drawdown) | Consistency | Medium | Medium | Central alias map in metrics_core; canonical ordering in hashing | Dev | T021 |
| Mixed semantics in ORM Trade row (pnl & position_after) | Domain Purity | Medium | Medium | Treat as Fill persistence only; derive CompletedTrade in-memory; migration script docs | Dev | T060 |
| EquityBar granularity mismatch (per-trade vs per-bar) | Future Extension | Low | Medium | Document current assumption; add Phase N task if bar-level timeline required | PM | T033 |

## 6. Decision Log (from Clarifications Session 2)
| # | Decision | Rationale | Potential Revisit Condition |
|---|----------|-----------|-----------------------------|
| 1 | Exclude trade model version from hash | Preserve legacy baselines | If structural change affects semantics |
| 2 | No immediate equity recompute | Avoid broad diff noise | If compatibility layer complexity grows |
| 3 | Defer optimization execution | Scope containment | Demand for parameter sweeps increases |
| 4 | Preserve metric keys | Reduce frontend churn | Consistency overhaul initiative |
| 5 | Exclude caution runs from promotion | Risk mitigation | Too many false positives |
| 6 | Global epsilon config | Uniform determinism | Need per-strategy tolerance |
| 7 | Backend-first deploy w/ flags | Safe rollout | Frontend lag causes UX inconsistency |
| 8 | Dual output for migration script | Human + machine audit | Pipeline automation replacing manual review |
| 9 | Temporary feature flags | Reduce config sprawl | Need persistent safety toggle |
| 10 | 5% perf cap / 3% alert | Guard regressions | New hardware/perf baseline shift |

## 7. Observability & Instrumentation Plan
- Add logging around hashing consolidation (T020) with before/after counts.
- Emit timing span for equity normalization (T030) including slowdown % vs baseline.
- Validation caution gating logs metrics that triggered caution (T040).
- Migration script structured JSON includes counts transformed & skipped.

## 8. Open Questions (None)
All clarifications resolved; future questions added here if discovered.

## 9. Exit Criteria (Phase 0)
- Table populated (T001 complete)
- Baseline hash JSON persisted (T002)
- Performance baseline JSON persisted (T003)
- Metrics key list populated (T004)
- Risk register & decision log committed (this file)

---
Pending tasks will progressively replace <pending> placeholders.
