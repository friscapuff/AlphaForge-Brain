from __future__ import annotations

from lib.hash_utils import canonical_dumps, run_config_hash, run_hash


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
