"""Fixture scripts for CI quality gate simulations."""

from __future__ import annotations

from pathlib import Path


def fixture_path(name: str) -> Path:
    """Return absolute path to a fixture script within this package."""

    return Path(__file__).with_suffix("").parent.joinpath(f"{name}.py")


__all__ = ["fixture_path"]
