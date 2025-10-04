from __future__ import annotations

from pathlib import Path

from domain.run.create import InMemoryRunRegistry, create_or_get
from domain.schemas.run_config import (
    ExecutionSpec,
    IndicatorSpec,
    RiskSpec,
    RunConfig,
    StrategySpec,
    ValidationSpec,
)

DATA_PATH = Path("src/domain/data/NVDA_5y.csv")
BACKUP_PATH = Path("src/domain/data/NVDA_5y.csv.bak")


def _build_config() -> RunConfig:
    return RunConfig(
        symbol="NVDA",
        timeframe="1d",
        start="2024-01-01",
        end="2024-01-05",
        indicators=[
            IndicatorSpec(name="sma", params={"window": 5}),
            IndicatorSpec(name="sma", params={"window": 15}),
        ],
        strategy=StrategySpec(name="dual_sma", params={"fast": 5, "slow": 15}),
        risk=RiskSpec(model="fixed_fraction", params={"fraction": 0.1}),
        execution=ExecutionSpec(),
        validation=ValidationSpec(permutation={"trials": 3}),
        seed=123,
    )


def test_dataset_perturbation_changes_run_hash(tmp_path: Path) -> None:
    if not DATA_PATH.exists():
        # Skip if dataset not present
        return
    # Backup original
    BACKUP_PATH.write_bytes(DATA_PATH.read_bytes())
    try:
        reg = InMemoryRunRegistry()
        cfg = _build_config()
        h1, rec1, created1 = create_or_get(cfg, reg, seed=cfg.seed)
        assert created1
        assert h1 == rec1["hash"]
        # Modify a single price cell (replace first occurrence of a numeric close value)
        text = DATA_PATH.read_text("utf-8").splitlines()
        if len(text) < 2:
            return  # unexpected format
        header = text[0]
        row = text[1].split(",")
        # Assume columns include 'close' after o,h,l per typical schema (timestamp,open,high,low,close,volume,...)
        # Add a tiny perturbation to close value
        try:
            close_idx = header.split(",").index("close")
            orig_close = row[close_idx]
            try:
                val = float(orig_close)
                row[close_idx] = f"{val + 0.01:.2f}"
            except ValueError:
                row[close_idx] = "9999.99"
        except Exception:
            # If schema unexpected, skip
            return
        text[1] = ",".join(row)
        DATA_PATH.write_text("\n".join(text), encoding="utf-8")
        # Second run
        reg2 = InMemoryRunRegistry()
        cfg2 = _build_config()
        h2, _, created2 = create_or_get(cfg2, reg2, seed=cfg2.seed)
        if h1 == h2:
            # Failing assertion informs hashing not including dataset yet
            raise AssertionError(
                "Run hash unchanged after dataset perturbation; expected different hash"
            )
        assert created2
    finally:
        # Restore original file
        if BACKUP_PATH.exists():
            DATA_PATH.write_bytes(BACKUP_PATH.read_bytes())
            BACKUP_PATH.unlink(missing_ok=True)


def test_repeated_run_same_hash(tmp_path: Path) -> None:
    if not DATA_PATH.exists():
        return
    reg = InMemoryRunRegistry()
    cfg = _build_config()
    h1, _, _ = create_or_get(cfg, reg, seed=cfg.seed)
    h2, _, created2 = create_or_get(cfg, reg, seed=cfg.seed)
    assert h1 == h2
    assert not created2  # second call reused
