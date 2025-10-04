# Data Model & Persistence (Project A Backend v1)

This document specifies core entities, their schemas, relationships, and physical storage strategy for the single-user engine.

## Storage Technologies
- SQLite (single file `studio.db`) for metadata: runs, presets, manifests index, cached object registry.
- Filesystem (./data, ./runs, ./cache) for large columnar/series artifacts (Parquet + optional CSV) and plots.
- Hashing: SHA-256 hex lowercase for config/data/feature cache keys.

Directory Layout (proposed):
```
./studio.db
./runs/{run_id}/summary.json
./runs/{run_id}/metrics.json
./runs/{run_id}/equity.parquet
./runs/{run_id}/drawdown.parquet
./runs/{run_id}/trades.parquet
./runs/{run_id}/validation_summary.json (optional)
./runs/{run_id}/plots.png (optional)
./runs/{run_id}/manifest.json
./cache/candles/{provider}/{symbol}/{timeframe}/{hash}.parquet
./cache/features/{indicator_name}/{indicator_hash}.parquet
./presets/{name}.json
```

## Core Entities & Schemas
Notation:
Type primitives: STRING, INT, BIGINT, FLOAT, DOUBLE, BOOL, JSON, BLOB, TIMESTAMP(ms UTC stored as BIGINT).

### 1. Run
Represents a single backtest (with or without validation). Stored in SQLite table `runs`.
Schema (`runs`):
| field | type | notes |
|-------|------|-------|
| run_id | STRING (UUID v4) | Primary Key |
| hash | STRING | 64-char config hash (sha256) |
| status | STRING | queued|running|completed|failed|cancelled |
| stage | STRING | nullable current stage (data_loading, metrics...) |
| created_at | BIGINT | epoch ms |
| updated_at | BIGINT | epoch ms |
| started_at | BIGINT | nullable |
| completed_at | BIGINT | nullable |
| error_code | STRING | nullable |
| error_message | STRING | nullable |
| config_json | JSON | canonical frozen config snapshot |
| seed | INT | base RNG seed |
| metrics_summary_json | JSON | subset metrics for quick listing |
| artifacts_manifest_sha | STRING | reference to manifest file hash |

Indexes: (hash), (status), (created_at DESC).

### 2. RunConfig (embedded JSON)
JSON stored within `runs.config_json`:
```
{
	symbol: STRING,
	timeframe: STRING,        // e.g., '1h'
	start: BIGINT,            // inclusive epoch ms
	end: BIGINT,              // inclusive epoch ms
	provider: STRING,
	indicators: [ { name: STRING, params: {..} } ],
	strategy: { name: STRING, params: { fast: INT, slow: INT, ... } },
	risk: { name: STRING, params: { fraction: FLOAT } },
	execution: { commission_per_share?: FLOAT, slippage_bps?: FLOAT, borrow_bps?: FLOAT },
	validation: { permutation?: { n: INT }, block_bootstrap?: { n: INT, block_size: INT }, monte_carlo?: { n: INT }, wfo?: { windows?: INT } },
	seed: INT,
	preset_ref?: STRING
}
```

### 3. Preset
Saved configuration template.
Table `presets`:
| field | type | notes |
| name | STRING | primary key |
| created_at | BIGINT | |
| updated_at | BIGINT | |
| config_json | JSON | same shape as RunConfig (minus preset_ref) |

Also persisted as JSON file for portability.

### 4. Candle Cache Metadata
Table `candle_cache` (metadata only; data stored as Parquet):
| field | type | notes |
| candle_hash | STRING | primary key (sha256 of provider+symbol+timeframe+range+raw_version) |
| provider | STRING | |
| symbol | STRING | |
| timeframe | STRING | |
| start | BIGINT | |
| end | BIGINT | |
| row_count | INT | |
| created_at | BIGINT | |
| path | STRING | relative path to Parquet |

Candle Parquet Schema:
| column | type | notes |
| ts_utc | BIGINT | epoch ms (sorted) |
| open | DOUBLE | |
| high | DOUBLE | |
| low | DOUBLE | |
| close | DOUBLE | |
| volume | DOUBLE | |
| vwap? | DOUBLE | optional |
| gap_flag | BOOL | true if temporal gap from previous bar > expected interval * 1.5 |

### 5. Indicator Cache Metadata
Table `feature_cache`:
| field | type | notes |
| feature_hash | STRING | primary key (sha256 of indicator name+params+candle_hash+code_version) |
| name | STRING | indicator name |
| params_json | JSON | |
| candle_hash | STRING | FK -> candle_cache.candle_hash |
| row_count | INT | |
| created_at | BIGINT | |
| path | STRING | relative path |

Feature Parquet Schema (example):
| ts_utc | BIGINT |
| {feature_column(s)} | DOUBLE | shifted +1 bar already |
| raw_{feature_column(s)} | DOUBLE | (optional) unshifted for debugging (not exposed to strategy) |

### 6. Trades (Artifact)
Written per run: `trades.parquet`.
Schema:
| ts_utc | BIGINT |
| side | STRING | 'buy'|'sell'|
| qty | DOUBLE |
| price | DOUBLE |
| fee | DOUBLE |
| slippage | DOUBLE |
| pnl_realized | DOUBLE |
| borrow_cost | DOUBLE |

### 7. Portfolio Bars (Intermediate / Derived)
Possible optional artifact later; equity + drawdown derived.
Schema:
| ts_utc | BIGINT |
| position_qty | DOUBLE |
| price_ref | DOUBLE |
| market_value | DOUBLE |
| cash | DOUBLE |
| equity | DOUBLE |
| fees_cum | DOUBLE |
| pnl_unrealized | DOUBLE |

### 8. Equity & Drawdown Series
`equity.parquet` Schema:
| ts_utc | BIGINT |
| equity | DOUBLE |

`drawdown.parquet` Schema:
| ts_utc | BIGINT |
| drawdown | DOUBLE | (equity/peak - 1)

### 9. Metrics Summary
`metrics.json` example:
```
{
	total_return: FLOAT,
	cagr: FLOAT?,
	volatility: FLOAT,
	sharpe: FLOAT,
	sortino: FLOAT,
	max_drawdown: FLOAT,
	avg_drawdown: FLOAT,
	max_drawdown_duration_bars: INT,
	trade_count: INT,
	win_rate: FLOAT,
	payoff_ratio: FLOAT,
	turnover: FLOAT,
	exposure_pct: FLOAT,
	start_ts: BIGINT,
	end_ts: BIGINT
}
```

### 10. Validation Outputs
`validation_summary.json` structure (fields optional depending on enabled tests):
```
{
	permutation: { n: INT, p_value: FLOAT, mean_return: FLOAT, distribution_summary: { p5: FLOAT, p50: FLOAT, p95: FLOAT } },
	block_bootstrap: { n: INT, block_size: INT, return_ci: { lower: FLOAT, upper: FLOAT } },
	monte_carlo: { n: INT, equity_p5: FLOAT, equity_p95: FLOAT },
	wfo: { windows: INT, segments: [ { in_sample_start: BIGINT, in_sample_end: BIGINT, out_sample_start: BIGINT, out_sample_end: BIGINT, return: FLOAT } ] }
}
```

### 11. Artifact Manifest
`manifest.json` OR referenced hash in DB.
```
{
	run_id: STRING,
	created_at: BIGINT,
	config_hash: STRING,
	files: [
		{ name: "summary.json", path: "summary.json", sha256: STRING, size: INT, mime: "application/json" },
		{ name: "metrics.json", path: "metrics.json", sha256: STRING, size: INT, mime: "application/json" },
		{ name: "equity.parquet", path: "equity.parquet", sha256: STRING, size: INT, mime: "application/vnd.apache.parquet" },
		{ name: "drawdown.parquet", path: "drawdown.parquet", sha256: STRING, size: INT, mime: "application/vnd.apache.parquet" },
		{ name: "trades.parquet", path: "trades.parquet", sha256: STRING, size: INT, mime: "application/vnd.apache.parquet" }
		// optional: validation_summary.json, plots.png
	]
}
```

### 12. Event Stream (Not Persisted Fully)
Only final metrics summary + manifest are persisted; events are ephemeral except maybe last known progress. Table `run_progress` (optional) to resume SSE:
| run_id | STRING | PK |
| last_seq | INT | |
| last_stage | STRING | |
| progress_ratio | FLOAT | |
| updated_at | BIGINT | |

### 13. Retention Tracking
Simplest approach: Query completed runs ordered by completed_at DESC; if count > 100 remove oldest (delete directory + DB row). Optionally table `retention_state` for bookkeeping.

## Hashing Strategy
config_hash = sha256( canonical_json( RunConfig minus seed? (include seed for reproducibility) + code_version ) ).
candle_hash = sha256(provider + '|' + symbol + '|' + timeframe + '|' + start + '|' + end + '|' + raw_source_version).
feature_hash = sha256(indicator_name + '|' + sorted_params + '|' + candle_hash + '|' + code_version).
run_hash (idempotency) = sha256(config_hash).

## Concurrency Considerations
Single-user: minimal contention. Use SQLite WAL mode. Acquire file locks when writing artifact manifest to avoid partial writes.

## Data Integrity
- After writing each artifact, compute sha256 streaming; update manifest.
- At run completion, finalize manifest then update runs.artifacts_manifest_sha.
- Optionally verification endpoint recalculates hash for integrity check.

## Future Extensions (Not v1)
- Multi-symbol correlation matrices.
- Compressed zstd Parquet writer settings.
- External object storage (S3) backend adapter.
- Incremental candles append service.
