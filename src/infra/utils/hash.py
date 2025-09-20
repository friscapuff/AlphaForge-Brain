from __future__ import annotations

import hashlib
import json
from typing import Any

from infra.config import get_settings

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
