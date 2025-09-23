from __future__ import annotations

import hashlib
import json
from datetime import date, datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

# Avoid package/module name collision: import config module explicitly
from .. import config as _config_mod  # relative import avoids attr-defined ambiguity for mypy


def get_settings() -> _config_mod.Settings:
    return _config_mod.get_settings()

CANONICAL_SEPARATORS = (",", ":")


def canonical_json(obj: Any) -> str:
    """Return a canonical JSON string with sorted keys and controlled float precision.

    This is critical for deterministic hashing of run configurations and manifests.
    """
    settings = get_settings()

    def _float_truncate(o: Any) -> Any:  # pragma: no cover - deterministic formatting focus
        if isinstance(o, float):
            return float(f"{o:.{settings.canonical_float_precision}g}")
        return o

    def _transform(x: Any) -> Any:
        if isinstance(x, dict):
            return {k: _transform(_float_truncate(v)) for k, v in sorted(x.items())}
        if isinstance(x, list):
            return [_transform(_float_truncate(v)) for v in x]
        # Datetime / date normalization (UTC zulu where applicable) for deterministic hashing
        if isinstance(x, datetime):  # pragma: no cover - simple conversion
            if x.tzinfo is not None:
                try:
                    x_utc = x.astimezone(timezone.utc)
                except Exception:
                    x_utc = x
                return x_utc.replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")
            return x.isoformat()
        if isinstance(x, date):  # pragma: no cover
            return x.isoformat()
        # Path objects -> POSIX string
        if isinstance(x, Path):  # pragma: no cover
            return x.as_posix()
        # Enums -> their value (or name if value not serializable)
        if isinstance(x, Enum):  # pragma: no cover
            try:
                return _transform(x.value)
            except Exception:
                return x.name
        return _float_truncate(x)

    transformed = _transform(obj)
    return json.dumps(transformed, separators=CANONICAL_SEPARATORS, sort_keys=True, ensure_ascii=False)


def sha256_hex(data: bytes) -> str:
    """Return the hex sha256 digest for the given byte sequence."""
    return hashlib.sha256(data).hexdigest()


def sha256_of_text(text: str, encoding: str = "utf-8") -> str:
    """Convenience wrapper for tests to hash arbitrary text deterministically."""
    return sha256_hex(text.encode(encoding))


def hash_canonical(obj: Any) -> str:
    return sha256_hex(canonical_json(obj).encode("utf-8"))


__all__ = ["canonical_json", "hash_canonical", "sha256_hex", "sha256_of_text"]
