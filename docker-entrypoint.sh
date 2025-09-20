#!/usr/bin/env bash
set -euo pipefail

echo "[entrypoint] Starting Project A Backend"
echo "[entrypoint] Python version: $(python -V)"

# Placeholder: run migrations if using Alembic later
if [ -d "infra/migrations" ]; then
  echo "[entrypoint] (skip) migrations not wired yet"
fi

export APP_ENV=${APP_ENV:-production}

exec uvicorn api.app:app \
  --host 0.0.0.0 \
  --port ${PORT:-8000} \
  --workers ${UVICORN_WORKERS:-1} \
  --no-access-log