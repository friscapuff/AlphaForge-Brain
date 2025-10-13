import json
from pathlib import Path

import pytest
from cli.retention.commands import retention
from click.testing import CliRunner


def _write_policy(tmp_path: Path) -> Path:
    policy_path = tmp_path / "policy.yaml"
    policy_path.write_text(
        "\n".join(
            [
                'policy_version: "2025.10.13"',
                "max_runs: 5",
                "per_strategy_top: 2",
                "pin_expiry_days: null",
                "waiver_required: true",
                f"audit_log_path: \"{(tmp_path / 'audit.log').as_posix()}\"",
                f"breach_log_path: \"{(tmp_path / 'breaches.log').as_posix()}\"",
            ]
        ),
        encoding="utf-8",
    )
    return policy_path


@pytest.fixture()
def cli_runner(tmp_path: Path):
    policy_path = _write_policy(tmp_path)
    env = {
        "RETENTION_POLICY_PATH": str(policy_path),
        "RETENTION_PIN_STORE": str(tmp_path / "pins.json"),
        "GOVERNANCE_AUDIT_PATH": str(tmp_path / "governance_audit.log"),
        "ALPHAFORGEB_ARTIFACT_ROOT": str(tmp_path / "artifacts"),
    }
    runner = CliRunner()
    return runner, env


def test_pin_requires_waiver_when_policy_demands(cli_runner):
    runner, env = cli_runner
    result = runner.invoke(retention, ["pin", "--run-hash", "RUN-001"], env=env)
    assert result.exit_code != 0
    assert "waiver" in result.output.lower()


def test_pin_unpin_and_policy_inspect(cli_runner):
    runner, env = cli_runner
    pin_args = [
        "pin",
        "--run-hash",
        "RUN-9001",
        "--waiver-id",
        "W-01",
        "--note",
        "investigation",
    ]
    result = runner.invoke(retention, pin_args, env=env)
    assert result.exit_code == 0

    pins_path = Path(env["RETENTION_PIN_STORE"])
    assert pins_path.exists()
    pins_payload = json.loads(pins_path.read_text(encoding="utf-8"))
    assert "RUN-9001" in pins_payload["pinned"]
    assert pins_payload["pinned"]["RUN-9001"]["waiver_id"] == "W-01"

    audit_path = Path(env["GOVERNANCE_AUDIT_PATH"])
    audit_records = [
        json.loads(line)
        for line in audit_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert audit_records[-1]["message"] == "retention.cli.pin"

    inspect = runner.invoke(retention, ["policy", "inspect"], env=env)
    assert inspect.exit_code == 0
    assert "policy_version" in inspect.output

    unpin = runner.invoke(retention, ["unpin", "--run-hash", "RUN-9001"], env=env)
    assert unpin.exit_code == 0
    pins_payload = json.loads(pins_path.read_text(encoding="utf-8"))
    assert "RUN-9001" not in pins_payload["pinned"]
