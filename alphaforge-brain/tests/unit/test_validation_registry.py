import pytest
from domain.validation import registry as vr


def test_validation_registry_duplicate_registration_raises(tmp_path):
    # Define two functions dynamically; second should raise
    @vr.validation_test("dup_case")
    def _a():
        return 1

    with pytest.raises(ValueError):

        @vr.validation_test("dup_case")
        def _b():
            return 2


def test_validation_registry_snapshot_is_copy():
    @vr.validation_test("unique_case")
    def _c():
        return 3

    snap = vr.get_validation_registry()
    assert "unique_case" in snap
    snap["unique_case"] = lambda: 99  # mutate snapshot only
    assert vr.get_validation_registry()["unique_case"]() == 3
