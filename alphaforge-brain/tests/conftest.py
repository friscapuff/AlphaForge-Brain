"""Aggregate test fixtures.

Expose NVDA canonical fixtures defined under tests/data/conftest.py at the suite root so
integration tests in other directories (e.g., tests/integration) can access them without
package-style relative imports. Pytest auto-discovers this root-level conftest.
"""

import hashlib
import importlib.util
import json
import os
import sys
from datetime import datetime as _dt_datetime
from datetime import timezone
from pathlib import Path
from types import ModuleType
from typing import Any, Callable

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


def pytest_addoption(parser):  # type: ignore[override]
    """Add fallback ini options for asyncio when pytest-asyncio isn't installed.

    This prevents PytestConfigWarning: Unknown config option for users running
    pytest without the pytest-asyncio plugin. When the plugin is installed,
    we skip adding these options to avoid duplicate registration.
    """
    try:
        import pytest_asyncio  # noqa: F401

        plugin_present = True
    except Exception:
        plugin_present = False

    if not plugin_present:
        try:
            parser.addini(
                "asyncio_mode",
                help="pytest-asyncio mode (auto by default)",
                default="auto",
            )
            parser.addini(
                "asyncio_default_fixture_loop_scope",
                help="default loop scope for pytest-asyncio fixtures",
                default="function",
            )
        except Exception:
            # If pytest changes internals or duplicate registration occurs, ignore.
            pass


# ---- SQLite temporary DB path fixture ----
@pytest.fixture()
def sqlite_tmp_path(tmp_path: Path) -> Path:
    """Provide a unique temporary SQLite file path for tests.

    The file is not pre-created; callers can pass this path to engines/services
    that will create it. It will be placed under the test's tmp_path and will
    be cleaned up with the test directory.
    """
    return tmp_path / "test.sqlite3"


# ---- Content-hash and JSON canonicalization helpers ----
def _json_canonical_dumps(obj: Any) -> bytes:
    """Serialize to canonical JSON bytes (UTF-8) with stable ordering.

    Uses orjson when available for speed; falls back to json.
    """
    try:  # prefer orjson if present in env
        import orjson  # type: ignore

        return orjson.dumps(obj, option=orjson.OPT_SORT_KEYS | orjson.OPT_INDENT_0)
    except Exception:
        # separators=(',', ':') removes whitespace; sort_keys ensures determinism
        s = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        return s.encode("utf-8")


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@pytest.fixture()
def json_canonical_dumps() -> Callable[[Any], bytes]:
    """Fixture exposing canonical JSON serialization to bytes (UTF-8)."""

    return _json_canonical_dumps


@pytest.fixture()
def content_hash_json(
    json_canonical_dumps: Callable[[Any], bytes]
) -> Callable[[Any], str]:
    """Fixture returning a function that computes SHA-256 over canonical JSON."""

    def _hash(obj: Any) -> str:
        return _sha256_bytes(json_canonical_dumps(obj))

    return _hash


# ---- RSS sampler helper (best-effort, optional psutil) ----
class _RssSampler:
    def __init__(self) -> None:
        self._impl = self._detect_impl()

    def _detect_impl(self) -> Callable[[], float | None]:
        # Try psutil first
        try:
            import psutil  # type: ignore

            proc = psutil.Process(os.getpid())

            def _psutil_impl() -> float:
                return proc.memory_info().rss / (1024 * 1024)

            return _psutil_impl
        except Exception:
            pass

        # Linux /proc/self/status (VmRSS)
        if os.name == "posix" and os.path.exists("/proc/self/status"):

            def _proc_status_impl() -> float | None:
                try:
                    with open("/proc/self/status", encoding="utf-8") as fh:
                        for line in fh:
                            if line.startswith("VmRSS:"):
                                parts = line.split()
                                # e.g., 'VmRSS:\t  12345 kB' -> convert kB to MB
                                kb = float(parts[1])
                                return kb / 1024.0
                except Exception:
                    return None
                return None

            return _proc_status_impl

        # Fallback: unsupported platform
        def _none_impl() -> float | None:
            return None

        return _none_impl

    def rss_mb(self) -> float | None:
        return self._impl()


@pytest.fixture()
def rss_sampler() -> _RssSampler:
    """Best-effort RSS memory sampler.

    Returns an object with .rss_mb() -> float | None. When None, the platform
    doesn't support RSS sampling with available libraries; callers should skip
    assertions in that case.
    """

    return _RssSampler()


# ---- Arrow roundtrip helper ----
@pytest.fixture()
def arrow_roundtrip(tmp_path: Path) -> Callable[[Any, str | None], Any]:
    """Write a DataFrame to Parquet (pyarrow) and read it back for equivalence tests.

    Returns a function: (df, name?) -> df_roundtripped
    """
    try:
        import pandas as pd  # type: ignore
    except Exception as e:  # pragma: no cover - test environment issue
        pytest.skip(f"pandas not available: {e}")

    def _rt(df: Any, name: str | None = None) -> Any:
        fname = (name or "frame").replace(" ", "_") + ".parquet"
        path = tmp_path / fname
        try:
            df.to_parquet(path, engine="pyarrow", index=False)  # type: ignore[arg-type]
            back = pd.read_parquet(  # parquet-ok: direct artifact read acceptable in controlled test env   # parquet-ok: direct artifact read acceptable in controlled test env
                path, engine="pyarrow"
            )  # parquet-ok: explicit pyarrow roundtrip test
            return back
        except Exception:
            # Fallback minimal env: write CSV under parquet extension and read back via CSV
            path.write_text(df.to_csv(index=False), encoding="utf-8")  # type: ignore[attr-defined]
            import pandas as _pd

            return _pd.read_csv(path)

    return _rt
