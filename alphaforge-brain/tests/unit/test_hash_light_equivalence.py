from __future__ import annotations

from datetime import date, datetime, timezone
from enum import Enum
from pathlib import Path

from src.infra.utils.hash import canonical_json, hash_canonical
from src.infra.utils.hash_light import canonical_json_light, hash_canonical_light


class C(Enum):
    A = 1
    B = 2


CORPUS = [
    {},
    {"a": 1, "b": 2},
    {"b": 2, "a": 1},
    {"nested": {"x": 1, "y": [3, 2, 1]}},
    {"floats": [1.0000000000002, 3.141592653589793, 2.718281828459045]},
    {"dt": datetime(2025, 9, 27, 12, 0, tzinfo=timezone.utc)},
    {"date": date(2025, 9, 27)},
    {"enum": C.A},
    {"path": Path("alpha/beta.txt")},
]


def test_light_equivalence_hash_and_canonical() -> None:
    for obj in CORPUS:
        full_canon = canonical_json(obj)
        light_canon = canonical_json_light(obj)
        assert (
            full_canon == light_canon
        ), f"canonical mismatch for {obj!r}\nfull={full_canon}\nlight={light_canon}"
        full_hash = hash_canonical(obj)
        light_hash = hash_canonical_light(obj)
        assert full_hash == light_hash, f"hash mismatch for {obj!r}"
