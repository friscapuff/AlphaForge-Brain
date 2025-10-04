# AlphaForge Brain API Overview

This document provides a concise, implementation-synchronized overview of the public API surface currently exposed by the AlphaForge Brain service. It is intended for:

- Backend integrators
- Internal platform/runtime orchestration
- Future client SDK authors
- Test/contract authors

> Scope: Focuses on stable, test-backed endpoints. Anything not listed here is considered internal and subject to change.

## Versioning & Determinism Guarantees

The API and engine emphasize **reproducibility**, **structural determinism**, and **artifact integrity**.

| Aspect | Guarantee |
| ------ | --------- |
| Run ID generation | Cryptographic-strength, collision-resistant identifiers (UUID / hash-based) |
| Artifact manifest | Stable schema; all produced artifacts enumerated with type + path + hash |
| Metrics | Deterministic given identical inputs (data slice + parameters + engine version) |
| Validation outputs | Deterministic and hash-traceable |
| Engine/app version | Exposed at `/version` and embedded in run metadata |
| SSE event order | Strictly monotonic sequence IDs per run |

Reproducibility contract: A run re-executed with the same inputs MUST produce identical core artifacts (metrics, equity curve, trades, validation, manifest hashes) unless an engine version change is declared.

## Authentication

(Not yet implemented.) All endpoints are unauthenticated in the current phase. Add an auth layer before external exposure.

## Media Types

| Type | Usage |
| ---- | ----- |
| `application/json` | Standard request/response bodies |
| `text/event-stream` | Server-Sent Events stream for run progress |

## Endpoints

### POST /runs

Submit a new simulation/backtest run request.

Request body (representative shape – see Pydantic model for authoritative definition):
```json
{
  "preset": "walkforward-basic",         // Optional named preset
  "parameters": { "window": 50 },        // Strategy / engine parameters
  "data": {                               // Data selection / slice spec
    "symbol": "AAPL",
    "start": "2022-01-01",
    "end": "2022-12-31"
  },
  "tags": ["ci", "regression"],
  "metadata": { "initiator": "contract-test" }
}
```

Response 202 Accepted:
```json
{
  "run_id": "af_01hxyz...",
  "status": "queued",
  "submitted_at": "2024-09-25T12:34:56.123Z"
}
```
Semantics:
- Asynchronous execution; artifacts become available progressively.
- Idempotency: Submitting identical bodies may yield distinct run IDs (no dedupe layer yet).

### GET /runs/{run_id}
Retrieve the current state + artifact index for a run.

Response (example):
```json
{
  "run_id": "af_01hxyz...",
  "status": "completed",
  "started_at": "2024-09-25T12:34:56.789Z",
  "completed_at": "2024-09-25T12:35:07.004Z",
  "engine_version": "0.1.0",
  "app_version": "0.1.0",
  "parameters": { "window": 50 },
  "metrics": {
    "sharpe": 1.42,
    "return": 0.0831,
    "drawdown": -0.041
  },
  "artifacts": [
    {"name": "manifest.json", "kind": "manifest", "sha256": "...", "path": "runs/af_01hxyz/manifest.json"},
    {"name": "metrics.json", "kind": "metrics", "sha256": "...", "path": "runs/af_01hxyz/metrics.json"},
    {"name": "validation.json", "kind": "validation", "sha256": "...", "path": "runs/af_01hxyz/validation.json"},
    {"name": "equity.parquet", "kind": "equity_curve", "sha256": "...", "path": "runs/af_01hxyz/equity.parquet"},
    {"name": "trades.parquet", "kind": "trades", "sha256": "...", "path": "runs/af_01hxyz/trades.parquet"},
    {"name": "plots.png", "kind": "plot_bundle", "sha256": "...", "path": "runs/af_01hxyz/plots.png"}
  ]
}
```
Semantics:
- Always returns the canonical list of recognized artifacts (subset may be materialized early-phase).
- Missing-yet-expected artifacts: MAY be omitted or flagged depending on implementation detail (future: explicit readiness states).

### GET /runs/{run_id}/events (SSE)
Server-Sent Events stream emitting lifecycle + progress events.

Event fields:
- `id`: Monotonic sequence number (string or int-formatted)
- `event`: Event type (`status`, `artifact`, `metric`, `heartbeat`)
- `data`: JSON payload

Example event wire format:
```
id: 7
event: artifact
data: {"name": "metrics.json", "sha256": "...", "kind": "metrics"}

```
Termination: Stream closes after terminal status (`completed`, `failed`, `canceled`). Clients should treat a disconnect pre-terminal as retryable.

### GET /version
Returns build / semantic version indicators.

Response:
```json
{
  "app_version": "0.1.0",
  "engine_version": "0.1.0",
  "api_revision": "2024.09.25"  // (If exposed; optional)
}
```

## Run Lifecycle States

| State | Meaning |
| ----- | ------- |
| queued | Accepted, awaiting execution slot |
| running | Engine executing / generating artifacts |
| completed | Success path; all core artifacts finalized |
| failed | Irrecoverable error; partial artifacts MAY exist |
| canceled | Aborted by operator (future) |

## Determinism Notes

Key sources of nondeterminism eliminated:
- System clock usage outside timestamp stamping (simulation seeded).
- Random number generators seeded per run.
- Data slicing pinned to explicit ranges + symbol(s).

###  Deterministic Timestamp & Event Ordering Addendum (2025-09-23)
Test infrastructure now freezes wall-clock time in unit/integration tests that assert manifest or SSE event timestamps. The production system still stamps real UTC instants; tests substitute a subclassed `datetime` inside project modules only (third-party libs unaffected). SSE events remain strictly ordered by an in-process monotonic counter; contract tests assert both ordering and heartbeat interval without relying on wall-clock drift tolerance.

Residual variability considerations:
- Floating point drift across hardware/BLAS variants (expected negligible; metrics normalized).
- Engine version change intentionally invalidates strict hash expectations.

## Error Handling

| Condition | Status | Body Shape |
| --------- | ------ | ---------- |
| Unknown run_id | 404 | `{ "detail": "run not found" }` |
| Malformed body | 422 | FastAPI validation errors |
| Internal error | 500 | `{ "detail": "internal error" }` (future: trace id) |

## Pagination & Filtering
(Not implemented.) Future enhancements: `GET /runs?status=completed&limit=50`.

## Stability Index

| Endpoint | Stability |
| -------- | --------- |
| POST /runs | beta |
| GET /runs/{id} | beta |
| GET /runs/{id}/events | beta |
| GET /version | stable |

Definitions:
- experimental: Subject to structural change without notice
- beta: Backward-compatible within minor versions; fields may be added
- stable: Strong backward compatibility; only additive, non-breaking changes

## Client Recommendations

- Use SSE for near-real-time progress instead of polling GET /runs aggressively.
- Treat SSE disconnects as transient; implement exponential backoff reconnect with `Last-Event-ID` (future support).
- Cache artifact hashes to avoid redundant downloads.

## Planned Extensions (Roadmap)

| Area | Item |
| ---- | ---- |
| Auth | API tokens + role scoping |
| Query | Run listing & filtering |
| Replay | Deterministic re-run endpoint (`POST /runs/{id}/replay`) |
| Diff | Artifact diffing / run comparison endpoint |
| Bundles | Compressed artifact bundle export |
| Webhooks | Callback registration for terminal states |
| Validation | Adaptive walk-forward & permutation summary endpoints |

## Traceability Checklist

| Guarantee | Mechanism |
| --------- | --------- |
| Artifact integrity | SHA-256 hashing at creation time |
| Full run manifest | `manifest.json` enumerates all primary outputs |
| Version trace | Run metadata + `/version` endpoint |
| Event ordering | Monotonic in-process counter |
| Deterministic metrics | Seeded simulation & controlled data slice |

---
Maintainers: Update this file if endpoint shapes or determinism guarantees change. Contract tests should fail if undocumented breaking changes are introduced.
