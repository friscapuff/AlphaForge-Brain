from __future__ import annotations

from importlib import resources


def load_sql(name: str) -> str:
    """Load SQL text resource from this package by filename (e.g., '001_init.sql')."""
    with resources.files(__package__).joinpath(name).open("r", encoding="utf-8") as f:
        return f.read()


__all__ = ["load_sql"]
