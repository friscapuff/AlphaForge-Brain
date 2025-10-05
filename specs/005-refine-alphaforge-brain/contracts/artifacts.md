# Artifact Schemas v0.1

## Run Manifest
- run_hash, config_hash, dataset_digest, seed_root, created_at
- latency_model, feature_timestamping, gap_policy
- artifact_index: name, type, path, content_hash, bytes, retention_state

## Trades
- Columns: ts, side, qty, fill_price, fees, slippage, pnl, position_after, indices, content_hash
- Notes: fees/slippage applied both sides; ts aligns with next-bar open fills

## Equity
- Columns: ts, equity, drawdown, realized_pnl, unrealized_pnl, content_hash

## Features
- Spec: spec_hash, rows, cols, digest, build_policy (chunk_size, overlap), cache linkage

## Validation
- Method-specific blocks
  - Bootstrap: trials, block_length, jitter, ci_width, seed
  - Permutation: trials, p_value, seed
  - Walk-forward: splits, metrics

## Dataset & Policies
- adjustment_policy = full-adjusted; adjustment_factors_digest, adjusted_digest

## Retention
- retention_state: full | manifest-only | evicted | pinned | top_k
- pin metadata: pinned_by, pinned_at, reason
