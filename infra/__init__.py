"""Infrastructure package root (compat shim).

This top-level `infra` package proxies to the implementation under `src/infra` so
imports like `from infra.time.timestamps import to_epoch_ms` succeed even when
test runners or tools prepend the repository root ahead of `src` on `sys.path`.
"""
from __future__ import annotations

import importlib
import sys
from pathlib import Path

_repo_root = Path(__file__).resolve().parent.parent
_src_dir = _repo_root / "src"
if _src_dir.exists() and str(_src_dir) not in sys.path:  # ensure src first for its infra package
	sys.path.insert(0, str(_src_dir))

# Extend package search path to include implementation package under src/infra so
# that submodules (e.g., infra.time.timestamps) are resolvable via this shim.
_this_dir = Path(__file__).resolve().parent
try:
	# Extend package search path for submodule resolution
	_ = __path__  # trigger evaluation for side effect; silences B018
	src_infra = str(_src_dir / "infra")
	if src_infra not in __path__:
		__path__.append(src_infra)
except Exception:  # pragma: no cover - defensive
	pass

# Attempt to import real infra subpackage (idempotent if already loaded)
for _mod in ("infra.time", "infra.cache"):
	try:  # pragma: no cover - environment specific
		importlib.import_module(_mod)
	except Exception:
		pass
__all__: list[str] = []
