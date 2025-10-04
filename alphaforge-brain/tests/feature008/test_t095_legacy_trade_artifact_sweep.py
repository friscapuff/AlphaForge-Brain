from __future__ import annotations

import ast
from pathlib import Path

SRC_ROOT = Path(__file__).resolve().parents[3] / "alphaforge-brain" / "src"


def _iter_py_files(base: Path):
    for p in base.rglob("*.py"):
        # Skip virtualenvs or build caches just in case
        if ".venv" in p.parts or "site-packages" in p.parts:
            continue
        yield p


def test_no_legacy_trade_or_position_models_in_models_package() -> None:
    models_dir = SRC_ROOT / "models"
    assert models_dir.exists(), f"missing models dir: {models_dir}"

    # Enforced: legacy Trade/Position classes must not exist anywhere in models package

    for p in _iter_py_files(models_dir):
        tree = ast.parse(p.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                # Allow canonical models only
                if node.name in {"Trade", "Position"}:
                    raise AssertionError(f"Legacy model '{node.name}' found in {p}")


def test_no_public_exports_of_legacy_trade_position_identifiers() -> None:
    disallowed = {"Trade", "Position"}
    allowed = {"CompletedTrade", "Fill", "PositionState"}
    for p in _iter_py_files(SRC_ROOT):
        tree = ast.parse(p.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            # __all__ = ["..."] analysis
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "__all__":
                        # Gather string names in __all__
                        exported: set[str] = set()
                        if isinstance(node.value, (ast.List, ast.Tuple)):
                            for elt in node.value.elts:
                                if isinstance(elt, ast.Constant) and isinstance(
                                    elt.value, str
                                ):
                                    exported.add(elt.value)
                        # check for disallowed tokens (but ignore allowed canonical names)
                        for name in exported:
                            base = name.split(".")[-1]
                            if base in disallowed and base not in allowed:
                                raise AssertionError(
                                    f"Disallowed legacy export '{name}' found in {p}"
                                )
