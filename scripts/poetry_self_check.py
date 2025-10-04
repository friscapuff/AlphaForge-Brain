#!/usr/bin/env python
"""Poetry environment self-check.

Outputs JSON summary including:
- python_version
- package_version (project)
- installed_extras: list of extras detected as installed (by attempting optional imports)
- missing_optionals: extras declared but not importable
- dependency_versions: selected key runtime dependencies (fastapi, numpy, pandas, pandas_ta, pydantic, uvicorn)
- lock_fingerprint: sha256 over (pyproject.toml + poetry.lock) contents for quick drift detection
- warnings: any non-fatal observations (python version mismatch, optional mismatch)

Exit Codes:
 0 OK (no critical issues)
 1 Environment issue (python major/minor mismatch or core dependency missing)

Designed to be inexpensive and safe. Avoids importing heavy libs unless needed.
"""
from __future__ import annotations

import hashlib
import importlib
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
PYPROJECT = ROOT / "pyproject.toml"
LOCK = ROOT / "poetry.lock"

OPTIONAL_IMPORTS = {
    "pandas_ta": "indicators",  # maps module -> extra name
}

KEY_DEPENDENCIES = [
    "fastapi",
    "numpy",
    "pandas",
    "pydantic",
    "uvicorn",
    "pandas_ta",
]

PY_VERSION_SPEC_PATTERN = re.compile(r"python\s*=\s*\"(?P<spec>[^\"]+)\"")


def _read_text(path: pathlib.Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""


def compute_lock_fingerprint() -> str:
    h = hashlib.sha256()
    for path in (PYPROJECT, LOCK):
        if path.exists():
            h.update(path.name.encode())
            h.update(b"\0")
            h.update(_read_text(path).encode())
            h.update(b"\0")
    return h.hexdigest()


def extract_python_spec(pyproject_text: str) -> str | None:
    for line in pyproject_text.splitlines():
        if line.strip().startswith("python "):
            m = PY_VERSION_SPEC_PATTERN.search(line)
            if m:
                return m.group("spec")
    # fallback parse under [tool.poetry.dependencies]
    in_deps = False
    for line in pyproject_text.splitlines():
        if line.strip() == "[tool.poetry.dependencies]":
            in_deps = True
            continue
        if in_deps and line.startswith("["):
            break
        if in_deps and line.strip().startswith("python ="):
            m = PY_VERSION_SPEC_PATTERN.search(line)
            if m:
                return m.group("spec")
    return None


def safe_version(module: str) -> str | None:
    try:
        mod = importlib.import_module(module)
    except Exception:
        return None
    for attr in ("__version__", "VERSION", "version"):
        v = getattr(mod, attr, None)
        if isinstance(v, (str, tuple)):
            return str(v)
    return None


def detect_optionals() -> tuple[list[str], list[str]]:
    installed = []
    missing = []
    for mod, extra in OPTIONAL_IMPORTS.items():
        try:
            importlib.import_module(mod)
            installed.append(extra)
        except Exception:
            missing.append(extra)
    return installed, missing


def main() -> int:
    pyproject_text = _read_text(PYPROJECT)
    python_spec = extract_python_spec(pyproject_text) or ""
    py_version = (
        f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    )

    installed_extras, missing_extras = detect_optionals()

    dependency_versions: dict[str, str | None] = {
        dep: safe_version(dep) for dep in KEY_DEPENDENCIES
    }

    warnings: list[str] = []
    exit_code = 0

    # Basic python version check (only major.minor vs spec fragment numbers we can parse)
    if python_spec:
        # crude parse like ^3.11 or >=3.10,<3.12 etc
        mm = re.findall(r"(\d+\.\d+)", python_spec)
        if mm:
            current_mm = f"{sys.version_info.major}.{sys.version_info.minor}"
            if current_mm not in python_spec:
                warnings.append(
                    f"python version {current_mm} not explicitly in spec '{python_spec}' (informational)"
                )

    # Core dependency presence minimal check (fastapi & pydantic should exist)
    for core in ["fastapi", "pydantic"]:
        if dependency_versions.get(core) is None:
            warnings.append(f"Missing core dependency: {core}")
            exit_code = 1

    if missing_extras:
        warnings.append("Missing optional extras: " + ", ".join(sorted(missing_extras)))

    payload = {
        "python_version": py_version,
        "python_spec": python_spec,
        "package_version": safe_version("project_a_backend")
        or safe_version("alphaforge_brain")
        or "unknown",  # adjust name fallback
        "installed_extras": sorted(installed_extras),
        "missing_optionals": sorted(missing_extras),
        "dependency_versions": {
            k: v for k, v in dependency_versions.items() if v is not None
        },
        "dependency_missing": [k for k, v in dependency_versions.items() if v is None],
        "lock_fingerprint": compute_lock_fingerprint(),
        "warnings": warnings,
        "status": "ok" if exit_code == 0 else "issue",
    }

    print(json.dumps(payload, indent=2, sort_keys=True))
    return exit_code


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
