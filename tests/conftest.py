"""Aggregate test fixtures.

Expose NVDA canonical fixtures defined under tests/data/conftest.py at the suite root so
integration tests in other directories (e.g., tests/integration) can access them without
package-style relative imports. Pytest auto-discovers this root-level conftest.
"""
import importlib.util
import sys
from pathlib import Path

_data_conftest = Path(__file__).parent / "data" / "conftest.py"
spec = importlib.util.spec_from_file_location("_nvda_data_conftest", _data_conftest)
if spec and spec.loader:  # pragma: no cover - import wiring
	module = importlib.util.module_from_spec(spec)
	sys.modules[spec.name] = module
	spec.loader.exec_module(module)  # type: ignore[attr-defined]
	# Inject exported fixtures (attributes without underscore) into globals so pytest sees them
	for k, v in module.__dict__.items():
		if not k.startswith("_"):
			globals()[k] = v
