from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import jsonschema
import yaml


@dataclass(slots=True)
class ValidationOutcome:
    path: Path
    schema: Path


class SchemaValidationError(RuntimeError):
    """Raised when a configuration file fails schema validation."""


class ChangeLogValidationError(RuntimeError):
    """Raised when a configuration change lacks a signed change-log entry."""


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _load_yaml(path: Path) -> Any:
    try:
        with path.open("r", encoding="utf-8") as handle:
            return yaml.safe_load(handle) or {}
    except FileNotFoundError as exc:  # pragma: no cover - surfaced in CLI
        raise SchemaValidationError(f"Configuration file not found: {path}") from exc
    except yaml.YAMLError as exc:
        raise SchemaValidationError(f"Unable to parse YAML for {path}: {exc}") from exc


def _load_schema(path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except FileNotFoundError as exc:  # pragma: no cover - surfaced in CLI
        raise SchemaValidationError(f"Schema file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise SchemaValidationError(f"Invalid JSON schema at {path}: {exc}") from exc


def ensure_schema_matches(config_path: Path, schema_path: Path) -> None:
    """Validate a YAML configuration file against a JSON schema definition."""

    payload = _load_yaml(config_path)
    schema = _load_schema(schema_path)

    validator = jsonschema.Draft7Validator(
        schema, format_checker=jsonschema.FormatChecker()
    )
    errors = sorted(validator.iter_errors(payload), key=lambda error: error.path)
    if errors:
        messages = []
        for error in errors:
            location = " / ".join(str(item) for item in error.absolute_path)
            if location:
                messages.append(f"{config_path}: {location}: {error.message}")
            else:
                messages.append(f"{config_path}: {error.message}")
        raise SchemaValidationError("; ".join(messages))


def _normalise_target(target: Path) -> str:
    try:
        relative = target.relative_to(_repo_root())
    except ValueError:
        relative = target
    return relative.as_posix()


def require_signed_change_entry(target: Path, change_log_path: Path) -> None:
    """Ensure a change-log entry references the target file and contains a signature."""

    if not change_log_path.exists():
        raise ChangeLogValidationError(f"Change log not found: {change_log_path}")

    target_token = _normalise_target(target)
    lines = change_log_path.read_text(encoding="utf-8").splitlines()

    hit_indices = [idx for idx, line in enumerate(lines) if target_token in line]
    if not hit_indices:
        raise ChangeLogValidationError(
            f"No change-log entry references '{target_token}' in {change_log_path}"
        )

    for index in hit_indices:
        signature_found = False
        # Scan forwards until blank line or new section heading.
        for cursor in range(index, len(lines)):
            raw = lines[cursor].strip()
            if cursor != index and (
                not raw
                or raw.startswith("## ")
                or raw.startswith("- ")
                and target_token not in raw
            ):
                break
            if "Signed-off-by:" in raw:
                signature_found = True
                break
        if not signature_found:
            raise ChangeLogValidationError(
                f"Change-log entry for '{target_token}' is missing a Signed-off-by line"
            )


def _iter_tolerance_files(directory: Path) -> Iterable[Path]:
    if not directory.exists():
        return []
    return sorted(path for path in directory.glob("*.yaml") if path.is_file())


def _parse_arguments(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate governance configuration files"
    )
    default_root = _repo_root()
    parser.add_argument(
        "--tolerances",
        type=Path,
        default=default_root / "configs" / "trust_gates" / "tolerances",
        help="Directory containing tolerance YAML files",
    )
    parser.add_argument(
        "--retention",
        type=Path,
        default=default_root / "configs" / "retention" / "policy.yaml",
        help="Retention policy YAML file to validate",
    )
    parser.add_argument(
        "--schemas",
        type=Path,
        default=default_root / "configs" / "schemas",
        help="Directory containing JSON schema definitions",
    )
    parser.add_argument(
        "--change-log",
        type=Path,
        default=default_root / "configs" / "CONFIG_CHANGELOG.md",
        help="Change log file that must contain Signed-off-by entries",
    )
    parser.add_argument(
        "--artifact-dir",
        type=Path,
        default=default_root / "zz_artifacts" / "governance",
        help="Optional directory to emit validation summaries",
    )
    return parser.parse_args(argv)


def _record_summary(outcomes: list[ValidationOutcome], artifact_dir: Path) -> None:
    artifact_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "validated": [
            {
                "config": outcome.path.as_posix(),
                "schema": outcome.schema.as_posix(),
            }
            for outcome in outcomes
        ]
    }
    summary_path = artifact_dir / "config_validation_summary.json"
    summary_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    args = _parse_arguments(argv)

    tolerance_schema = args.schemas / "trust_tolerances.schema.json"
    retention_schema = args.schemas / "retention_policy.schema.json"

    outcomes: list[ValidationOutcome] = []

    for path in _iter_tolerance_files(args.tolerances):
        ensure_schema_matches(path, tolerance_schema)
        require_signed_change_entry(path, args.change_log)
        outcomes.append(ValidationOutcome(path=path, schema=tolerance_schema))

    ensure_schema_matches(args.retention, retention_schema)
    require_signed_change_entry(args.retention, args.change_log)
    outcomes.append(ValidationOutcome(path=args.retention, schema=retention_schema))

    _record_summary(outcomes, args.artifact_dir)
    print(
        json.dumps(
            {
                "status": "ok",
                "validated": [item.path.as_posix() for item in outcomes],
            }
        )
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
