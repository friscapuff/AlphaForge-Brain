from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping


@dataclass(frozen=True)
class DiffReport:
    added: list[str]
    removed: list[str]
    changed: list[str]

    @classmethod
    def from_maps(
        cls, base: Mapping[str, Any] | None, head: Mapping[str, Any] | None
    ) -> DiffReport:
        base = base or {}
        head = head or {}
        added: list[str] = []
        removed: list[str] = []
        changed: list[str] = []

        base_keys = set(base.keys())
        head_keys = set(head.keys())

        for key in sorted(head_keys - base_keys):
            added.append(key)
        for key in sorted(base_keys - head_keys):
            removed.append(key)
        for key in sorted(base_keys & head_keys):
            if json.dumps(base[key], sort_keys=True) != json.dumps(
                head[key], sort_keys=True
            ):
                changed.append(key)

        return cls(added=added, removed=removed, changed=changed)

    def is_clean(self) -> bool:
        return not (self.added or self.removed or self.changed)

    def to_payload(self) -> dict[str, list[str]]:
        return {
            "added": self.added,
            "removed": self.removed,
            "changed": self.changed,
        }


def sha256_digest(payload: str | bytes) -> str:
    if isinstance(payload, str):
        payload = payload.encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def load_json_file(path: Path) -> tuple[dict[str, Any], str]:
    text = path.read_text(encoding="utf-8")
    data = json.loads(text)
    return data, text


def load_baseline_from_git(path: Path, ref: str) -> tuple[dict[str, Any], str]:
    result = subprocess.run(
        ["git", "show", f"{ref}:{path.as_posix()}"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"Unable to load baseline spec from git ref '{ref}' at '{path}'.\n{result.stderr.strip()}"
        )
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as exc:  # pragma: no cover - defensive
        raise RuntimeError(
            f"Baseline spec at {ref}:{path} is not valid JSON: {exc}"
        ) from exc
    return data, result.stdout


def collect_operations(spec: Mapping[str, Any] | None) -> dict[str, Any]:
    operations: dict[str, Any] = {}
    paths = (spec or {}).get("paths", {})
    for path, methods in paths.items():
        if not isinstance(methods, Mapping):
            continue
        for method, details in methods.items():
            if not isinstance(details, Mapping):
                continue
            key = f"{method.upper()} {path}"
            operations[key] = details
    return operations


def build_diff(
    base_spec: Mapping[str, Any] | None, head_spec: Mapping[str, Any]
) -> dict[str, Any]:
    base_spec = base_spec or {}
    head_spec = head_spec or {}
    ops_diff = DiffReport.from_maps(
        collect_operations(base_spec), collect_operations(head_spec)
    )
    schemas_diff = DiffReport.from_maps(
        (base_spec.get("components", {}) or {}).get("schemas", {}),
        (head_spec.get("components", {}) or {}).get("schemas", {}),
    )
    params_diff = DiffReport.from_maps(
        (base_spec.get("components", {}) or {}).get("parameters", {}),
        (head_spec.get("components", {}) or {}).get("parameters", {}),
    )
    security_diff = DiffReport.from_maps(
        (base_spec.get("components", {}) or {}).get("securitySchemes", {}),
        (head_spec.get("components", {}) or {}).get("securitySchemes", {}),
    )

    return {
        "paths": ops_diff.to_payload(),
        "schemas": schemas_diff.to_payload(),
        "parameters": params_diff.to_payload(),
        "security_schemes": security_diff.to_payload(),
    }


def aggregate_status(diff_payload: Mapping[str, Any]) -> str:
    def iter_changes(section: Mapping[str, Iterable[str]]) -> bool:
        for values in section.values():
            if values:
                return True
        return False

    for key in diff_payload:
        section = diff_payload[key]
        if iter_changes(section):
            return "changed"
    return "clean"


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Verify frontend contract drift against baseline OpenAPI snapshot",
    )
    parser.add_argument(
        "--spec",
        type=Path,
        default=Path("openapi.deref.json"),
        help="Path to the generated OpenAPI spec to verify (defaults to openapi.deref.json)",
    )
    parser.add_argument(
        "--baseline-path",
        type=Path,
        default=None,
        help="Relative path of the baseline spec within the git ref (defaults to --spec path)",
    )
    parser.add_argument(
        "--baseline-ref",
        type=str,
        default="origin/main",
        help="Git ref that contains the canonical baseline spec",
    )
    parser.add_argument(
        "--baseline-file",
        type=Path,
        default=None,
        help="Optional explicit path to a local baseline spec file (bypasses git lookup)",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("zz_artifacts/frontend_contract.json"),
        help="Destination path for the verification artifact",
    )
    parser.add_argument(
        "--allow-diff",
        action="store_true",
        help="Exit successfully even when differences are detected (recorded in artifact)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    repo_root = Path.cwd()
    spec_path = args.spec.resolve()
    if not spec_path.exists():
        raise SystemExit(f"Spec file not found: {spec_path}")

    if args.baseline_path is None:
        try:
            default_rel = spec_path.relative_to(repo_root)
        except ValueError:  # pragma: no cover - defensive
            default_rel = Path(spec_path.name)
        baseline_path_obj = default_rel
    else:
        baseline_path_obj = args.baseline_path
        if baseline_path_obj.is_absolute():
            try:
                baseline_path_obj = baseline_path_obj.relative_to(repo_root)
            except ValueError as exc:
                raise SystemExit(
                    "Baseline path must reside inside the repository root"
                ) from exc

    baseline_path = baseline_path_obj.as_posix()

    head_data, head_text = load_json_file(spec_path)
    head_sha = sha256_digest(head_text)

    baseline_data: dict[str, Any] | None = None
    baseline_text = ""
    baseline_sha: str | None = None
    baseline_source: dict[str, Any]

    if args.baseline_file is not None:
        baseline_file_path = args.baseline_file.resolve()
        if not baseline_file_path.exists():
            raise SystemExit(f"Baseline file not found: {baseline_file_path}")
        baseline_data, baseline_text = load_json_file(baseline_file_path)
        baseline_sha = sha256_digest(baseline_text)
        baseline_source = {
            "type": "file",
            "path": str(baseline_file_path),
        }
    else:
        try:
            baseline_data, baseline_text = load_baseline_from_git(
                Path(baseline_path), args.baseline_ref
            )
            baseline_sha = sha256_digest(baseline_text)
            baseline_source = {
                "type": "git",
                "ref": args.baseline_ref,
                "path": baseline_path,
            }
        except RuntimeError as exc:
            baseline_source = {
                "type": "git",
                "ref": args.baseline_ref,
                "path": baseline_path,
                "error": str(exc),
            }
            baseline_data = None
            baseline_text = ""
            baseline_sha = None

    diff_payload = build_diff(baseline_data, head_data)
    status = aggregate_status(diff_payload)
    if baseline_data is None:
        status = "baseline_missing"

    artifact = {
        "spec_path": str(spec_path),
        "baseline": baseline_source,
        "status": status,
        "spec_sha256": head_sha,
        "baseline_sha256": baseline_sha,
        "diff": diff_payload,
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(artifact, indent=2, sort_keys=True), encoding="utf-8"
    )

    if status == "clean" or args.allow_diff:
        return 0
    return 1


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main())
