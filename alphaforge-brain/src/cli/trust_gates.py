"""Command-line entrypoint for the Trust Gate suite."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

from services.trust_gates.suite_service import (
    TrustGateSuiteService,
    UnknownGateError,
)

DEFAULT_REPORT_DIR = Path("artifacts/trust_gates/reports")


@dataclass(frozen=True)
class TrustGateCLIArgs:
    """Normalized CLI arguments for the trust gate suite."""

    report_dir: Path
    gates: tuple[str, ...]
    tolerance_profile: str | None
    dry_run: bool


class TrustGateCLIError(RuntimeError):
    """Raised when the CLI cannot proceed due to configuration issues."""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="trust-gates",
        description=(
            "Run the AlphaForge Trust Gate suite and emit trust_gate_report artifacts that"
            " document determinism, causality, ingest integrity, and accounting trust gates."
        ),
    )
    parser.add_argument(
        "--only",
        metavar="GATES",
        help=(
            "Comma-separated list of gates to execute (e.g. 'causality,accounting')."
            " Defaults to the full suite mandated in FR-201."
        ),
    )
    parser.add_argument(
        "--report-dir",
        type=Path,
        default=DEFAULT_REPORT_DIR,
        help=(
            "Directory where trust_gate_report artifacts are written."
            " Defaults to artifacts/trust_gates/reports."
        ),
    )
    parser.add_argument(
        "--tolerance-profile",
        metavar="PROFILE",
        help="Override the tolerance profile (e.g. institutional_default).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help=(
            "Resolve configuration and print the execution plan without running gates."
            " Useful for confirming trust_gate_report targets during development."
        ),
    )
    return parser


def parse_args(ns: argparse.Namespace) -> TrustGateCLIArgs:
    gates = tuple(g.strip() for g in (ns.only or "").split(",") if g.strip())
    report_dir = (ns.report_dir or DEFAULT_REPORT_DIR).expanduser()
    if not report_dir.parts:
        raise TrustGateCLIError(
            "Report directory is empty; specify a valid path for trust_gate_report output."
        )
    return TrustGateCLIArgs(
        report_dir=report_dir,
        gates=gates,
        tolerance_profile=ns.tolerance_profile,
        dry_run=bool(ns.dry_run),
    )


def _normalized_gate_subset(gates: Iterable[str]) -> tuple[str, ...]:
    return tuple(gate for gate in gates if gate)


def execute(args: TrustGateCLIArgs) -> int:
    service = TrustGateSuiteService(
        report_dir=args.report_dir,
        tolerance_profile=args.tolerance_profile,
    )

    subset = _normalized_gate_subset(args.gates)

    if not args.dry_run:
        args.report_dir.mkdir(parents=True, exist_ok=True)

    try:
        summary = service.run(
            only=subset or None,
            dry_run=args.dry_run,
        )
    except (
        UnknownGateError
    ) as exc:  # pragma: no cover - validated via CLI contract tests
        raise TrustGateCLIError(str(exc)) from exc

    print(json.dumps(summary.as_dict(), indent=2), file=sys.stdout)

    if summary.status == "dry-run":
        return 0

    if summary.status != "pass":
        failing = (
            ", ".join(result.name for result in summary.failing_gates()) or "unknown"
        )
        raise TrustGateCLIError(f"Trust gate suite failed: {failing}")

    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    try:
        ns = parser.parse_args(argv)
        args = parse_args(ns)
        return execute(args)
    except TrustGateCLIError as exc:
        parser.exit(status=1, message=f"trust-gates: {exc}\n")


if __name__ == "__main__":  # pragma: no cover - exercised via subprocess in tests
    sys.exit(main())
