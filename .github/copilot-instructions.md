# AlphaForge3 Development Guidelines

Auto-generated from all feature plans. Last updated: 2025-10-11

## Active Technologies
- Python 3.11 (Poetry-managed virtualenv) + pytest, coverage.py, psutil (for RSS capture), FastAPI/uvicorn stack, ruff/mypy tooling (012-tests-enhancment-deliver)
- Python 3.11 (Poetry-managed virtualenv) + FastAPI surfaces, Pydantic models, internal `services.trust_gates` suite, Masters validation engines, Prometheus client, Ruff/Mypy strict-plus overlays (013-testing-governance-hardening)
- SQLite artifacts, JSON manifests, Parquet exports (Brain project scope) (013-testing-governance-hardening)
- Python 3.11 (Poetry-managed environment) + FastAPI, Pydantic, internal orchestration/validation services, pytest + ruff/mypy tooling (014-param-sweep-introduction)
- Existing SQLite manifests, artifact directories, and optional Parquet/CSV caches (no new storage engines) (014-param-sweep-introduction)
- Python 3.11 (Poetry-managed) for backend automation; dashboards via existing observability stack (presumed Python + Prometheus metrics wiring). + FastAPI services, pytest benchmarks, Prometheus client tooling, existing parquet doctor script, CI (GitHub Actions) with ruff/mypy. (015-addressing-pitfalls-to)
- SQLite artifacts, JSON/Parquet caches, Prometheus TSDB, governance tracker (existing SQLite/JSON). (015-addressing-pitfalls-to)
- Python 3.11 (Poetry-managed env) + Pydantic v2 models, internal `alphaforge_brain` services/pipelines, FastAPI surfaces, Prometheus client, pandas/numpy for aggregates (016-description-initiate-the)
- SQLite (`studio.db` artifacts), JSON/Parquet exports under `zz_artifacts/` (Brain scope) (016-description-initiate-the)

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
- 016-description-initiate-the: Added Python 3.11 (Poetry-managed env) + Pydantic v2 models, internal `alphaforge_brain` services/pipelines, FastAPI surfaces, Prometheus client, pandas/numpy for aggregates
- 015-addressing-pitfalls-to: Added Python 3.11 (Poetry-managed) for backend automation; dashboards via existing observability stack (presumed Python + Prometheus metrics wiring). + FastAPI services, pytest benchmarks, Prometheus client tooling, existing parquet doctor script, CI (GitHub Actions) with ruff/mypy.
- 014-param-sweep-introduction: Added Python 3.11 (Poetry-managed environment) + FastAPI, Pydantic, internal orchestration/validation services, pytest + ruff/mypy tooling

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
