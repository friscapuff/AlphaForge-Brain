# Data Model: Truthful Run Foundation

## Overview
Entities derived from spec FR-001..FR-049 and Phase 0/Walk-Forward research. Focus: deterministic replay, causality enforcement, auditability, additive evolution, robustness validation.

## Entity Definitions

### DatasetSnapshot
| Field | Type | Notes |
|-------|------|-------|
| path | str | Canonical dataset path/ref id |
| data_hash | str (sha256) | Content hash used in run hashing (FR-001) |
| calendar_id | str | Exchange calendar (FR-002) |
| bar_count | int | Derived validation metric |
| first_ts | datetime | UTC |
| last_ts | datetime | UTC |
| gap_count | int | Unexpected gaps (FR-002/030) |
| holiday_gap_count | int | Calendar aligned gaps |
| duplicate_count | int | Should be 0 post-normalization |

### FeatureSpec
| Field | Type | Notes |
| name | str | Registry key (FR-004) |
| version | str | Feature registry version tag |
| inputs | list[str] | Required base columns |
| params | dict[str, Any] | Parameterization |
| shift_applied | bool | True if global +1 shift active (FR-005) |

### StrategyConfig
| Field | Type | Notes |
| id | str | Strategy identifier |
| required_features | list[str] | Subset of registry names (FR-004) |
| parameters | dict[str, Any] | Strategy specific |

### ExecutionConfig
| Field | Type | Notes |
| fill_policy | enum("NEXT_BAR_OPEN","NEXT_TICK_SURROGATE") | FR-007 |
| lot_size | int | Minimum tradable lot |
| rounding_mode | enum("FLOOR","ROUND","CEIL") | Applied pre-trade (FR-009) |

### CostModelConfig
| Field | Type | Notes |
| slippage_bps | float | FR-008 |
| spread_pct | float? | Optional extended model input |
| participation_rate | float? | Mutually exclusive with spread_pct |
| fee_bps | float | Commission (FR-008) |
| borrow_cost_bps | float | Borrow accrual (FR-039) |

### ValidationConfig
| Field | Type | Notes |
| permutation_trials | int | N (FR-020/022) |
| seed | int | Base seed (FR-019) |
| caution_p_threshold | float | For FR-021 |

### RunConfig
| Field | Type | Notes |
| dataset | DatasetSnapshot | Bound snapshot |
| features | list[FeatureSpec] | Requested feature specs |
| strategy | StrategyConfig | Strategy + params |
| execution | ExecutionConfig | Execution behavior |
| costs | CostModelConfig | Cost modeling |
| validation | ValidationConfig | Statistical validation |
| causality_shift | bool | Global +1 features shift (FR-005) |
| strict_causality_guard | bool | Default True (ISSUE-GUARD-001) |

### Trade
| Field | Type | Notes |
| ts | datetime | Execution timestamp |
| side | enum("BUY","SELL") | Direction |
| qty | int | Post-lot rounding quantity |
| pre_cost_price | float | Price before costs |
| exec_price | float | Price after slippage/fees |
| fill_policy | enum | Copied from ExecutionConfig |
| slippage_model | str? | Identifier (if extended model) |
| bps_slippage | float | Applied bps component |
| fee_bps | float | Commission rate |
| borrow_accrued | float | Cost this bar if short |
| position_after | int | Post-trade position |
| cash_after | float | Post-trade cash |
| hash | str? | Optional row hash for audit |

### EquityBar
| Field | Type | Notes |
| ts | datetime | Bar timestamp |
| equity | float | Total portfolio value |
| realized_pnl | float | Realized component |
| unrealized_pnl | float | Unrealized component |
| cost_drag | float | Sum of costs this bar |
| position | int | End-of-bar position |

### ValidationResult (Permutation)
| Field | Type | Notes |
| observed_statistic | float | Strategy performance metric |
| distribution | list[float] | Trials results (precision=8) |
| p_value | float | Empirical p (FR-020) |
| trials | int | Count |
| distribution_hash | str | Hash of ordered distribution |

### WalkForwardSegment
| Field | Type | Notes |
|-------|------|-------|
| segment_index | int | Sequential order starting at 0 (FR-046) |
| train_start | datetime | Inclusive in-sample start |
| train_end | datetime | Inclusive in-sample end |
| test_start | datetime | Inclusive out-of-sample start |
| test_end | datetime | Inclusive out-of-sample end |
| optimized_params_hash | str | Hash of parameter set chosen on in-sample |
| in_sample_metrics | dict[str, float] | Sharpe, return, drawdown, etc. |
| out_sample_metrics | dict[str, float] | Same schema as in-sample |
| stability_flag | bool | True if deviation > threshold (FR-047) |

### WalkForwardAggregate
| Field | Type | Notes |
|-------|------|-------|
| total_segments | int | Count included |
| profitable_oos_segments | int | For proportion_of_profitable_oos_segments (FR-047) |
| oos_consistency_score | float | CV or other dispersion metric |
| aggregate_oos_return | float | Weighted / simple aggregation |
| aggregate_oos_sharpe | float | Aggregated risk-adjusted metric |
| robustness_score | float | Composite score derived from permutation p_value & oos metrics |
| extreme_tail_ratio | float | From permutation (FR-043) |

### RunManifest
| Field | Type | Notes |
| run_id | str | External id |
| run_hash | str | Deterministic hash over config & dataset (FR-015/016) |
| config_hash | str | Hash of canonical RunConfig serialization |
| dataset_hash | str | Mirror of dataset.data_hash |
| calendar_id | str | Calendar (FR-002) |
| float_precision | int | 8 (FR-041) |
| seeds | dict | {base_seed, permutation_seeds[]} |
| created_at | datetime | ISO8601 |
| artifacts | list[ArtifactDescriptor] | Name, path, sha256, size |
| chain_prev | str? | Prior manifest id (FR-035) |
| api_version | str | Package version (FR-031) |
| feature_registry_version | str | Registry version snapshot |
| idempotency_key | str? | If provided (FR-016) |

### ArtifactDescriptor
| Field | Type | Notes |
| name | str | Logical name e.g., equity.parquet |
| path | str | Relative path |
| sha256 | str | Content hash |
| size | int | Bytes |

### SummarySnapshot (SSE/Event)
| Field | Type | Notes |
| run_id | str | |
| phase | enum | Current phase (FR-026) |
| progress_pct | float | Approx progress |
| trades | int | Count so far |
| p_value | float? | When available |
| final_equity | float? | On completion |
| anomalies | dict? | Optional subset (FR-036) |

### CausalityViolationMetric
| Field | Type | Notes |
| violations_count | int | EXPECT 0 (FR-006) |

## Relationships
- RunConfig 1:1 RunManifest (manifest created after run hash stable)
- RunManifest 1:* ArtifactDescriptor
- RunConfig 1:* Trade (via execution process) → EquityBar (derived)
- RunConfig 1:1 ValidationResult (permutation) when trials>0
- SummarySnapshot aggregates metrics + anomalies derived from Trades, EquityBars, ValidationResult
- WalkForwardSegment * trains per segment → contributes to WalkForwardAggregate (if walk-forward enabled)
- ValidationResult + WalkForwardAggregate feed robustness_score computation

## State Transitions (Run Phases)
NEW → data_validation → feature_build → signals → execution → metrics → permutation_test (optional) → finalize(success|failure)
If walk-forward enabled: metrics phase encompasses per-segment optimization loops before aggregate computation.

## Hashing Inputs
config_hash includes: serialized RunConfig (deterministic JSON) excluding volatile runtime fields; run_hash combines config_hash + dataset_hash + feature_registry_version + float_precision.

## Determinism Guarantees
- Float representation locked (precision=8)
- Seeds enumerated
- Distribution ordering explicit
- Plot style fixed; figure checksum test

## Validation Rules Summary
- DatasetSnapshot: duplicates must be 0; if >0 after normalization -> ERROR
- FeatureSpec: shift_applied True only if causality_shift True
- CostModelConfig: spread_pct XOR participation_rate (mutual exclusivity)
- ValidationConfig: permutation_trials >=0; if 0 -> placeholders
- Trade: qty % lot_size == 0
- RunManifest: artifact list fully hashed; missing hash => invalid
- WalkForwardSegment: non-overlapping (except optional warm-up) sequential boundaries; assert train_end < test_start

## Open Extensions (Future)
- MultiAssetRunConfig (list of symbols)
- AdvancedExecution (partial fills, impact models)
- AdditionalValidation (walk-forward, block bootstrap)
- BootstrapResampling (future FR-049 adaptive)
- MonteCarloPathPerturbation
- RegimeStressTesting
- StrategyMetaValidation (portfolio-level aggregation)
