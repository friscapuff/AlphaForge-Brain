# Contract Version Manifest (T050)

## Overview
This manifest documents the baseline `v1` JSON Schemas and additive `v1alpha2` extensions introduced during feature 006 execution. No breaking changes have been made; all `v1alpha2` changes are strictly additive or optional, preserving backward compatibility.

## Baseline Schemas (v1)
| Domain | Schema File | Notes |
|--------|-------------|-------|
| Candles | `chart-candles.v1.schema.json` | OHLCV array with ISO timestamps. |
| Backtest Run Request | `backtest-run-request.v1.schema.json` | Core strategy + risk + date range fields. |
| Backtest Run Create (request) | `backtest-run-create-request.v1.schema.json` | Canonical submission shape (client → server). |
| Backtest Run Create (response) | `backtest-run-create-response.v1.schema.json` | Accepted run id + status (queued). |
| Backtest Result | `backtest-result.v1.schema.json` | Equity curve, metrics, trades summary, validation placeholders. |
| Monte Carlo Paths | `montecarlo-paths.v1.schema.json` | Matrix of simulated equity paths (baseline percentiles only). |

## Additive Alpha2 Schemas / Extensions (v1alpha2)
| Domain | Schema File | Additions |
|--------|-------------|-----------|
| Backtest Run Request | `backtest-run-request.v1alpha2.schema.json` | Optional extended validation toggles; seed exposure for deterministic replay. |
| Monte Carlo Paths | `montecarlo-paths.v1alpha2.schema.json` | Extended percentile outputs (e.g., p5, p95) gated by feature flag `extendedPercentiles`. |

## Additive Fields Summary
| Area | Field(s) | Conditions | Impact |
|------|----------|-----------|--------|
| Determinism | `seed` | Optional in alpha2 request | Enables reproducible path & equity generation. |
| Extended Percentiles | `percentiles_extended` (structure dependent on schema) | Returned only when flag/param set | Provides additional statistical insight without altering baseline keys. |
| Advanced Validation | `advanced.validation.*` (toggles) | Ignored unless feature flag enabled | Future expansion; currently pass-through. |

## Compatibility Guarantees
- All `v1` clients remain compatible: no required fields added, no removals, no semantic changes to existing keys.
- Alpha2 fields are optional and feature-flag or parameter gated.
- Server SHOULD omit alpha2 fields if unsupported flags/params are absent.

## Versioning Policy
- `v1` remains the stable base; `v1alpha2` acts as a staging surface for FR extensions (EXT-PCT, EXT-VAL).
- Promotion path: once stable & universally deployed, alpha2 fields can migrate into a `v2` (or `v1` minor revision) with deprecation notice for prior alpha2 indicators.

## Traceability Mapping
| Feature Requirement | Related Tasks | Schema(s) |
|---------------------|--------------|-----------|
| EXT-PCT (Extended Percentiles) | T010 T043 T044 T046 T051 | `montecarlo-paths.v1alpha2.schema.json` |
| EXT-VAL (Advanced Validation Toggles) | T010 T047 T051 | `backtest-run-request.v1alpha2.schema.json` |
| Deterministic Replay | T026 T036 T078 (planned) | `backtest-run-request.v1alpha2.schema.json` (seed) |

## Change Log
| Date | Change | Schema | Notes |
|------|--------|--------|-------|
| 2025-09-27 | Initial manifest creation | All listed | Established baseline vs alpha2 delineation. |

## Outstanding / Future
- Correlation ID propagation (planned observability) may introduce a header-level convention (non-schema) — documented separately under observability tasks.
- Potential `walk_forward.splits.metrics` expansion slated for later task (T101) — will require alpha schema extension.

---
Generated as part of T050 to formalize additive evolution strategy.
