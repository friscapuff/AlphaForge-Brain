#!/usr/bin/env python
"""CI helper: verify legacy infra.cache shim parity.

Intended usage in CI pipeline before running full tests:
    python scripts/ci_check_cache_shims.py
Exits non-zero if parity fails.
"""
from __future__ import annotations

import importlib
import inspect
import sys

EXPECTED = {"CandleCache","FeaturesCache","cache_metrics","CacheMetrics","CacheMetricsRecorder"}

legacy = importlib.import_module("infra.cache")
src = importlib.import_module("src.infra.cache")


def public(mod):
    out = set()
    for k, v in vars(mod).items():
        if k.startswith("_"):
            continue
        if inspect.ismodule(v):
            continue
        out.add(k)
    return out

legacy_pub = public(legacy)
src_pub = public(src)
missing_legacy = EXPECTED - legacy_pub
missing_src = EXPECTED - src_pub

if missing_legacy or missing_src:
    print("Shim parity check failed:")
    if missing_legacy:
        print("  Legacy missing:", missing_legacy)
    if missing_src:
        print("  Src missing:", missing_src)
    sys.exit(1)

print("Shim parity OK. Symbols:", sorted(EXPECTED))
