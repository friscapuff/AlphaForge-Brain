# AlphaForge3 Development Guidelines

Auto-generated from all feature plans. Last updated: 2025-10-11

## Active Technologies
- Python 3.11 (Poetry-managed virtualenv) + pytest, coverage.py, psutil (for RSS capture), FastAPI/uvicorn stack, ruff/mypy tooling (012-tests-enhancment-deliver)
- Python 3.11 (Poetry-managed virtualenv) + FastAPI surfaces, Pydantic models, internal `services.trust_gates` suite, Masters validation engines, Prometheus client, Ruff/Mypy strict-plus overlays (013-testing-governance-hardening)
- SQLite artifacts, JSON manifests, Parquet exports (Brain project scope) (013-testing-governance-hardening)

## Project Structure
```
src/
tests/
```

## Commands
cd src; pytest; ruff check .

## Code Style
Python 3.11 (Poetry-managed virtualenv): Follow standard conventions

## Recent Changes
- 013-testing-governance-hardening: Added Python 3.11 (Poetry-managed virtualenv) + FastAPI surfaces, Pydantic models, internal `services.trust_gates` suite, Masters validation engines, Prometheus client, Ruff/Mypy strict-plus overlays
- 012-tests-enhancment-deliver: Added Python 3.11 (Poetry-managed virtualenv) + pytest, coverage.py, psutil (for RSS capture), FastAPI/uvicorn stack, ruff/mypy tooling

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
