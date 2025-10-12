from __future__ import annotations

import importlib.util
import json
import os
import sys
from contextlib import contextmanager
from pathlib import Path
from types import ModuleType
from typing import Iterator


@contextmanager
def pushd(path: Path) -> Iterator[None]:
    previous = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(previous)


def load_verifier(script_path: Path) -> ModuleType:
    module_name = "scripts.contracts.verify_frontend_contract"
    spec = importlib.util.spec_from_file_location(module_name, script_path)
    if spec is None or spec.loader is None:  # pragma: no cover - defensive
        raise RuntimeError(f"Unable to load verifier module from {script_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def test_frontend_contract_verifier_produces_artifact(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    spec_path = repo_root / "openapi.deref.json"
    assert spec_path.exists(), "openapi.deref.json missing"

    out_path = tmp_path / "frontend_contract.json"
    verifier = load_verifier(
        repo_root / "scripts" / "contracts" / "verify_frontend_contract.py"
    )

    with pushd(repo_root):
        exit_code = verifier.main(
            [
                "--spec",
                str(spec_path),
                "--baseline-file",
                str(spec_path),
                "--out",
                str(out_path),
            ]
        )

    assert exit_code == 0
    assert out_path.exists()

    payload = json.loads(out_path.read_text(encoding="utf-8"))
    assert payload["status"] == "clean"
    assert payload["diff"]["paths"] == {"added": [], "removed": [], "changed": []}
    assert payload["spec_sha256"]
    assert payload["baseline_sha256"]
    assert payload["baseline"]["type"] == "file"
    assert payload["generated_at"].endswith("Z")
