#!/usr/bin/env python3
"""Compute type hint coverage for public API (Profile B policy).

Changes for Profile B:
- Constants (ALL_CAPS) are reported but excluded from pass/fail gating.
- Adds --list-missing to output untyped methods and class attributes for targeted remediation.
- Adds --json-path override and ratchet placeholder hook.
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import sys
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]  # repo root
SRC_ROOT = ROOT / "alphaforge-brain" / "src"
PUBLIC_PACKAGES = ["domain", "services", "api", "infra", "models", "lib"]
ARTIFACT_DIR = ROOT / "zz_artifacts" / "type_hygiene"

FUNC_REQ = float(os.getenv("TYPE_COV_FUNC", "100"))
METHOD_REQ = float(os.getenv("TYPE_COV_METHOD", "100"))
ATTR_REQ = float(os.getenv("TYPE_COV_ATTR", "95"))
CONST_REQ = float(os.getenv("TYPE_COV_CONST", "95"))


@dataclass
class Counts:
    functions_total: int = 0
    functions_typed: int = 0
    methods_total: int = 0
    methods_typed: int = 0
    class_attrs_total: int = 0
    class_attrs_typed: int = 0
    consts_total: int = 0
    consts_typed: int = 0

    def as_dict(self) -> dict:
        return self.__dict__.copy()


def iter_module_files() -> Iterable[Path]:
    for pkg in PUBLIC_PACKAGES:
        base = SRC_ROOT / pkg
        if not base.exists():
            continue
        for path in base.rglob("*.py"):
            # Skip private or dunder modules
            if path.name.startswith("_"):
                continue
            yield path


def is_fully_typed_function(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    # Return annotation required
    if node.returns is None:
        return False

    # All args (posonly, args, kwonly) must have annotation except *args/**kwargs which also must
    # themselves be annotated if present.
    def annotated(arg: ast.arg) -> bool:
        return arg.annotation is not None

    parts: list[ast.arg] = []
    parts.extend(node.args.posonlyargs)
    parts.extend(node.args.args)
    if node.args.vararg:
        parts.append(node.args.vararg)
    parts.extend(node.args.kwonlyargs)
    if node.args.kwarg:
        parts.append(node.args.kwarg)
    # Exclude implicit 'self' / 'cls' from requirement if no annotation (we will count under method coverage completeness instead)
    missing = []
    for _i, p in enumerate(parts):
        if p.arg in {"self", "cls"}:
            continue
        if not annotated(p):
            missing.append(p.arg)
    return not missing


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument(
        "--list-missing", action="store_true", help="List missing methods/attrs"
    )
    p.add_argument("--json-path", type=Path, help="Override output JSON path")
    return p.parse_args()


missing_methods: list[tuple[str, str, int]] = []  # (file, method, line)
missing_attrs: list[tuple[str, str, int]] = []

# Adjust analyze_file to record missing
old_analyze_file = None


def analyze_file(path: Path, counts: Counts) -> None:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except SyntaxError:
        return
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name.startswith("_"):
                continue
            counts.functions_total += 1
            if is_fully_typed_function(node):
                counts.functions_typed += 1
        elif isinstance(node, ast.ClassDef):
            for b in node.body:
                if isinstance(b, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if b.name.startswith("_") and b.name not in {"__init__"}:
                        continue
                    counts.methods_total += 1
                    if is_fully_typed_function(b):
                        counts.methods_typed += 1
                    else:
                        missing_methods.append(
                            (
                                str(path.relative_to(ROOT)),
                                f"{node.name}.{b.name}",
                                b.lineno,
                            )
                        )
                elif isinstance(b, ast.AnnAssign):
                    counts.class_attrs_total += 1
                    if b.annotation is not None:
                        counts.class_attrs_typed += 1
                    else:
                        target = getattr(b.target, "id", "?")
                        missing_attrs.append(
                            (
                                str(path.relative_to(ROOT)),
                                f"{node.name}.{target}",
                                b.lineno,
                            )
                        )
                elif isinstance(b, ast.Assign):
                    for t in b.targets:
                        if isinstance(t, ast.Name):
                            counts.class_attrs_total += 1
                            missing_attrs.append(
                                (
                                    str(path.relative_to(ROOT)),
                                    f"{node.name}.{t.id}",
                                    b.lineno,
                                )
                            )
        elif isinstance(node, ast.AnnAssign):
            # constants tracked but not gated
            if isinstance(node.target, ast.Name) and node.target.id.isupper():
                counts.consts_total += 1
                counts.consts_typed += 1
        elif isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name) and t.id.isupper():
                    counts.consts_total += 1


def main() -> int:
    args = parse_args()
    counts = Counts()
    for file in iter_module_files():
        analyze_file(file, counts)

    def pct(n: int, d: int) -> float:
        return 100.0 if d == 0 else round(n / d * 100.0, 2)

    summary = counts.as_dict()
    summary.update(
        {
            "functions_pct": pct(counts.functions_typed, counts.functions_total),
            "methods_pct": pct(counts.methods_typed, counts.methods_total),
            "class_attrs_pct": pct(counts.class_attrs_typed, counts.class_attrs_total),
            "consts_pct": pct(counts.consts_typed, counts.consts_total),
            "thresholds": {
                "functions": FUNC_REQ,
                "methods": METHOD_REQ,
                "class_attrs": ATTR_REQ,
                "consts": CONST_REQ,
            },
            "profile": "B",
            "constants_excluded_from_gating": True,
        }
    )
    status = {
        "functions": summary["functions_pct"] >= FUNC_REQ,
        "methods": summary["methods_pct"] >= METHOD_REQ,
        "class_attrs": summary["class_attrs_pct"] >= ATTR_REQ,
        # constants intentionally excluded
    }
    summary["passes"] = status
    if args.list_missing:
        summary["missing_methods"] = [
            {"file": f, "symbol": s, "line": ln} for f, s, ln in missing_methods
        ]
        summary["missing_class_attrs"] = [
            {"file": f, "symbol": s, "line": ln} for f, s, ln in missing_attrs
        ]

    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = args.json_path or (ARTIFACT_DIR / "type_hint_coverage.json")
    out_path.write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))

    if all(status.values()):
        return 0
    return 2


if __name__ == "__main__":  # pragma: no cover
    try:
        raise SystemExit(main())
    except Exception as e:
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        raise SystemExit(3) from e
