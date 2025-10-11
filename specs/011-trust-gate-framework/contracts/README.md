# Contracts: Trust Gate Framework

Reference payloads and schema notes for trust gate surfaces between AlphaForge Brain and consuming clients (Mind, CI, tooling).

## Contents
- `api-run.trust_gate.example.json` — Representative `GET /api/v1/runs/{run_id}` trust gate section.
- `manifest.trust_gate.example.json` — Manifest excerpt showing trust gate summary and artifact references.
- `sse-trust_gate-update.example.json` — Example Server-Sent Event emitted when trust gates complete.
- `cli-trust_gates.example.txt` — Sample CLI output for `poetry run trust-gates`.

Schema version: `trust_gates.v1`. Unknown fields must be ignored by clients to maintain forward compatibility.
