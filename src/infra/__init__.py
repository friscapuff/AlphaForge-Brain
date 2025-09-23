"""Infrastructure helpers (db, cache, config, logging, time).

Expose selected subpackages to support older absolute import patterns (e.g.,
`from infra.time.timestamps import to_epoch_ms`).
"""

from importlib import import_module as _import_module  # pragma: no cover - light indirection

try:  # optional exposure; absence should not break other imports
	_import_module("infra.time.timestamps")
except Exception:  # pragma: no cover
	pass

from . import config as config  # explicit re-export for mypy attr-defined satisfaction

__all__ = ["cache", "config", "time"]