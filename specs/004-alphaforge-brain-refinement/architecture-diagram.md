# Architecture Overview (Mermaid Diagram)

This document offers a simple, visual overview of how AlphaForge Brain is organized. It focuses on clarity and avoids technical jargon wherever possible.

## Big Picture
- Data is read and prepared (features)
- A strategy runs over time on that data
- Results are stored (trades, equity, validations)
- Checks are performed to ensure results are stable and reproducible

## Diagram
```mermaid
flowchart LR
  A[Input Data] --> B[Feature Builder]
  B --> C[Strategy Engine]
  C --> D[Results]
  D -->|Trades & Equity| E[(SQLite Database)]
  D -->|Artifacts| F[Files (e.g., Parquet, JSON)]
  C --> G[Validation]
  G --> E
  C --> H[Observability]
  H --> E
  subgraph CI
    I[Determinism Replay]
    J[Bootstrap CI Width Gate]
    K[Acceptance Suite]
  end
  E --> I
  E --> J
  E --> K
```

## What Lives Where
- Feature Builder: Creates indicators (like moving averages) from input data
- Strategy Engine: Decides when to buy or sell based on features
- Results: The outcomes (equity curve and list of trades)
- Validation: Statistical checks (bootstrap resampling, walk‑forward testing)
- Observability: Timing and traces so you can see what happened
- SQLite Database: A simple, reliable storage file for runs and their results
- CI (Continuous Integration): Automated checks that run on every change

## Why This Matters
- Separation of concerns keeps the system understandable
- Clear storage of results makes auditing simple
- Automated checks prevent regressions and ensure trust
