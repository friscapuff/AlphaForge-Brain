# Quickstart: AlphaForge Brain Hello-Run

## Prereqs
- Python 3.11
- Install project deps (poetry or pip)

## Hello-Run Flow
1. Submit a run via API or CLI with a minimal config and dataset reference.
2. Stream SSE events to observe deterministic progress (phases, timings).
3. Fetch artifacts and verify content hashes; rerun to confirm determinism.

## Contracts to Know
- Next-bar open fills; features at bar-close with shift(1)
- Fully adjusted prices at ingest
- CI memory cap: 1.5 GB; local warn 2.0 GB, soft fail 3.0 GB
- Retention: last 50 full, top 5 per strategy full, manual pin; others manifest-only with rehydrate

## Example Minimal Config (pseudo)
{
  "strategy": "ref-strat-001",
  "features": ["sma_20", "sma_50"],
  "fees": {"bps": 1},
  "slippage": {"bps": 2},
  "latency_model": "next_bar_open",
  "feature_timestamping": "bar_close_shift1"
}

## Verification Steps
- Run twice → run_hash, artifact hashes, and SQLite digests match
- Validate bootstrap/permutation/walk-forward pass with CI defaults
- Confirm retention endpoints: pin/unpin; simulate eviction (non-destructive in CI)
