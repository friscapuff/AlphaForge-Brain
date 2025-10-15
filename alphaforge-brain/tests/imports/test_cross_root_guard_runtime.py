import importlib
import json
import sys
from types import ModuleType

import pytest

from infra.import_guard import (
    CrossRootImportError,
    install_import_guard,
    uninstall_import_guard,
)


@pytest.fixture()
def guard_env(tmp_path, monkeypatch):
    log_path = tmp_path / "import_guard_events.json"
    monkeypatch.setenv("IMPORT_GUARD_LOG_PATH", str(log_path))
    monkeypatch.setenv("ALPHAFORGE_IMPORT_GUARD_DISABLE", "0")
    uninstall_import_guard()
    install_import_guard()
    yield log_path
    uninstall_import_guard()


def test_guard_blocks_alphaforge_mind_import(guard_env):
    log_path = guard_env
    with pytest.raises(CrossRootImportError):
        importlib.import_module("alphaforge_mind.internals")

    events = [
        json.loads(line)
        for line in log_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert events, "Import guard should record blocked attempt"
    assert events[-1]["module"].startswith("alphaforge_mind"), events[-1]


def test_guard_allows_shared_module_imports(guard_env):
    # Install a dummy shared module to simulate allowed utility import.
    module_name = "shared.safe_utils"
    sys.modules[module_name] = ModuleType(module_name)

    # Should not raise since guard only blocks alphaforge_mind modules.
    try:
        importlib.import_module(module_name)
    finally:
        sys.modules.pop(module_name, None)

    log_path = guard_env
    if log_path.exists():
        entries = [
            json.loads(line)
            for line in log_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        blocked_modules = {entry.get("module") for entry in entries}
        assert module_name not in blocked_modules


def test_guard_allows_journaling_prefix(guard_env):
    placeholder_name = "alphaforge_mind.placeholder"
    sys.modules[placeholder_name] = ModuleType(placeholder_name)

    test_module_name = "services.journaling._guard_probe"
    probe_module = ModuleType(test_module_name)
    exec(
        "def load_placeholder():\n    import importlib\n    return importlib.import_module('alphaforge_mind.placeholder')\n",
        probe_module.__dict__,
    )
    sys.modules[test_module_name] = probe_module

    try:
        module = importlib.import_module(test_module_name)
        module.load_placeholder()
    finally:
        sys.modules.pop(placeholder_name, None)
        sys.modules.pop(test_module_name, None)
