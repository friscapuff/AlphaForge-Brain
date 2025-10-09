from __future__ import annotations

from api.app import create_app


def test_openapi_includes_error_schema_or_examples():
    app = create_app()
    spec = app.openapi()
    # Tolerant check: ensure components exist and basic schemas or responses are present
    assert isinstance(spec, dict)
    assert "paths" in spec
    assert "components" in spec
    # Now assert explicit ErrorResponse schema and X-Correlation-ID header presence
    comps = spec.get("components", {})
    schemas = comps.get("schemas", {})
    headers = comps.get("headers", {})
    assert "ErrorResponse" in schemas
    assert "X-Correlation-ID" in headers
