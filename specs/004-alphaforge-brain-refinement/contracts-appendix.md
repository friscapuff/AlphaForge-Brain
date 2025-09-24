# Contracts Appendix: AlphaForge Brain

This appendix explains, in plain language, the key contracts (agreements between parts of the system) used by AlphaForge Brain. It is designed to be easy to understand for readers without a coding background.

## What is a Contract?
A contract describes what data looks like (its fields) and the rules everyone must follow when creating or reading that data. Contracts help keep the system reliable and predictable.

## 1) Manifest (Run Configuration) Schema
The manifest captures the full configuration of a "run" (an experiment or backtest). It includes:
- What data we use (for example, stock symbol and time period)
- Which features (indicators) are applied
- Which strategy parameters are used
- What validation methods are enabled (like bootstrap sampling)
- Extra provenance (trace) information for reproducibility

In the repository, a formal JSON Schema exists at:
- `specs/004-alphaforge-brain-refinement/contracts/manifest.schema.json`

In simple terms, here are the kinds of fields you’ll find:
- run_id / run_hash: Unique identifiers for a run
- dataset: Where the price data comes from and its time range
- features: A list of feature names and their settings
- strategy: The algorithm’s parameters for deciding when to buy/sell
- validation: Methods used to test robustness (e.g., bootstrap, walk‑forward)
- provenance: Extra information like database version and random seed

Why it matters: If two people use the same manifest, they should get the same results. This enables fair comparisons and auditing.

## 2) Persistence (Database) Entities
AlphaForge stores important pieces of each run in a lightweight database (SQLite). Key tables include:
- runs: One row per run with high‑level details (manifest, seeds, version)
- trades: Individual buy/sell records
- equity: The account value over time (the equity curve)
- features_cache: Metadata about cached feature files (like shape and checksum)
- phase_metrics: Timing and tracing markers for transparency
- run_errors: Any errors captured during a run
- validations: Results from statistical validation (e.g., bootstrap summaries)

Why it matters: This provides a trustworthy history of what happened in each run. It’s the system’s memory.

## 3) Validation Artifacts
Validation outputs measure how stable and trustworthy a strategy’s results are. Common artifacts include:
- Bootstrap distributions: Many re‑simulations to estimate result variability
- Walk‑forward results: Performance across rolling time windows
- Merge summaries: Combined views that summarize overall robustness

Why it matters: Strong strategies should be consistent across time and under resampling.

## 4) Error Code Taxonomy
When things go wrong, clear and consistent error codes help us understand and fix issues quickly. Codes are grouped by area:
- PERSIST_xxx: Database or storage issues (e.g., failed to write results)
- CAUSAL_xxx: Time‑related rules violations (e.g., attempted to use future data)
- STATS_xxx: Statistical processing problems (e.g., invalid bootstrap parameters)
- PIPE_xxx: Pipeline coordination problems (e.g., wrong configuration shape)
- OBS_xxx: Observability/tracing issues (e.g., missing timing markers)
- CI_xxx: Continuous Integration gates (e.g., width too wide in acceptance tests)

Why it matters: Standardized codes reduce confusion and speed up resolution.

## 5) API and OpenAPI
The project includes an OpenAPI description (`openapi.json` and `openapi.html`). This document explains the available endpoints (like how to start a run or fetch its results) in a machine‑ and human‑readable way.

Why it matters: OpenAPI doubles as documentation and a contract for anyone integrating with AlphaForge Brain.

## 6) Determinism & Reproducibility
Determinism means that given the same inputs and configuration, AlphaForge Brain produces identical outputs (bit‑for‑bit where applicable). The system enforces:
- Strict time‑order execution (no “peeking” into the future)
- Seeded randomness for statistical procedures
- Canonical JSON formatting and content hashing for key artifacts

Why it matters: Reproducibility builds trust—results can be verified by others.

## Glossary
- Manifest: A structured configuration for a run
- Bootstrap: A statistical method that resamples data to estimate variability
- Walk‑forward: Testing over sequential time windows to simulate changing markets
- Equity curve: A chart of account value over time
- Provenance: The recorded history and settings that led to a result
