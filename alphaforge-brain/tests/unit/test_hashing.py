from src.lib.hash_utils import canonical_dumps, run_config_hash, run_hash


def test_canonical_dumps_key_ordering():
    a = {"b": 1, "a": 2}
    b = {"a": 2, "b": 1}
    assert canonical_dumps(a) == canonical_dumps(b)
    # Should not contain whitespace beyond separators
    dumped = canonical_dumps(a)
    assert ": " not in dumped and ", " not in dumped


def test_run_config_hash_stability():
    config1 = {"x": 1, "nested": {"y": [3, 2, 1]}}
    config2 = {"nested": {"y": [3, 2, 1]}, "x": 1}
    h1 = run_config_hash(config1)
    h2 = run_config_hash(config2)
    assert h1 == h2


def test_run_hash_composition_changes():
    base = run_hash("cfg", "data", 6, "v1")
    changed = run_hash("cfg", "data", 6, "v2")
    assert base != changed
    changed_prec = run_hash("cfg", "data", 7, "v1")
    assert base != changed_prec
