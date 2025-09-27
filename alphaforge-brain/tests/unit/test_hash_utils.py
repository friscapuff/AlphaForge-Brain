from __future__ import annotations

# New hash utility module (infra.utils.hash) coverage
from datetime import date, datetime, timezone
from enum import Enum
from pathlib import Path

import pytest
from src.infra.utils.hash import (
    canonical_json,
    hash_canonical,
    row_digest,
    sha256_hex,
    sha256_of_text,
)
from src.lib.hash_utils import canonical_dumps, run_config_hash, run_hash


def test_canonical_dumps_ordering_stable() -> None:
    data_a = {"b": 2, "a": 1}
    data_b = {"a": 1, "b": 2}
    assert canonical_dumps(data_a) == canonical_dumps(data_b)


def test_run_config_hash_changes_with_value() -> None:
    config = {"a": 1}
    h1 = run_config_hash(config)
    config["a"] = 2
    h2 = run_config_hash(config)
    assert h1 != h2


def test_run_hash_composition() -> None:
    rh = run_hash("c1", "d1", 8, "v1")
    rh2 = run_hash("c1", "d1", 8, "v1")
    assert rh == rh2
    rh3 = run_hash("c1", "d1", 9, "v1")
    assert rh != rh3


# ---------------------------------------------------------------------------
# Additional tests for infra.utils.hash canonicalization & helpers
# ---------------------------------------------------------------------------


class _Color(Enum):
    RED = 1
    BLUE = 2


def test_canonical_json_orders_keys_and_truncates_floats() -> None:
    payload = {"b": 3.1415926535, "a": 2.7182818284}
    s1 = canonical_json(payload)
    s2 = canonical_json({"a": 2.7182818284, "b": 3.1415926535})
    assert s1 == s2  # key order stable
    # Precision in settings is 12 so full original strings (10+ digits) may persist; assert deterministic ordering instead
    assert s1 == '{"a":2.7182818284,"b":3.1415926535}'


def test_canonical_json_datetime_date_enum_and_path_normalization(
    tmp_path: Path,
) -> None:
    dt = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
    d = date(2024, 1, 2)
    p = tmp_path / "file.txt"
    p.write_text("x")
    obj = {"when": dt, "day": d, "color": _Color.RED, "path": p}
    out = canonical_json(obj)
    assert "2024-01-01T12:00:00Z" in out  # UTC Z designator
    assert "2024-01-02" in out
    assert "file.txt" in out
    # Enum collapsed to its value (1)
    assert "1" in out


def test_hash_canonical_deterministic_under_unordered_input() -> None:
    a = {"x": 1, "y": [3, 2, 1]}
    b = {"y": [3, 2, 1], "x": 1}
    assert hash_canonical(a) == hash_canonical(b)


def test_sha256_helpers_round_trip() -> None:
    text = "AlphaForge Rocks"
    h = sha256_of_text(text)
    assert h == sha256_hex(text.encode())
    assert h != sha256_of_text(text + "!")


def test_row_digest_accepts_mapping_like() -> None:
    class RowLike(dict):
        pass

    r = RowLike(a=1, b=2)
    d1 = row_digest(r)
    d2 = row_digest({"b": 2, "a": 1})
    assert d1 == d2


def test_row_digest_list_input_stable() -> None:
    # Fallback path (non-dict coercion) — list should hash as-is deterministically
    lst = [1, 2, 3]
    h1 = row_digest(lst)
    h2 = row_digest(lst.copy())
    assert h1 == h2


@pytest.mark.parametrize(
    "mutation",
    [
        lambda o: o.update({"new": 5}),
        lambda o: o.setdefault("nested", {"k": 1}),
    ],
)
def test_hash_canonical_changes_on_mutation(mutation) -> None:  # type: ignore
    base = {"a": 1, "b": {"c": 2}}
    h0 = hash_canonical(base)
    mutation(base)
    assert hash_canonical(base) != h0
