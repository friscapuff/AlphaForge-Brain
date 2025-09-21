# Research: NVDA 5-Year Dataset Integration

## Objective
Understand the characteristics, potential anomalies, and normalization requirements for integrating a static 5-year NVDA historical dataset (daily or intraday bars assumed daily unless specified) into the AlphaForge Brain pipeline with deterministic, reproducible ingestion.

## Source Assumptions
- Input file: `NVDA_5y.csv` placed under configured `data_dir` (e.g. `./data/NVDA_5y.csv`).
- Format: CSV with header row. Columns expected: `timestamp`, `open`, `high`, `low`, `close`, `volume` (optionally `adj_close`).
- Timestamp granularity: Daily close (assumption). If intraday discovered, timeframe classification logic must adapt but spec currently targets daily.
- Timezone: Potentially US/Eastern (exchange local) or already UTC. We will normalize to UTC.
- Exchange: NASDAQ (use official trading calendar including holidays + early closes). Library implementation detail deferred; require calendar abstraction at planning.

## Data Quality & Anomalies
| Anomaly Type | Description | Handling Policy | Rationale |
|--------------|-------------|-----------------|-----------|
| Duplicate timestamps | Same timestamp appears more than once | Keep first, drop subsequent | Determinism, avoids synthetic merging |
| Out-of-order rows | Timestamps not strictly ascending | Sort ascending; record event | Maintain continuity & reproducibility |
| Missing core fields | Null/NaN in o/h/l/c/volume | Drop row; increment anomaly counters | Avoid hidden imputation risk |
| Zero volume row | Volume = 0 but prices present | Retain with flag | Preserves liquidity signal |
| Future-dated row | Timestamp beyond max expected range | Drop & log | Dataset integrity |
| Outside 5y lower bound | Too old relative to window start parameter | Still ingested then filtered by slicing | Allows flexible sub-ranges |
| Partial final session | Last day truncated | Accept; possible indicator warm-up adjustments | Avoid over-engineering |
| Entire day gap (holiday) | Calendar-expected closure | Not anomaly | Real market closure |
| Unexpected missing day | Non-holiday gap | Record anomaly (missing_period) | Transparency |

## Normalization Steps (Conceptual)
1. Load raw CSV with explicit dtype coercion.
2. Coerce timestamp to timezone-aware; interpret source timezone if needed; convert to UTC.
3. Sort by timestamp.
4. Drop exact duplicate timestamp rows after first occurrence.
5. Validate strictly increasing timestamps.
6. Remove rows with null critical fields.
7. Flag zero-volume rows; retain.
8. Filter date range (start/end) lazily for run requests (do not mutate cached canonical dataset).
9. Calendar gap classification: produce lists of expected closures vs unexpected gaps.
10. Hash canonical dataset (post-cleaning, full 5y) to produce `data_hash`.

## Reproducibility Considerations
- Hash function: SHA256 of normalized parquet/CSV bytes (canonical serialization) or DataFrame JSON with stable formatting.
- `data_hash` included in run config canonical hash -> stable run identity.
- Maintain a dataset registry keyed by symbol pointing to loader + metadata (row counts, hash, calendar id).
- Deterministic ordering and filtering ensures repeatable feature & strategy calculations.

## Performance Considerations
- 5-year daily dataset is small (<10K rows) ⇒ negligible load cost; ensure pipeline overhead dominates.
- If intraday future extension added, consider lazy memory mapping & on-demand slice extraction.

## Exchange Calendar
- Calendar object resolves trading sessions, holidays, early closes.
- Provide functions: `is_trading_day(date)`, `next_trading_day(date)`, `classify_gap(previous_ts, current_ts)`.
- Calendar id (e.g. `XNYS` or `NASDAQ`) recorded in manifest for contextual reproducibility.

## Feature / Indicator Interaction
- Indicators must receive clean, strictly ascending timestamp series.
- Warm-up rows (window-1) not treated as anomalies.
- Zero-volume flags optionally passed to strategy/execution for liquidity-aware decisions (future).

## Validation Output Design
- Counts: duplicates_dropped, rows_dropped_missing_fields, zero_volume_rows, unexpected_gaps, future_rows_dropped.
- Sample arrays (limited) of example timestamps for each anomaly category.
- Structured JSON stored as `validation.json` artifact and embedded summary subset in run detail.

## Open Questions (Resolved Already in Spec)
None outstanding; all earlier ambiguities resolved.

## Deferred Items
- Multi-asset loader generalization.
- Real-time incremental update pipeline.
- Corporate action adjustment enrichment beyond provided CSV.

## Benchmark Notes
- Record initial end-to-end run wall-clock and ingestion duration in benchmark logs for FR-019 documentation.

## Risks
| Risk | Impact | Mitigation |
|------|--------|------------|
| Timezone misinterpretation | Indicator misalignment | Force explicit source timezone assumption, convert to UTC, add test |
| Silent duplicate retention | Distorted metrics | Deterministic drop & counter |
| Hidden imputation | Compromised realism | Strict exclusion policy |
| Calendar misclassification | Incorrect anomaly counts | Use vetted calendar abstraction + tests |

## Summary
A deterministic, transparent ingestion + validation layer for NVDA forms a reproducible foundation for strategy experimentation, consistent with constitutional principles (determinism, realism-lite, extensibility).