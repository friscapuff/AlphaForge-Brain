# Persistence Quickstart: From Run to Query

This guide walks you through running AlphaForge Brain and then viewing the stored results, without requiring programming knowledge. We’ll use simple steps and explain the terms along the way.

## What You’ll Do
1) Start a run (an experiment/backtest)
2) Wait for it to finish
3) Look up the results stored in a local database (SQLite)

## Key Concepts in Plain Language
- Run: A single experiment with a specific configuration
- Manifest: The “recipe” for the run (what data, features, and settings)
- SQLite: A small file‑based database that stores results
- Equity: Your account value over time
- Trades: The individual buy/sell actions taken by the strategy

## Step 1: Start a Run
There are several ways to start a run depending on your setup. In CI and tests, runs are launched by Python code. Locally, you might use a helper script or a small Python entry point. The run will:
- Load the manifest (configuration)
- Build features
- Execute the strategy across time
- Record results and validation summaries

When the run starts, it also writes an entry to the database with a unique identifier called the run hash. Think of this like a receipt number.

## Step 2: Let It Finish and Record Results
At the end of the run, AlphaForge Brain stores:
- A copy of the manifest (for transparency)
- The final equity curve and trade list
- Any validation results (like bootstrap summaries)
- Timing and trace information for visibility

This ensures anyone can later reconstruct what happened and verify results.

## Step 3: Query Your Results
If you’re comfortable with basic tools, you can open the SQLite database using a graphical browser or command‑line tool. The main tables to look at are:
- runs: One row per run, with run_hash, manifest, seeds, and version info
- equity: Equity values over time (date and value)
- trades: Individual trades with timestamps, sides (buy/sell), and sizes
- validations: Summaries of statistical checks
- phase_metrics: Timing entries for stages of the run

Tip: Use the run_hash from the runs table to filter related rows in other tables.

## Reproducibility
The system records a canonical (standardized) JSON copy of the manifest and content hashes. If two runs have the same manifest and data, they should produce the same outputs. This makes audits simple and results trustworthy.

## Where Is the Database?
The project uses SQLite and sets a path as part of the run configuration. In CI and tests, this is handled automatically. For local usage, refer to README notes in this repository for the current default location and how to override it.

## Troubleshooting
- If the runs table is empty: Ensure a run has completed successfully
- If you can’t find the database file: Check the README and configuration
- If results don’t match expectations: Review the manifest used and validation summaries

## Learn More
- Contracts Appendix: See `contracts-appendix.md` for schemas and error codes
- HADJ‑BB & CI Width Gate: See `hadj-bb-ci-width-policy.md` for validation details
- Architecture Diagram: See `architecture-diagram.md` for how parts fit together
