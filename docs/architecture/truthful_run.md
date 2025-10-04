# Truthful Run Architecture (T073)

This document summarizes the deterministic "truthful run" pipeline — the contract guaranteeing that any backtest result can be independently reproduced and audited.

## Goals
- Deterministic replay (same config + dataset snapshot -> identical run_hash & artifact hashes)
- Explicit provenance & anomaly surfacing (no silent data massaging)
- Additive evolution (public schemas only change via additive fields)
- Separation of concerns (strategy intent vs risk sizing vs execution vs validation)

## Phase Diagram
```
Config -> Hash (idempotent) -> Orchestrator
  |
  v
Data Load -> Feature Build -> Strategy -> Risk -> Execution -> Metrics -> Validation -> Artifacts -> Manifest (hashed + chain_prev)
                                              ^                                    |
                                              |                                    v
                                          Event Buffer  <---------------------  Snapshot (summary)
```

## Determinism Anchors
| Anchor | Mechanism | Failure Signal |
|--------|-----------|----------------|
| Config Hash | Canonical JSON (sorted keys, normalized types) | Hash drift on replay |
| Dataset Snapshot | Content hash + symbol/timeframe binding | Different `data_hash` in manifest |
| Time | `datetime.now(timezone.utc)` + `freeze_time` in tests | Timestamp mismatch in tests |
| Randomness | Base seed + indexed sub-seeds per module | Non-reproducible permutation p-values |
| Manifest Integrity | `manifest_hash` + `chain_prev` | Chain break detection |

## Validation Layers
1. Permutation: Structural shuffle preserving gaps -> null distribution of metrics.
2. Walk-Forward: Rolling OOS segments -> stability & generalization.
3. Robustness Score: Composite of statistical evidence & OOS consistency.
4. (Planned) Bootstrap / Monte Carlo: Sampling & distributional stress tests.

## Artifact Set
| File | Purpose |
|------|---------|
| `manifest.json` | Index & integrity metadata (sizes, hashes, chain link) |
| `metrics.json` | Aggregate performance metrics |
| `validation.json` | Statistical outputs (permutation distribution, p_value, robustness_score, etc.) |
| `equity.parquet` | Equity curve (timestamped) |
| `trades.parquet` | Executed trades with fills & fees |
| `plots.png` | Deterministic equity curve visualization |

## Event Model
Ordered in-memory buffer emits deterministic sequence: `started -> data_loaded -> features_ready -> strategy_done -> risk_done -> execution_done -> metrics_done -> validation_done -> artifacts_finalized -> completed` plus heartbeats (streaming) and snapshot summary events.

## Extension Guidelines
- New validation methods: accept explicit `seed`, append fields to `validation.json` under additive keys.
- New metrics: pure function returning dict; never mutate prior outputs.
- New artifacts: add descriptor to manifest writer ensuring size & sha recorded.

## Anti-Goals
- Multi-user tenancy (out of scope; single-user ephemeral registry)
- Implicit data corrections (all anomalies counted & surfaced)
- Hidden randomness (must be seed-derivable)

## Future Enhancements
- Bootstrap & Monte Carlo modules (additive schema extension)
- Dataset diff explorer tooling
- Portfolio-level multi-symbol orchestrator (shared seed partitioning)

---
Maintainers: update this document first when altering core pipeline stages or artifact semantics.
