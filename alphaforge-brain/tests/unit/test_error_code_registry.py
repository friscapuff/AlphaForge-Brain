from __future__ import annotations

from api.error_codes import (
    DETAIL_CODE_MAP,
    all_codes,
    infer_code_from_detail,
    map_domain_code_to_status,
    openapi_example_errors,
    render_markdown_table,
    to_kebab,
)


def test_to_kebab_basic() -> None:
    assert to_kebab("INVALID_PARAM") == "invalid-param"
    assert to_kebab(" dependency unavailable ") == "dependency-unavailable"
    assert to_kebab(None) == "unknown-error"


def test_map_domain_code_to_status_defaults() -> None:
    assert map_domain_code_to_status("INVALID_PARAM") == 400
    assert map_domain_code_to_status("NOT_FOUND") == 404
    assert map_domain_code_to_status("CONFLICT") == 409
    assert map_domain_code_to_status("SOMETHING_ELSE") == 400
    assert map_domain_code_to_status(None) == 400


def test_infer_code_from_detail_prefixes() -> None:
    for marker, code in DETAIL_CODE_MAP:
        # Take just the marker as detail and ensure mapping picks it up
        assert infer_code_from_detail(marker) == code
    # Unknown detail falls back
    assert infer_code_from_detail("totally unknown message") == "UNKNOWN_ERROR"


def test_all_codes_and_render_table() -> None:
    rows = all_codes()
    kebabs = {r["kebab"] for r in rows}
    assert "invalid-param" in kebabs
    assert "internal-error" in kebabs
    md = render_markdown_table()
    assert "| Code | Kebab | Status | Description |" in md
    assert "invalid-param" in md


def test_openapi_example_errors() -> None:
    examples = openapi_example_errors(limit=3)
    assert 1 <= len(examples) <= 3
    for ex in examples:
        assert "error_code" in ex and "message" in ex
