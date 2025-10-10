# Contracts: Advanced Statistical Validation

This directory captures reference payloads and schema notes for the Masters-style validation integration.

## Contents
- `api-run.validation.example.json` — Representative response fragment for `GET /api/v1/runs/{run_id}`.
- `sse-validation-update.example.json` — Example Server-Sent Event payload streaming validation sections.
- `manifest.validation.example.json` — Manifest excerpt showing stored metadata and artifact references.

All examples assume validation schema version 2. Field additions are backward compatible; legacy clients should ignore unknown keys.
