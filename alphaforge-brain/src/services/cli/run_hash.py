from __future__ import annotations

import json
from pathlib import Path

import click

from src.models.run_config import RunConfig
from src.services.manifest import collect_artifacts
from src.services.run_hash import compute_run_hash


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.option(
    "--config",
    "config_path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    required=True,
    help="Path to RunConfig JSON file",
)
@click.argument(
    "artifact", nargs=-1, type=click.Path(exists=True, dir_okay=False, path_type=Path)
)
@click.option(
    "--run-id", type=str, required=False, help="Optional run id for printing context"
)
@click.option(
    "--pretty", is_flag=True, help="Pretty-print JSON output including config signature"
)
@click.version_option(message="%(version)s")
@click.option("--quiet", is_flag=True, help="Only print the hash value")
@click.option("--debug", is_flag=True, help="Print debug info to stderr")
@click.pass_context
def main(
    ctx: click.Context,
    config_path: Path,
    artifact: tuple[Path, ...],
    run_id: str | None,
    pretty: bool,
    quiet: bool,
    debug: bool,
) -> None:
    """Compute deterministic run hash from a RunConfig JSON and artifact files.

    Example:
      run-hash --config run_config.json artifacts/equity.csv artifacts/trades.csv
    """
    try:
        cfg_data = json.loads(config_path.read_text(encoding="utf-8"))
        config = RunConfig.model_validate(cfg_data)
    except Exception as e:
        raise click.ClickException(
            f"Failed to load RunConfig from {config_path}: {e}"
        ) from e

    artifacts = collect_artifacts(list(artifact))
    rh = compute_run_hash(config, artifacts)

    if quiet and not pretty:
        click.echo(rh)
        return

    out = {"run_hash": rh}
    if run_id:
        out["run_id"] = run_id
    if pretty:
        out["config_signature"] = config.deterministic_signature()
        out["artifacts"] = [
            {"name": a.name, "path": a.path, "content_hash": a.content_hash}
            for a in artifacts
        ]
        click.echo(json.dumps(out, indent=2))
    else:
        click.echo(json.dumps(out))


if __name__ == "__main__":
    main()
