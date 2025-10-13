#!/usr/bin/env python3
"""Dataset manifest generator.

Computes DatasetManifest payloads containing SHA256, schema signature, and row counts
for canonical CSV datasets. Designed for use in CI and local workflows to ensure
fixture provenance is tracked via deterministic metadata.
"""

from __future__ import annotations

import argparse
import csv
import functools
import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATASET = ROOT / "alphaforge-brain" / "Data" / "NVDA_5y.csv"


@dataclass(slots=True)
class ColumnSignature:
    name: str
    dtype: str
    nullable: bool


@dataclass(slots=True)
class DatasetManifest:
    dataset_name: str
    path: str
    sha256: str
    schema_signature: list[ColumnSignature]
    row_count: int
    generated_at: str

    def to_payload(self) -> dict[str, object]:
        return {
            "dataset_name": self.dataset_name,
            "path": self.path,
            "sha256": self.sha256,
            "schema_signature": [
                {"name": col.name, "dtype": col.dtype, "nullable": col.nullable}
                for col in self.schema_signature
            ],
            "row_count": self.row_count,
            "generated_at": self.generated_at,
        }


def _classify_value(raw: str | None) -> str:
    if raw is None:
        return "null"
    value = raw.strip()
    if value == "":
        return "null"
    try:
        int(value)
        return "integer"
    except ValueError:
        pass
    try:
        float(value)
        return "float"
    except ValueError:
        return "string"


def _merge_dtype(existing: str, new: str) -> str:
    if existing == "":
        return new
    if new == "null":
        return existing
    if existing == "null":
        return new
    if existing == new:
        return existing
    numeric = {"integer", "float"}
    if existing in numeric and new in numeric:
        return "float"
    return "string"


def _compute_schema_signature(
    rows: Iterable[dict[str, str | None]], headers: list[str]
) -> tuple[list[ColumnSignature], int]:
    dtype_map: dict[str, str] = {header: "" for header in headers}
    nullable_map: dict[str, bool] = {header: False for header in headers}
    total_rows = 0
    for row in rows:
        total_rows += 1
        for header in headers:
            value = row.get(header)
            dtype = _classify_value(value)
            dtype_map[header] = _merge_dtype(dtype_map[header], dtype)
            if dtype == "null":
                nullable_map[header] = True
    if total_rows == 0:
        for header in headers:
            dtype_map[header] = "string"
    signature = [
        ColumnSignature(
            name=header,
            dtype=dtype_map[header] or "string",
            nullable=nullable_map[header],
        )
        for header in headers
    ]
    return signature, total_rows


def _sha256_file(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as fh:
        read_chunk = functools.partial(fh.read, 1024 * 1024)
        for chunk in iter(read_chunk, b""):
            if not chunk:
                break
            hasher.update(chunk)
    return hasher.hexdigest()


def build_manifest(dataset_path: Path) -> DatasetManifest:
    if not dataset_path.exists():
        raise FileNotFoundError(f"Dataset file not found: {dataset_path}")

    sha256 = _sha256_file(dataset_path)
    with dataset_path.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        if reader.fieldnames is None:
            raise ValueError(f"Dataset missing header row: {dataset_path}")
        headers = reader.fieldnames
        schema_signature, row_count = _compute_schema_signature(reader, headers)
    generated_at = datetime.now(timezone.utc).isoformat()
    try:
        relative_path = str(dataset_path.relative_to(ROOT))
    except ValueError:
        relative_path = str(dataset_path.resolve())
    relative_path = relative_path.replace("\\", "/")
    manifest = DatasetManifest(
        dataset_name=dataset_path.stem,
        path=relative_path,
        sha256=sha256,
        schema_signature=schema_signature,
        row_count=row_count,
        generated_at=generated_at,
    )
    return manifest


def write_manifest(manifest: DatasetManifest, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(manifest.to_payload(), indent=2, sort_keys=True), encoding="utf-8"
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate dataset manifests for canonical fixtures"
    )
    parser.add_argument(
        "datasets",
        nargs="*",
        type=Path,
        help="One or more dataset CSV paths. Defaults to NVDA canonical dataset when omitted.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional output path. If omitted and only one dataset is provided, writes to <dataset_parent>/dataset_manifest.json",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    dataset_paths: list[Path] = (
        [path.resolve() for path in args.datasets]
        if args.datasets
        else [DEFAULT_DATASET]
    )
    manifests = [build_manifest(path) for path in dataset_paths]

    if len(manifests) > 1:
        if not args.output:
            raise SystemExit(
                "Provide --output when generating manifests for multiple datasets"
            )
        payload = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "datasets": [manifest.to_payload() for manifest in manifests],
        }
        output_path = args.output.resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8"
        )
        print(f"Wrote aggregated manifest to {output_path}")
        return 0

    manifest = manifests[0]
    output_path = (
        args.output.resolve()
        if args.output
        else (dataset_paths[0].parent / "dataset_manifest.json")
    )
    write_manifest(manifest, output_path)
    print(f"Wrote manifest to {output_path}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
