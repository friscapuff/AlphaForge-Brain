# Data Model (Phase 1 Draft)

**Feature**: AlphaForge Brain Refinement
**Spec**: ./spec.md
**Research**: ./research.md
**Status**: Skeleton (Pending Phase 0 completion)

---
## Design Principles
- Deterministic reproducibility: all persisted rows contain or can derive a run_hash.
- Minimal redundant storage: features cached once per canonical key.
- Memory diet: float32 for numeric feature columns; int64 for timestamps & volume.
- Explicit schema versioning: migrations gated; schema_version recorded.
- No MultiIndex: single-symbol monotonic timestamp index for all time series tables.

---
## Entity Overview
| Entity | Purpose | Persistence | Notes |
|--------|---------|-------------|-------|
| Run | Captures configuration & lifecycle status | SQLite `runs` | Source of truth manifest + seeds |
| Trade | Execution events & position transitions | SQLite `trades` | Ordered by timestamp |
| Equity | Equity curve & drawdown metrics | SQLite `equity` | One row per bar |
| Validation | Statistical outputs (permutation, bootstrap, walk-forward) | SQLite `validation` | Stores CIs + method metadata |
| Metrics | Key-value numeric/string metrics per phase | SQLite `metrics` | Phase attribution |
| FeaturesCacheMeta | Metadata about cached feature parquet artifacts | SQLite `features_cache` | Dedup keys & reproducibility |
| RunError | Captured exception records | SQLite `run_errors` | Enables post-mortem |
| PhaseMetric | Timing + progress instrumentation | SQLite `phase_metrics` | Observability |

---
## Detailed Schemas
### Run
| Field | Type | Constraints | Description |
|-------|------|------------|-------------|
| run_hash | TEXT PK | not null | Deterministic hash of config + seed derivation |
| created_at | INTEGER | epoch ms | Creation timestamp |
| updated_at | INTEGER | epoch ms | Updated per status change |
| status | TEXT | enum(pending,running,failed,completed) | Lifecycle state |
| config_json | TEXT | canonical JSON | Original run configuration |
| manifest_json | TEXT | canonical JSON | Augmented manifest (provenance fields) |
| data_hash | TEXT | sha256 | Hash of input dataset (after dtype normalization) |
| seed_root | INTEGER | uint32 | Derived master seed |
| db_version | INTEGER | schema version | Matches migration head |
| bootstrap_seed | INTEGER | uint32 | Seed for bootstrap trials |
| walk_forward_spec_json | TEXT | nullable | JSON spec if walk-forward enabled |

### Trade
| Field | Type | Constraints | Description |
|-------|------|------------|-------------|
| run_hash | TEXT FK(runs.run_hash) | not null | Parent run |
| ts | INTEGER | epoch ns | Bar timestamp |
| side | TEXT | enum(buy,sell,flat) | Action direction |
| qty | REAL | float32 | Quantity (signed) |
| entry_price | REAL | float32 | Fill entry price |
| exit_price | REAL | float32 | Fill exit price (if closed) |
| cost_bps | REAL | float32 | Transaction cost basis points |
| borrow_cost | REAL | float32 | Funding/borrow cost allocated |
| pnl | REAL | float32 | Realized PnL for trade |
| position_after | REAL | float32 | Position after execution |

Indexes: (run_hash, ts)

### Equity
| Field | Type | Constraints | Description |
|-------|------|------------|-------------|
| run_hash | TEXT FK | not null | Parent run |
| ts | INTEGER | epoch ns | Bar timestamp |
| equity | REAL | float32 | Equity value |
| drawdown | REAL | float32 | Current drawdown fraction/amount |
| realized_pnl | REAL | float32 | Accumulated realized PnL |
| unrealized_pnl | REAL | float32 | Mark-to-market unrealized PnL |
| cost_drag | REAL | float32 | Aggregated cost impact |

Indexes: (run_hash, ts)

### Validation
| Field | Type | Constraints | Description |
|-------|------|------------|-------------|
| run_hash | TEXT FK | not null | Parent run |
| payload_json | TEXT | canonical JSON | Extended stats payload (walk-forward summary, distribution samples hash) |
| permutation_pvalue | REAL | float32 | Permutation test p-value |
| bootstrap_sharpe_low | REAL | float32 | Sharpe CI lower |
| bootstrap_sharpe_high | REAL | float32 | Sharpe CI upper |
| bootstrap_cagr_low | REAL | float32 | CAGR CI lower |
| bootstrap_cagr_high | REAL | float32 | CAGR CI upper |
| bootstrap_method | TEXT | enum(hadj_bb,simple) | Selected method |
| bootstrap_block_length | INTEGER | nullable | Block length used (if method == hadj_bb) |
| bootstrap_jitter | INTEGER | nullable | Jitter parameter (default 1) |
| bootstrap_fallback | INTEGER | 0/1 | Flag (1 == fallback to simple) |

### Metrics
| Field | Type | Constraints | Description |
|-------|------|------------|-------------|
| run_hash | TEXT FK | not null | Parent run |
| key | TEXT | not null | Metric key |
| value | TEXT | not null | Stored as text; numeric parse in consumer |
| value_type | TEXT | enum(int,float,str,json) | Type hint |
| phase | TEXT | nullable | Phase source |

Composite PK suggestion: (run_hash,key,phase) optional; else index (run_hash,key)

### FeaturesCacheMeta
| Field | Type | Constraints | Description |
|-------|------|------------|-------------|
| meta_hash | TEXT PK | not null | Hash of canonical spec object |
| spec_json | TEXT | canonical JSON | Key components (dataset_hash, indicator, version, params, seed_root, code_version) |
| built_at | INTEGER | epoch ms | Build timestamp |
| rows | INTEGER | count | Row count |
| columns | INTEGER | count | Column count |
| digest | TEXT | sha256 | Digest of parquet content (post-write) |

### RunError
| Field | Type | Constraints | Description |
|-------|------|------------|-------------|
| id | INTEGER PK | autoincrement | Identity |
| run_hash | TEXT FK | not null | Parent run |
| ts | INTEGER | epoch ms | Error capture time |
| phase | TEXT | nullable | Phase identifier |
| error_code | TEXT | short code | Stable classification |
| message | TEXT | truncated | Message excerpt |
| stack_hash | TEXT | sha256 | Hash of stack trace string |

### PhaseMetric
| Field | Type | Constraints | Description |
|-------|------|------------|-------------|
| id | INTEGER PK | autoincrement | Identity |
| run_hash | TEXT FK | not null | Parent run |
| phase | TEXT | not null | Phase name/simple slug |
| started_at | INTEGER | epoch ms | Start time |
| ended_at | INTEGER | epoch ms | End time |
| duration_ms | INTEGER | computed | ended - started |
| rows_processed | INTEGER | nullable | Throughput indicator |
| extra_json | TEXT | canonical JSON | Additional structured stats |

---
## Derived / Computed Fields
- `duration_ms` (PhaseMetric) computed at finalize.
- Rolling stats for bootstrap not persisted raw; only CI endpoints + method metadata (payload_json may contain distribution digest/hash to avoid heavy duplication).

---
## Relationships
- Run 1:N Trade, Equity, Metrics, Validation(1:1 logically), RunError, PhaseMetric
- FeaturesCacheMeta independent; referenced from feature build process and manifest (link by digest or meta_hash)

---
## Feature Cache Key Specification (Draft)
Canonical object:
```
{
  "dataset_hash": <sha256 str>,
  "indicator": <str>,
  "version": <semver>,
  "params": {<sorted key:value pairs>},
  "seed_root": <int>,
  "code_version": <git short sha>
}
```
- Serialize with sorted keys; UTF-8; no whitespace tailoring beyond json.dumps(sort_keys=True,separators=(',',':')).
- meta_hash = sha256(serialized).

---
## Indexing & Performance Notes
- Ensure PRAGMA synchronous=NORMAL and WAL mode for sustained bulk inserts.
- Create composite indexes only where query patterns justify (run_hash, ts) heavy scan reduction.

---
## Data Integrity & Validation Rules
| Rule | Enforcement |
|------|------------|
| Monotonic timestamp in Trade/Equity | Assertion in ingestion & pre-insert sort |
| Float32 enforcement for OHLC, features | Downcast step with assert no overflow/NaN inflation |
| No chained indexing / implicit copy | Lint rule + code review; optional runtime guard in dev mode |
| Consistent dataset_hash across run tables | Compare on finalize against manifest |
| Bootstrap metadata coherence | If method==simple then block_length & jitter NULL, fallback flag allowed |

---
## Open TBD (Should Clear During Phase 0)
- Whether to store distribution sample hashes per metric (vs single payload digest)
- Potential secondary index on metrics (run_hash, phase)

---
Generated: 2025-09-23
