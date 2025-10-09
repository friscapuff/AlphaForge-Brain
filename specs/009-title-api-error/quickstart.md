# Quickstart: API Error Logging Improvement (009)

This guide helps you try the new error contract, correlation tracing, and verbosity/redaction settings.

## Prerequisites
- Python 3.11
- Poetry (preferred) or requirements.txt

## Install

Using Poetry:

```powershell
poetry install
```

Using requirements.txt:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Run the API

```powershell
poetry run uvicorn api.app:app --reload
```

Open:
- http://localhost:8000/docs
- http://localhost:8000/openapi.json
- http://localhost:8000/metrics

## Toggle verbosity and redaction

```powershell
# Development verbosity (includes debug block on 5xx)
$env:ERROR_VERBOSITY = "development"

# Redaction mode (strict default; relaxed allows placeholders)
$env:ERROR_REDACTION_MODE = "strict"  # or "relaxed"
```

## Try an invalid request

```powershell
# Missing fields force validation errors
poetry run python - << 'PY'
import httpx
r = httpx.post("http://localhost:8000/runs", json={"symbol":"NVDA"})
print(r.status_code)
print(r.headers.get("X-Correlation-ID"))
print(r.json())
PY
```

Expected:
- Response status 400/422
- Header `X-Correlation-ID` present and matches body `correlation_id`
- Body includes `error_code`, `message`, and optionally `details`

## Notes
- Metrics counter `api_error_total{category,endpoint,status}` increments on errors.
- OpenAPI includes `components.schemas.ErrorResponse` and `components.headers.X-Correlation-ID`.
- No secrets/PII are ever included in responses.
