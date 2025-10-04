"""Hashing utilities for deterministic run & config hashing (FR-015, FR-024, FR-041).

Provides canonical JSON serialization and helper functions to produce stable
hash digests for run configuration and artifacts.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any

CANONICAL_SEPARATORS = (",", ":")


def canonical_dumps(obj: Any) -> str:
    """Return a canonical JSON string with sorted keys & fixed separators.

    ensure_ascii=False to keep UTF-8 stable; no whitespace differences.
    """
    return json.dumps(
        obj, sort_keys=True, separators=CANONICAL_SEPARATORS, ensure_ascii=False
    )


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def file_sha256(path: str | Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def run_config_hash(config: dict[str, Any]) -> str:
    return sha256_text(canonical_dumps(config))


def combined_hash(items: Iterable[str]) -> str:
    h = hashlib.sha256()
    for part in items:
        h.update(part.encode("utf-8"))
    return h.hexdigest()


def run_hash(
    config_hash: str,
    dataset_hash: str,
    float_precision: int,
    feature_registry_version: str,
) -> str:
    return combined_hash(
        [config_hash, dataset_hash, str(float_precision), feature_registry_version]
    )
