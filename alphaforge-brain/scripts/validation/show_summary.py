from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Iterable


def _resolve_run_dir(run_id: str, base_path: str | None) -> Path:
    if base_path:
        root = Path(base_path)
    else:
        root = Path(os.getenv("ALPHAFORGEB_ARTIFACT_ROOT", "artifacts"))
    run_dir = root / run_id
    if not run_dir.exists():
        raise FileNotFoundError(f"Run artifacts not found for '{run_id}' under {root}")
    return run_dir


def _load_manifest(run_dir: Path) -> dict[str, Any]:
    manifest_path = run_dir / "manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(
            f"Manifest missing for run '{run_dir.name}' at {manifest_path}"
        )
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:  # pragma: no cover - defensive
        raise RuntimeError(f"Invalid JSON in manifest: {manifest_path}") from exc
    if not isinstance(data, dict):
        raise RuntimeError(
            f"Unexpected manifest shape (expected object): {manifest_path}"
        )
    return data


def _print_heading(title: str) -> None:
    print(title)
    print("=" * len(title))


def _render_modules(modules: dict[str, Any] | None) -> None:
    if not modules:
        print("  (no module metadata)")
        return
    for name, details in modules.items():
        status = details
        extra: list[str] = []
        if isinstance(details, dict):
            enabled = details.get("enabled")
            status = "enabled" if enabled is not False else "disabled"
            if "executed_permutations" in details:
                extra.append(f"executed={details['executed_permutations']}")
            if "mode" in details:
                extra.append(f"mode={details['mode']}")
        print(f"  - {name}: {status}{(' (' + ', '.join(extra) + ')') if extra else ''}")


def _render_segments(segments: Iterable[dict[str, Any]]) -> None:
    printed = False
    for seg in segments:
        if not isinstance(seg, dict):
            continue
        printed = True
        sid = seg.get("segment_id", "?")
        p_val = seg.get("p_value")
        effect = seg.get("effect_size")
        artifact = seg.get("artifact_path")
        fallback = seg.get("fallback_reason")
        parts = [f"p={p_val}", f"effect={effect}"]
        if artifact:
            parts.append(f"artifact={artifact}")
        if fallback:
            parts.append(f"fallback={fallback}")
        print(f"  - {sid}: {', '.join(str(p) for p in parts if p is not None)}")
    if not printed:
        print("  (no permutation segments)")


def _render_bias_adjustments(bias: dict[str, Any] | None) -> None:
    if not bias:
        print("  (no bias adjustment metrics)")
        return
    keys = [
        "observed_sharpe",
        "deflated_sharpe",
        "probabilistic_sharpe",
        "assumed_trials",
        "benchmark_sharpe",
    ]
    for key in keys:
        if key in bias:
            print(f"  - {key.replace('_', ' ').title()}: {bias[key]}")


def _render_cross_validation(cross: dict[str, Any] | None) -> None:
    if not cross:
        print("  (no cross-validation details)")
        return
    mode = cross.get("mode")
    leakage = cross.get("leakage_score")
    artifact = cross.get("folds_artifact") or cross.get("folds_artifact_path")
    print(f"  Mode: {mode}")
    if leakage is not None:
        print(f"  Leakage Score: {leakage}")
    if artifact:
        print(f"  Folds Artifact: {artifact}")


def _render_execution_realism(realism: dict[str, Any] | None) -> None:
    if not realism:
        print("  (no execution realism diagnostics)")
        return
    status = realism.get("status")
    print(f"  Status: {status}")
    tc = realism.get("transaction_cost_bps")
    impact = realism.get("market_impact_bps")
    capacity = realism.get("capacity_ratio")
    if tc is not None:
        print(f"  Transaction Cost (bps): {tc}")
    if impact is not None:
        print(f"  Market Impact (bps): {impact}")
    if capacity is not None:
        print(f"  Capacity Ratio: {capacity}")
    warnings = realism.get("warnings")
    if isinstance(warnings, list) and warnings:
        print("  Warnings:")
        for item in warnings:
            print(f"    - {item}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Print validation summary from run manifest"
    )
    parser.add_argument("--run-id", required=True, help="Run hash / identifier")
    parser.add_argument(
        "--base-path",
        help="Override artifact root (defaults to $ALPHAFORGEB_ARTIFACT_ROOT or ./artifacts)",
    )
    args = parser.parse_args(argv)

    try:
        run_dir = _resolve_run_dir(args.run_id, args.base_path)
        manifest = _load_manifest(run_dir)
    except (FileNotFoundError, RuntimeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    schema_version = manifest.get("validation_schema_version")
    significance = manifest.get("validation_significance")
    config = manifest.get("validation_config")
    validation_manifest = manifest.get("validation_manifest") or {}
    modules = validation_manifest.get("modules") or manifest.get("validation_modules")

    _print_heading(f"Validation Summary · {args.run_id}")
    print(
        f"Schema Version : {schema_version if schema_version is not None else 'unknown'}"
    )
    print(f"Significance   : {significance if significance else 'unknown'}")
    if isinstance(config, dict) and config:
        print("Configuration :")
        for key, value in config.items():
            print(f"  - {key}: {value}")
    print()

    print("Modules:")
    _render_modules(modules if isinstance(modules, dict) else None)
    print()

    perm_summary = {}
    if isinstance(validation_manifest, dict):
        perm_summary = validation_manifest.get("permutation_summary", {}) or {}
    segments = perm_summary.get("segments") if isinstance(perm_summary, dict) else None
    print("Permutation Segments:")
    _render_segments(segments if isinstance(segments, Iterable) else [])
    print()

    bias = (
        validation_manifest.get("sharpe_adjustments")
        if isinstance(validation_manifest, dict)
        else None
    )
    print("Sharpe Adjustments:")
    _render_bias_adjustments(bias if isinstance(bias, dict) else None)
    print()

    cross = (
        validation_manifest.get("cross_validation")
        if isinstance(validation_manifest, dict)
        else None
    )
    print("Cross-Validation:")
    _render_cross_validation(cross if isinstance(cross, dict) else None)
    print()

    realism = (
        validation_manifest.get("execution_realism")
        if isinstance(validation_manifest, dict)
        else None
    )
    print("Execution Realism:")
    _render_execution_realism(realism if isinstance(realism, dict) else None)
    print()

    print("Artifacts:")
    artifacts_list = manifest.get("files")
    printed_artifact = False
    if isinstance(artifacts_list, list):
        for entry in artifacts_list:
            if not isinstance(entry, dict):
                continue
            name = entry.get("name")
            if not isinstance(name, str) or not name.startswith("validation/"):
                continue
            printed_artifact = True
            sha256 = entry.get("sha256")
            size = entry.get("size")
            print(f"  - {name}: sha256={sha256} size={size}")
    if not printed_artifact:
        print("  (no validation artifacts recorded)")

    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry
    raise SystemExit(main())
