from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BRAIN_DIR = ROOT / "alphaforge-brain"
SRC_DIR = BRAIN_DIR / "src"

for candidate in (SRC_DIR, BRAIN_DIR):
    path_str = str(candidate)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

import infra.logging as logging_mod  # noqa: E402


def _safe_add_logger_name(logger, method_name, event_dict):
    name = getattr(logger, "name", None)
    if name is not None:
        event_dict["logger"] = name
    return event_dict


logging_mod.add_logger_name = _safe_add_logger_name

api_app = importlib.import_module("api.app")
app = api_app.app
schema = app.openapi()
Path("zz_artifacts/openapi.generated.json").write_text(
    json.dumps(schema, indent=2), encoding="utf-8"
)
