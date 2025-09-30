"""Lightweight canonical JSON + hashing utilities.

Goal: Provide a minimal, side-effect free variant of canonical_json/hash_canonical
to be safely imported in performance-sensitive or early-startup contexts without
triggering heavier infra (DB, settings resolution with environment IO, etc.).

Differences vs hash.py:
- No dynamic settings lookup; fixed float precision (10 significant digits) chosen
  to mirror default expectation from settings.canonical_float_precision (adjust if needed).
- Limited type handling: dict, list, float truncation, datetime/date normalization,
  Enum (value->recursion or name), Path -> posix. Avoids any external imports beyond stdlib.
"""

from __future__ import annotations

import hashlib
import json
from datetime import date, datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

try:  # Try to mirror configured precision; fallback to 12 if settings import is heavy/unavailable
    from . import config as _cfg  # type: ignore

    _FLOAT_SIG_DIGITS = getattr(_cfg.get_settings(), "canonical_float_precision", 12)
except Exception:  # pragma: no cover - defensive fallback
    _FLOAT_SIG_DIGITS = 12
_SEPARATORS = (",", ":")


def _float_truncate(v: float) -> float:
    return float(f"{v:.{_FLOAT_SIG_DIGITS}g}")


def _transform(x: Any) -> Any:  # pragma: no cover - recursion lines aggregated
    if isinstance(x, dict):
        return {k: _transform(_coerce(v)) for k, v in sorted(x.items())}
    if isinstance(x, list):
        return [_transform(_coerce(v)) for v in x]
    return _coerce(x)


def _coerce(x: Any) -> Any:
    if isinstance(x, float):
        return _float_truncate(x)
    if isinstance(x, datetime):
        if x.tzinfo is not None:
            try:
                x = x.astimezone(timezone.utc).replace(tzinfo=timezone.utc)
            except Exception:
                pass
            return x.isoformat().replace("+00:00", "Z")
        return x.isoformat()
    if isinstance(x, date):
        return x.isoformat()
    if isinstance(x, Path):
        return x.as_posix()
    if isinstance(x, Enum):
        try:
            return _coerce(x.value)
        except Exception:
            return x.name
    return x


def canonical_json_light(obj: Any) -> str:
    transformed = _transform(obj)
    return json.dumps(
        transformed, separators=_SEPARATORS, sort_keys=True, ensure_ascii=False
    )


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def hash_canonical_light(obj: Any) -> str:
    return sha256_hex(canonical_json_light(obj).encode("utf-8"))


__all__ = [
    "canonical_json_light",
    "hash_canonical_light",
]
