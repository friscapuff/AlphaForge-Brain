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
