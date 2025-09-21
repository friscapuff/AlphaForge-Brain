"""Aggregate test fixtures.

Expose NVDA canonical fixtures defined under tests/data/conftest.py at the suite root so
integration tests in other directories (e.g., tests/integration) can access them without
package-style relative imports. Pytest auto-discovers this root-level conftest.
"""
import importlib.util
import sys
from pathlib import Path
from types import ModuleType

_data_fixtures = Path(__file__).parent / "data" / "nvda_fixtures.py"
spec = importlib.util.spec_from_file_location("_nvda_data_fixtures", _data_fixtures)
if spec and spec.loader:  # pragma: no cover - import wiring
	module: ModuleType = importlib.util.module_from_spec(spec)
	sys.modules[spec.name] = module
	# exec_module exists on Loader but not typed on GenericLoader union; cast via getattr
	spec.loader.exec_module(module)  # mypy: runtime attribute exists
	for k, v in module.__dict__.items():  # export fixtures
		if not k.startswith("_"):
			globals()[k] = v  # dynamic fixture export; value types vary
