# Data Model: AlphaForge Brain Canonical Schema

Version: 0.1 (initial design)

## Tables

### runs
- run_hash (PK)
- config_hash
- dataset_digest
- seed_root
- created_at (ts)
- status (enum)
- manifest_json
- latency_model (text)
- feature_timestamping (text)
- gap_policy (text)
- retention_state (enum: full, manifest-only, evicted, pinned, top_k)
- pinned (bool)
- pinned_by (text)
- pinned_at (ts)
- primary_metric_name (text)
- primary_metric_value (real)
- rank_within_strategy (int)

Indices: (config_hash), (dataset_digest), (primary_metric_value DESC), (created_at DESC)

### trades
- id (PK)
- run_hash (FK → runs.run_hash)
- ts (int64 ns)
- side (enum: buy/sell)
- qty (real)
- fill_price (real)
- fees (real)
- slippage (real)
- pnl (real)
- position_after (real)
- bar_index (int)
- content_hash (text)

Indices: (run_hash), (ts), (bar_index)

### equity
- id (PK)
- run_hash (FK)
- ts (int64 ns)
- equity (real)
- drawdown (real)
- realized_pnl (real)
- unrealized_pnl (real)
- content_hash (text)

Indices: (run_hash), (ts)

### features
- id (PK)
- run_hash (FK)
- spec_hash (text)
- rows (int)
- cols (int)
- digest (text)
- build_policy (json: chunk_size, overlap)
- cache_link (text)

Indices: (run_hash), (spec_hash)

### validation
- id (PK)
- run_hash (FK)
- method (enum: bootstrap, permutation, walk_forward)
- params_json (json)
- results_json (json)
- ci_width (real)
- p_value (real)
- content_hash (text)

Indices: (run_hash), (method)

### audit_log
- id (PK)
- event_type (enum: pin, unpin, evict, rehydrate)
- run_hash (FK)
- actor (text)
- ts (timestamp)
- details_json (json)

Indices: (run_hash), (event_type), (ts DESC)

## Migrations
- Alembic versioned scripts; head checksum enforced in CI.

## Notes
- All JSON stored with sorted keys for canonical hashing.
- Time stored as int64 ns.
- Numeric column dtypes align with Constitution constraints.
