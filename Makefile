# Project A Backend - Convenience Makefile
# All commands funnel through Poetry to ensure the managed virtual environment is used.
# Use `make help` to list targets.

POETRY_RUN=poetry run
PYTEST_OPTS?=

.DEFAULT_GOAL := help

help:
	@echo "Available targets:"
	@grep -E '^[a-zA-Z_-]+:.*?##' $(MAKEFILE_LIST) | sed -E 's/:.*?##/\t- /'

install: ## Install dependencies (respect lock)
	poetry install

lock: ## Regenerate lock file (no version bumps)
	poetry lock --no-update

update: ## Update dependencies to latest allowed versions & lock
	poetry update

run: ## Start API server (prod-ish)
	$(POETRY_RUN) uvicorn api.app:app --host 0.0.0.0 --port 8000

run-dev: ## Start API server with reload
	$(POETRY_RUN) uvicorn api.app:app --reload --host 0.0.0.0 --port 8000

test: ## Run tests
	$(POETRY_RUN) pytest $(PYTEST_OPTS)

test-cov: ## Run tests with coverage
	$(POETRY_RUN) pytest --cov=src --cov-report=term-missing $(PYTEST_OPTS)

bench: ## Run microbenchmark harness (T068)
	$(POETRY_RUN) python scripts/bench/perf_run.py --iterations 5 --warmup 1

lint: ## Lint (Ruff)
	$(POETRY_RUN) ruff check .

format: ## Auto-fix with Ruff
	$(POETRY_RUN) ruff check . --fix

format-style: ## (Optional) run Ruff formatting mode if adopted
	$(POETRY_RUN) ruff format .

type: ## Type check (mypy)
	$(POETRY_RUN) mypy src

pre-commit: ## Run all pre-commit hooks on entire codebase
	$(POETRY_RUN) pre-commit run --all-files

clean: ## Remove Python caches & build artifacts
	@echo "Cleaning caches..."
	@find . -type d -name __pycache__ -prune -exec rm -rf {} + 2>NUL || true
	@find . -type f -name '*.py[co]' -delete 2>NUL || true
	@find . -type d -name '.pytest_cache' -prune -exec rm -rf {} + 2>NUL || true
	@rm -rf build dist .mypy_cache 2>NUL || true

venv-info: ## Show Poetry environment info
	poetry env info

shell: ## Spawn Poetry shell
	poetry shell

sanity: ## Run environment sanity check (strict + dev)
	$(POETRY_RUN) python scripts/env/check_env.py --dev --strict

lock-checksum: ## Regenerate poetry.lock checksum file
	powershell -Command "Get-FileHash poetry.lock -Algorithm SHA256 | Select-Object -ExpandProperty Hash > scripts/env/poetry.lock.sha256"
