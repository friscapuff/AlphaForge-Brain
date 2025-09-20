# syntax=docker/dockerfile:1.6
# Multi-stage Dockerfile for Project A Backend (T071)

#############################
# Builder image
#############################
FROM python:3.11-slim AS builder
ENV POETRY_VERSION=1.8.3 \
    POETRY_NO_INTERACTION=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DEFAULT_TIMEOUT=120 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl git && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install --no-cache-dir poetry==${POETRY_VERSION}

WORKDIR /app

# Copy only dependency files first for layer caching
COPY pyproject.toml poetry.lock ./
# Export only main (non-dev) dependencies to a requirements file, then install with simple retry loop
RUN set -eux; \
    poetry export -f requirements.txt --without-hashes -o requirements.txt; \
    attempts=0; \
    until pip install --no-cache-dir --timeout 120 -r requirements.txt; do \
        attempts=$((attempts+1)); \
        if [ "$attempts" -ge 3 ]; then echo 'pip install failed after 3 attempts' >&2; exit 1; fi; \
        echo "Retrying pip install (attempt $attempts)..."; \
        sleep 5; \
    done

# Install project into a wheel (editable not required in final image)
COPY . .
RUN poetry build -f wheel && pip install --no-cache-dir dist/*.whl

#############################
# Runtime image
#############################
FROM python:3.11-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 APP_ENV=production

# Minimal runtime deps (tzdata for pandas timezones)
RUN apt-get update && apt-get install -y --no-install-recommends tzdata && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy installed site-packages from builder
COPY --from=builder /usr/local/lib/python3.11 /usr/local/lib/python3.11
COPY --from=builder /usr/local/bin/uvicorn /usr/local/bin/uvicorn
# orjson may not drop a standalone binary; ignore if absent
RUN set -eux; for f in /usr/local/bin/orjson*; do [ -e "$f" ] && cp "$f" /usr/local/bin/ || true; done

# Copy runtime artifacts (OpenAPI, specs, etc.)
COPY specs ./specs
COPY src/api ./api
COPY src/domain ./domain
COPY src/infra ./infra
COPY scripts ./scripts
COPY README.md ./README.md
COPY docker-entrypoint.sh ./docker-entrypoint.sh
RUN chmod +x docker-entrypoint.sh

# Non-root user
RUN useradd -u 1001 appuser && chown -R appuser /app
USER appuser

EXPOSE 8000

ENTRYPOINT ["./docker-entrypoint.sh"]
