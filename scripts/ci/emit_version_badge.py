"""Emit a JSON badge descriptor for Shields.io static endpoint.

Generates `.artifacts/version_badge.json` of the form:
{
  "schemaVersion": 1,
  "label": "alpha-forge",
  "message": "v0.3.0",
  "color": "blue"
}

CI can upload this as an artifact or push to a `badges/` branch served via GitHub Pages
and referenced in README using:

![Version](https://img.shields.io/endpoint?url=<raw-url-to-version_badge.json>)
"""

from __future__ import annotations

import json
from pathlib import Path

import toml

ROOT = Path(__file__).resolve().parent.parent.parent
PYPROJECT = ROOT / "pyproject.toml"
OUT_DIR = ROOT / ".artifacts"
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT_FILE = OUT_DIR / "version_badge.json"


def read_version() -> str:
    data = toml.loads(PYPROJECT.read_text(encoding="utf-8"))
    return data["tool"]["poetry"]["version"]


def main() -> None:
    version = read_version()
    badge = {
        "schemaVersion": 1,
        "label": "alpha-forge",
        "message": f"v{version}",
        "color": "blue",
    }
    OUT_FILE.write_text(json.dumps(badge, separators=(",", ":")), encoding="utf-8")
    print(f"Wrote badge JSON -> {OUT_FILE}")


if __name__ == "__main__":  # pragma: no cover
    main()
