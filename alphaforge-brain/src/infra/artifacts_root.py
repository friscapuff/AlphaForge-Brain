"""Central artifact root resolution for AlphaForgeB Brain.

Resolution order:
1. Explicit argument (when passed to resolve_artifact_root)
2. Environment variable: ALPHAFORGEB_ARTIFACT_ROOT
3. Default relative path: ./artifacts

This module intentionally lives outside the existing infra.config (config.py) to avoid
name shadowing issues introduced by creating a config package. Keep it standalone.
"""

from __future__ import annotations

import os
from pathlib import Path

_ENV_KEY = "ALPHAFORGEB_ARTIFACT_ROOT"
_DEFAULT = Path("artifacts")


def resolve_artifact_root(explicit: Path | None = None) -> Path:
    if explicit is not None:
        explicit.mkdir(parents=True, exist_ok=True)
        return explicit
    env_val = os.getenv(_ENV_KEY)
    if env_val:
        p = Path(env_val)
        p.mkdir(parents=True, exist_ok=True)
        return p
    _DEFAULT.mkdir(parents=True, exist_ok=True)
    return _DEFAULT


__all__ = ["resolve_artifact_root"]


def run_artifact_dir(run_hash: str) -> Path:
    """Return path to a run's artifact directory (ensured)."""
    base = resolve_artifact_root(None)
    d = base / run_hash
    d.mkdir(parents=True, exist_ok=True)
    return d


def evicted_dir(run_hash: str) -> Path:
    """Directory holding evicted artifacts for a run (physical demotion)."""
    d = run_artifact_dir(run_hash) / ".evicted"
    d.mkdir(parents=True, exist_ok=True)
    return d

__all__.extend(["run_artifact_dir", "evicted_dir"])
