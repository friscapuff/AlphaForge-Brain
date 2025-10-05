from src.services.permutation import bootstrap_indices, permutation_indices


def test_permutation_invariants_basic(random_seed_fixture):
    perms = permutation_indices(5, trials=3, seed=random_seed_fixture)
    assert len(perms) == 3
    baseline = set(range(5))
    for p in perms:
        assert set(p) == baseline  # no element loss/dup beyond permutation
    # Deterministic: same seed reproduces
    perms2 = permutation_indices(5, trials=3, seed=random_seed_fixture)
    assert perms == perms2
    # Different seed differs (probabilistic; assume low collision risk with small n)
    perms_diff = permutation_indices(5, trials=3, seed=124)
    assert perms_diff != perms


def test_bootstrap_indices_properties():
    boots = bootstrap_indices(4, trials=2, seed=42)
    assert len(boots) == 2
    for sample in boots:
        assert len(sample) == 4
        # Elements are within range
        assert all(0 <= x < 4 for x in sample)
    # Deterministic
    boots2 = bootstrap_indices(4, trials=2, seed=42)
    assert boots == boots2
