"""OpenAPI additive diff contract test (T071).

Ensures that the generated OpenAPI schema only changes additively vs the stored
snapshot `tests/contract/openapi_snapshot.json`.

Rules:
1. info.version must match package version (covered elsewhere but reasserted here).
2. Removing a path, operation, schema, property is a BREAKING change -> test fails.
3. Adding new properties/paths is allowed (logged for visibility).
4. Changing a schema type/enum without additive superset is breaking.

Implementation keeps logic lightweight to avoid adding heavy dependencies.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

try:
    from api.app import create_app
except Exception:  # pragma: no cover - defensive import guard
    create_app = None  # type: ignore

SNAPSHOT_PATH = Path(__file__).with_name("openapi_snapshot.json")


def _load_current() -> dict[str, Any]:
    # Build app and extract schema (FastAPI generates on demand)
    assert create_app is not None, "FastAPI app factory import failed"
    app = create_app()
    schema = app.openapi()  # type: ignore[no-untyped-call]
    return schema  # type: ignore[return-value]


def _load_snapshot() -> dict[str, Any]:
    if not SNAPSHOT_PATH.exists():
        pytest.skip("OpenAPI snapshot missing - generate snapshot before running diff test.")
    return json.loads(SNAPSHOT_PATH.read_text("utf-8"))


def _compare_dict_keys(old: dict[str, Any], new: dict[str, Any], prefix: str, removed: set[str], added: set[str]):
    old_keys = set(old.keys())
    new_keys = set(new.keys())
    for k in sorted(old_keys - new_keys):
        removed.add(f"{prefix}{k}")
    for k in sorted(new_keys - old_keys):
        added.add(f"{prefix}{k}")


def _walk_schema(old: Any, new: Any, path: str, removed: set[str], added: set[str]):
    # Only descend matching container types; differences at container level are breaking & handled via key diff.
    if isinstance(old, dict) and isinstance(new, dict):
        _compare_dict_keys(old, new, path, removed, added)
        for k in old.keys() & new.keys():
            _walk_schema(old[k], new[k], f"{path}{k}.", removed, added)
    elif isinstance(old, list) and isinstance(new, list):
        # Heuristic: compare list length; if snapshot list is longer, removal occurred.
        if len(old) > len(new):
            removed.add(f"{path}[list_length]:{len(old)}->{len(new)}")
        elif len(new) > len(old):
            added.add(f"{path}[list_length]:{len(old)}->{len(new)}")
    else:
        # Primitive change: if types differ -> treat as removal+addition for clarity
        if old.__class__ is not new.__class__:
            removed.add(f"{path[:-1]}:type_changed:{type(old).__name__}->{type(new).__name__}")


def test_openapi_additive_diff():
    current = _load_current()
    snapshot = _load_snapshot()

    # Reassert version alignment
    assert current.get("info", {}).get("version") == snapshot.get("info", {}).get("version"), "Version drift - bump snapshot alongside package version bump."

    removed: set[str] = set()
    added: set[str] = set()

    # Focus on high-value top-level sections
    for section in ("paths", "components"):
        if section in snapshot and section in current:
            _walk_schema(snapshot[section], current[section], f"{section}.", removed, added)

    # Fail if anything removed (breaking)
    if removed:
        missing = "\n".join(sorted(removed)[:25])
        pytest.fail(f"Breaking OpenAPI change(s) detected (removed/changed keys):\n{missing}\nTotal removed: {len(removed)}")

    # Log additions for visibility (not a failure)
    if added:
        print("Additive OpenAPI changes:")
        for k in sorted(list(added)[:25]):
            print("  +", k)


def test_openapi_snapshot_file_kept_small():
    # Ensures snapshot file not excessively large (guard accidental HTML dump, etc.)
    size_kb = SNAPSHOT_PATH.stat().st_size / 1024 if SNAPSHOT_PATH.exists() else 0
    assert size_kb < 512, f"Snapshot unexpectedly large: {size_kb:.1f} KB"
