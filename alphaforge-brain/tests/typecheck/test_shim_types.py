"""Lightweight mypy invocation for shim files.

Runs mypy programmatically on selected shim modules to ensure they stay type-clean.
Skips if mypy is not installed (non-fatal) to avoid hard dependency in minimal envs.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

SHIM_PATHS = [
    Path("infra/__init__.py"),
    Path("infra/cache/__init__.py"),
    Path("infra/cache/candles.py"),
    Path("infra/cache/features.py"),
    Path("infra/cache/metrics.py"),
]


@pytest.mark.skipif(
    importlib.util.find_spec("mypy") is None, reason="mypy not installed"
)
def test_shim_typecheck():
    from mypy import api as mypy_api  # type: ignore

    args = [str(p) for p in SHIM_PATHS if p.exists()]
    if not args:
        pytest.skip("No shim paths found")
    stdout, stderr, status = mypy_api.run(
        ["--ignore-missing-imports", "--show-error-codes", *args]
    )
    if status != 0:
        print(stdout)
        print(stderr, file=sys.stderr)
    assert status == 0, "Mypy type errors detected in shim files"
