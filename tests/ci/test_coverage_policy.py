from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT.parent))

from scripts.ci.write_coverage_policy import write_policy  # type: ignore  # noqa: E402


def _coverage_xml(tmp_path: Path, modules: dict[str, tuple[float, float]]) -> Path:
    parts: list[str] = [
        "<?xml version='1.0' encoding='UTF-8'?>",
        "<coverage branch-rate='1.0' line-rate='1.0' version='6.5'>",
        "  <packages>",
    ]
    for module, (line_rate, branch_rate) in modules.items():
        filename = module.replace(".", "/") + ".py"
        root_module = module.split(".")[0]
        class_name = module.split(".")[-1]
        parts.extend(
            [
                f"    <package name='{root_module}'>",
                "      <classes>",
                (
                    f"        <class name='{class_name}' filename='{filename}' "
                    f"line-rate='{line_rate:.3f}' branch-rate='{branch_rate:.3f}'></class>"
                ),
                "      </classes>",
                "    </package>",
            ]
        )
    parts.extend(["  </packages>", "</coverage>"])
    xml_path = tmp_path / "coverage.xml"
    xml_path.write_text("\n".join(parts), encoding="utf-8")
    return xml_path


def test_write_coverage_policy_happy(tmp_path: Path) -> None:
    modules = {
        "services.equity": (0.96, 0.95),
        "services.execution": (0.99, 0.97),
        "services.metrics": (0.98, 0.96),
        "infra.cold_storage": (0.95, 0.94),
        "infra.time.timestamps": (0.97, 0.95),
        "infra.utils.hash": (0.99, 0.98),
    }
    coverage_xml = _coverage_xml(tmp_path, modules)
    out = tmp_path / "coverage_policy.json"

    write_policy(
        coverage_xml=coverage_xml,
        output=out,
        enforced_by="pytest-local",
    )

    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["target_line"] == 90
    assert payload["target_branch"] == 90
    assert payload["target_function"] == 90
    assert payload["target_integration"] == 90
    assert payload["enforced_by"] == "pytest-local"
    overrides = {item["module"]: item for item in payload["module_overrides"]}
    assert set(overrides) == set(modules)
    for item in overrides.values():
        assert item["min_line"] == 90
        assert item["min_branch"] == 90


def test_write_coverage_policy_missing_module(tmp_path: Path) -> None:
    modules = {
        "services.equity": (0.96, 0.95),
        "services.execution": (0.99, 0.97),
        "services.metrics": (0.98, 0.96),
        # intentionally omit infra.cold_storage
        "infra.time.timestamps": (0.97, 0.95),
        "infra.utils.hash": (0.99, 0.98),
    }
    coverage_xml = _coverage_xml(tmp_path, modules)
    out = tmp_path / "coverage_policy.json"

    with pytest.raises(SystemExit) as exc:
        write_policy(
            coverage_xml=coverage_xml,
            output=out,
            enforced_by="pytest-local",
        )
    assert "infra.cold_storage" in str(exc.value)
