"""Command-line interfaces for AlphaForge Brain."""

from __future__ import annotations

from typing import Sequence

import click
from cli.retention.commands import retention as retention_group
from cli.trust_gates import main as trust_gates_main

from infra.import_guard import install_import_guard


@click.group(help="AlphaForge Brain CLI entrypoint")
def cli() -> None:
    """Root CLI command for AlphaForge Brain utilities."""


cli.add_command(retention_group, name="retention")


@cli.command(
    "trust-gates",
    context_settings={"ignore_unknown_options": True},
    add_help_option=False,
)
@click.argument("args", nargs=-1, type=click.UNPROCESSED)
def trust_gates(args: tuple[str, ...]) -> None:
    """Delegate to the trust-gates CLI preserving passthrough arguments."""

    code = trust_gates_main(list(args)) or 0
    if code:
        raise SystemExit(code)


def main(argv: Sequence[str] | None = None) -> int:
    """Console script entry for ``alphaforge-brain``."""

    try:
        install_import_guard()
        cli.main(args=argv, prog_name="alphaforge-brain", standalone_mode=False)
    except SystemExit as exc:  # pragma: no cover - passthrough exit codes
        return int(exc.code or 0)
    except click.ClickException as exc:  # pragma: no cover - interactive errors
        exc.show()
        return 1
    return 0


__all__ = ["cli", "trust_gates", "main", "retention_group"]
