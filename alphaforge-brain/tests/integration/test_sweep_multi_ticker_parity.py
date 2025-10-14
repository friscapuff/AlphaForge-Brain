from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from domain.run.create import InMemoryRunRegistry
from domain.schemas.run_config import RunConfig
from models.parameter_definition import ParameterCollection
from services.sweeps import execute_sweep
from services.sweeps.orchestrator import SweepTickerSpec
from services.sweeps.repository import load_manifest


def _merge_parameters(
    base: ParameterCollection, overrides: Mapping[str, Mapping[str, Any]] | None
) -> ParameterCollection:
    merged_payload = base.as_payload()
    if overrides:
        for name, payload in overrides.items():
            merged_payload[name] = dict(payload)
    return ParameterCollection.from_raw(merged_payload)


def test_multi_ticker_parity_metrics(
    tmp_path: Path,
    temp_artifacts_root: Path,
    sample_run_config: RunConfig,
    sample_parameter_collection: ParameterCollection,
) -> None:
    registry = InMemoryRunRegistry()
    sweep_id = "sweep-multi"
    tickers = [
        SweepTickerSpec(symbol="DET"),
        SweepTickerSpec(
            symbol="ALT",
            overrides={
                "fast": {"mode": "single", "value": 8},
                "slow": {"mode": "list", "values": [30, 45]},
            },
        ),
    ]

    result = execute_sweep(
        sweep_id=sweep_id,
        base_config=sample_run_config,
        parameters=sample_parameter_collection,
        registry=registry,
        tickers=tickers,
        storage_root=temp_artifacts_root,
        artifacts_base=tmp_path / "runs",
    )

    derived = result.manifest.derived_metrics
    per_ticker_stats = derived["per_ticker_totals"]
    assert set(per_ticker_stats) == {"DET", "ALT"}

    expected_totals: dict[str, int] = {}
    for spec in tickers:
        merged = _merge_parameters(sample_parameter_collection, spec.overrides)
        expected_totals[spec.symbol] = merged.combination_count

    assert derived["total_combinations"] == sum(expected_totals.values())
    assert derived["succeeded_combinations"] == sum(expected_totals.values())
    assert derived["skipped_combinations"] == 0

    combos_by_symbol: dict[str, list[str]] = {}
    for combo in result.manifest.combinations:
        symbol, _ = combo.combination_id.split("::", 1)
        combos_by_symbol.setdefault(symbol, []).append(combo.combination_id)
        assert combo.status.value == "succeeded"
        assert combo.run_hash is not None

    for symbol, expected_total in expected_totals.items():
        assert per_ticker_stats[symbol]["total"] == expected_total
        assert per_ticker_stats[symbol]["succeeded"] == expected_total
        assert per_ticker_stats[symbol]["skipped"] == 0
        assert len(combos_by_symbol[symbol]) == expected_total

    # ensure ticker manifests were written for each symbol
    for symbol, path in result.ticker_manifests.items():
        assert path.exists()
        assert path.parent.name == symbol.upper()

    record = load_manifest(sweep_id, storage_root=temp_artifacts_root)
    assert {ticker.ticker for ticker in record.manifest.tickers} == {"DET", "ALT"}
    for ticker in record.manifest.tickers:
        assert ticker.manifest_path is not None
        assert ticker.cap_status.value == "ok"
        assert ticker.data_quality_status.value == "pass"
