# API Contract v0.1 (Brain)

## Endpoints
- POST /runs: Submit a run
  - Request: config_json, dataset_ref, seed_root (optional)
  - Response: run_hash, status, manifest
- GET /runs/{run_hash}: Fetch run status & manifest
- GET /runs/{run_hash}/artifacts: List artifacts with hashes and retention_state
- GET /runs/{run_hash}/events (SSE): Stream seeded events (phase, progress, timings)
- POST /runs/{run_hash}/pin: Pin a run (body: reason)
- POST /runs/{run_hash}/unpin: Unpin a run
- POST /runs/{run_hash}/rehydrate: Rebuild evicted artifacts deterministically

## Contracts
- All responses include: api_version, schema_version, run_hash, content_hash
- Determinism: Responses stable given same inputs and seed_root
- Versioning: Semantic version pinned at api_version=0.1; MAJOR bump on breaking change

## Error Model
- 4xx: Validation/contract errors (explicit message, code)
- 5xx: Internal errors with trace_id and minimal diagnostics; manifest records failure
