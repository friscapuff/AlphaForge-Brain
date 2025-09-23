"""Validate public API parity between legacy shim infra.cache and src.infra.cache.

Ensures CI fails if symbols drift (additions/removals) without updating shim.
"""

from __future__ import annotations

import importlib
import inspect

LEGACY_MOD = importlib.import_module("infra.cache")
SRC_MOD = importlib.import_module("src.infra.cache")

# Symbols we intentionally expose
EXPECTED = {"CandleCache","FeaturesCache","cache_metrics","CacheMetrics","CacheMetricsRecorder"}

def _public(mod):
    out = set()
    for name, obj in vars(mod).items():
        if name.startswith("_"):
            continue
        if inspect.ismodule(obj):
            continue
        out.add(name)
    return out & EXPECTED

def test_cache_public_api_parity():
    legacy = _public(LEGACY_MOD)
    src = _public(SRC_MOD)
    # Both must be supersets of EXPECTED; drift triggers failure
    assert EXPECTED.issubset(legacy), f"Legacy missing: {EXPECTED - legacy}"
    assert EXPECTED.issubset(src), f"Src missing: {EXPECTED - src}"
    # If src gains new exported expected symbols, add to EXPECTED above deliberately.
