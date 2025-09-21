# Data Model: NVDA Dataset Integration

## Overview
This document defines conceptual and logical entities required to ingest, normalize, validate, and utilize a canonical 5-year NVDA dataset within the AlphaForge Brain pipeline.

## Entity Inventory
1. Dataset
2. RawBar (transient)
3. Candle (canonical normalized bar)
4. DatasetMetadata
5. AnomalyEvent
6. ValidationSummary
7. FeatureDefinition
8. FeatureOutput
9. StrategyConfig
10. RiskConfig
11. ExecutionConfig
12. RunConfig (extended)
13. RunManifest
14. Trade / Fill / Position
15. MetricsSummary / MetricsDetail
16. ValidationArtifact

## 1. Dataset
Represents a symbol-specific historical timeseries loaded and cleaned once per content hash.
- symbol: string (e.g., "NVDA")
- timeframe: string (e.g., "1d")
- rows_raw: int
- rows_canonical: int
- data_hash: string (sha256 of canonical serialized form)
- calendar_id: string (e.g., "NASDAQ")
- first_ts: int (epoch ms UTC)
- last_ts: int (epoch ms UTC)
- zero_volume_rows: int
- duplicates_dropped: int
- rows_dropped_missing: int
- future_rows_dropped: int
- unexpected_gap_count: int

## 2. RawBar (Transient)
Used only during ingestion before normalization.
- timestamp: string/int (raw)
- open/high/low/close: float | null
- volume: int | null
- adj_close: float | null (optional)

## 3. Candle
Normalized immutable record.
- ts: int (epoch ms UTC)
- o, h, l, c: float
- v: int
- flags: object { zero_volume?: bool }

## 4. DatasetMetadata
Cached snapshot enabling quick reuse.
- symbol
- timeframe
- data_hash
- calendar_id
- row_count
- anomaly_counters: map<string,int>
- created_at: int (epoch ms)

## 5. AnomalyEvent
Describes one anomaly category.
- type: enum [duplicate_timestamp, missing_field, zero_volume, future_row, unexpected_gap]
- count: int
- sample: array<int epoch ms> (limited, e.g., up to 5)
- resolution: enum [dropped, retained_flagged, sorted]

## 6. ValidationSummary
- symbol
- data_hash
- summary_counters: map<string,int>
- events: array<AnomalyEvent>
- expected_closures: int
- unexpected_gaps: int
- generated_at: int

## 7. FeatureDefinition
- name: string
- params_schema: JSON Schema (for UI form generation)
- window: int (if applicable)
- shift: int (>=1 for causal enforcement)

## 8. FeatureOutput
- name
- columns: array<string>
- data: DataFrame-like (opaque in docs; serialized artifact) or in-memory pointer
- metadata: { window, shift }

## 9. StrategyConfig
- name: string (e.g., dual_sma)
- params: map<string, any>

## 10. RiskConfig
- model: enum [fixed_fraction, volatility_target, kelly_fraction]
- params: map<string, any>

## 11. ExecutionConfig
- commission_per_share: float
- slippage_bps: float
- borrow_bps: float
- fill_price: enum [open_next, mid_next, vwap_next]
- slippage_model: { model: enum [spread_pct, participation_rate], params: map<string, any> }

## 12. RunConfig (Extended for NVDA Usage)
Adds dataset linkage & slicing.
- symbol
- timeframe
- start: int epoch ms (inclusive)
- end: int epoch ms (exclusive)
- provider: string
- indicators: array<{ name, params }>
- strategy: StrategyConfig
- risk: RiskConfig
- execution: ExecutionConfig
- validation: object
- seed: int
- preset_ref?: string
- data_hash (resolved during ingestion, not user-supplied)

## 13. RunManifest
Links configuration, dataset, and artifacts.
- run_id (hash)
- config_hash
- data_hash
- calendar_id
- created_at
- chain_prev
- manifest_hash
- files: array<{ name, path, sha256, size, mime? }>

## 14. Trade / Fill / Position
Simplified domain objects.
### Trade
- trade_id
- symbol
- direction: enum [LONG, SHORT]
- entry_ts
- exit_ts
- entry_price
- exit_price
- size
- pnl
- return_pct

### Fill
- fill_id
- trade_id
- ts
- price
- size
- commission
- slippage_cost
- borrow_cost

### Position
- symbol
- size
- avg_entry_price
- unrealized_pnl

## 15. MetricsSummary / Detail
### MetricsSummary
- total_return
- sharpe
- sortino
- max_drawdown
- trade_count
- win_rate
- exposure_pct
- turnover

### MetricsDetail (artifact)
- equity_curve: series
- drawdowns: series
- returns: series
- exposure_series: series
- trade_pnls: series

## 16. ValidationArtifact
Serialized JSON file capturing ValidationSummary + additional context.
- file: validation.json
- includes anomaly counters, events, calendar classification results.

## Relationships
- Dataset 1:N Candle
- Dataset 1:1 ValidationSummary
- RunConfig 1:1 RunManifest
- RunManifest references dataset (data_hash) and calendar
- Run produces artifacts (files array)
- FeatureDefinition reused across runs; FeatureOutput ephemeral per run
- Trade aggregates multiple Fill records

## Integrity & Determinism
- data_hash is part of config hashing pipeline -> stable run_id
- manifest_hash includes file metadata -> ensures artifact integrity
- No mutation of canonical Dataset after initial load (cached, read-only)

## Extensibility Notes
- Multi-asset: symbol becomes composite key; add portfolio entity later
- Additional anomaly types can extend AnomalyEvent.type enum
- Additional risk/slippage models expand enums with backward compatibility

## Non-Functional Alignment
- Determinism: enforced via hashing & immutable canonical dataset
- Transparency: anomaly events & counters exposed
- Extensibility: registries for features, risk models, slippage adapters

## OpenAPI Impact (Preview)
- RunDetail / Manifest enriched with data_hash & calendar_id
- Validation summary accessible via run detail or artifact download

## Out of Scope
- Corporate action adjustment beyond provided data
- Real-time incremental ingestion

