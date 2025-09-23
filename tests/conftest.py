"""Aggregate test fixtures.

Expose NVDA canonical fixtures defined under tests/data/conftest.py at the suite root so
integration tests in other directories (e.g., tests/integration) can access them without
package-style relative imports. Pytest auto-discovers this root-level conftest.
"""
import importlib.util
import sys
from datetime import datetime as _dt_datetime
from datetime import timezone
from pathlib import Path
from types import ModuleType

import pytest

# Ensure repository root is on sys.path so imports like `import src.services...` work.
_repo_root = Path(__file__).parent.parent
_src_dir = _repo_root / "src"
# Prioritize src directory first (shadows any site-packages 'infra' or 'domain' names), then repo root.
for p in (str(_src_dir), str(_repo_root)):
    if p not in sys.path:
        sys.path.insert(0, p)

_data_fixtures = Path(__file__).parent / "data" / "nvda_fixtures.py"
spec = importlib.util.spec_from_file_location("_nvda_data_fixtures", _data_fixtures)
if spec and spec.loader:  # pragma: no cover - import wiring
    try:
        module: ModuleType = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)  # mypy: runtime attribute exists
        for k, v in module.__dict__.items():  # export fixtures
            if not k.startswith("_"):
                globals()[k] = v  # dynamic fixture export; value types vary
    except ModuleNotFoundError as e:  # pragma: no cover - optional dataset deps
        # Allow unit tests that do not require dataset fixtures to proceed.
        sys.stderr.write(f"[conftest] Optional dataset fixtures not loaded: {e}\n")


# ---- Deterministic time fixture ----
@pytest.fixture()
def freeze_time(monkeypatch):
    """Freeze time for modules that imported `datetime` directly.

    Strategy:
    * Create a FrozenDateTime subclass overriding now()/utcnow().
    * Inject it into already-imported project modules that have a module-level
      symbol named `datetime` referencing the original class.
    * Return helper exposing aware frozen instant via .now().

    This avoids attempting to set attributes on the immutable C type
    `datetime.datetime`, which raised TypeError previously.
    """
    frozen = _dt_datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

    class FrozenDateTime(_dt_datetime):  # type: ignore[misc]
        @classmethod
        def now(cls, tz=None):
            if tz is None:
                # Maintain legacy behaviour: naive when tz not provided
                return frozen.replace(tzinfo=None)
            return frozen.astimezone(tz)

        @classmethod
        def utcnow(cls):
            return frozen.replace(tzinfo=None)

    # Target only our project modules (heuristic: path includes repo root or name prefixes)
    project_prefixes = ("src.", "tests.", "infra", "domain", "api")
    for mod_name, mod in list(sys.modules.items()):
        if not mod_name or mod_name.startswith("_frozen"):
            continue
        if not mod_name.startswith(project_prefixes):
            continue
        # Replace module-level datetime symbol if it is the original class.
        existing = getattr(mod, "datetime", None)
        if existing is _dt_datetime:
            try:
                monkeypatch.setattr(mod, "datetime", FrozenDateTime, raising=False)
            except Exception:  # pragma: no cover - defensive
                pass

    class _FrozenHelper:
        def now(self):
            return frozen

    return _FrozenHelper()


@pytest.fixture()
def random_seed_fixture():
    """Central RNG seed initialization for tests relying on random module.

    Ensures permutation tests are reproducible without embedding seed logic everywhere.
    """
    import random
    seed = 1337
    random.seed(seed)
    return seed
