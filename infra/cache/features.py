"""Shim forwarding to implementation in src.infra.cache.features.

Ensures legacy imports `infra.cache.features` resolve when test runner inserts
repository root ahead of `src` on sys.path.
"""

from __future__ import annotations

from src.infra.cache.features import *  # noqa: F403
