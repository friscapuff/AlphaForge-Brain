from __future__ import annotations

import numpy as np
import pandas as pd
from src.domain.validation.monte_carlo import monte_carlo_slippage
from src.infra.utils.hash import hash_canonical


def _trades_fixture(n: int = 50) -> pd.DataFrame:
    # Provide return_pct column so extract_returns picks it up.
    rows = []
    price = 100.0
    prev = price
    for i in range(n):
        price += np.sin(i / 5.0) * 0.1 + 0.05
        ret = (price / prev - 1.0) if i > 0 else 0.0
        rows.append({"timestamp": i, "return_pct": ret})
        prev = price
    return pd.DataFrame(rows)


def test_monte_carlo_reproducibility_same_seed() -> None:
    trades = _trades_fixture()
    r1 = monte_carlo_slippage(
        trades,
        n_iter=128,
        seed=999,
        model="normal",
        params={"mu": 0.00005, "sigma": 0.0001},
    )
    r2 = monte_carlo_slippage(
        trades,
        n_iter=128,
        seed=999,
        model="normal",
        params={"mu": 0.00005, "sigma": 0.0001},
    )
    # Distribution should be identical element-wise
    assert np.array_equal(
        r1["distribution"], r2["distribution"]
    )  # deterministic given seed
    assert r1["observed_metric"] == r2["observed_metric"]
    assert r1["p_value"] == r2["p_value"]


def test_monte_carlo_reproducibility_diff_seed_changes_distribution() -> None:
    trades = _trades_fixture()
    r1 = monte_carlo_slippage(
        trades,
        n_iter=64,
        seed=100,
        model="uniform",
        params={"low": 0.0, "high": 0.0002},
    )
    r2 = monte_carlo_slippage(
        trades,
        n_iter=64,
        seed=200,
        model="uniform",
        params={"low": 0.0, "high": 0.0002},
    )
    # At least one element should differ with different seeds (ensure non-empty)
    assert r1["distribution"].size > 0
    assert not np.array_equal(r1["distribution"], r2["distribution"])


def test_monte_carlo_prefix_stability_increasing_iterations() -> None:
    # Shrinking / prefix stability: increasing n_iter should preserve prefix with same seed & params.
    trades = _trades_fixture()
    base = monte_carlo_slippage(
        trades,
        n_iter=32,
        seed=321,
        model="normal",
        params={"mu": 0.00005, "sigma": 0.0001},
    )
    larger = monte_carlo_slippage(
        trades,
        n_iter=96,
        seed=321,
        model="normal",
        params={"mu": 0.00005, "sigma": 0.0001},
    )
    assert larger["distribution"].shape[0] == 96
    assert np.allclose(
        base["distribution"], larger["distribution"][:32]
    ), "Prefix of larger run diverged (non-deterministic RNG sequence)"


def test_monte_carlo_snapshot_hash_stability() -> None:
    trades = _trades_fixture()
    result = monte_carlo_slippage(
        trades,
        n_iter=64,
        seed=555,
        model="normal",
        params={"mu": 0.00005, "sigma": 0.0001},
    )
    # Snapshot: hash distribution length + first 5 values rounded + observed metric & p-value
    dist = result["distribution"]
    snapshot = {
        "n": int(dist.size),
        "head": [float(f"{v:.6g}") for v in dist[:5]],
        "observed": float(f"{result['observed_metric']:.6g}"),
        "p": float(f"{result['p_value']:.6g}"),
    }
    snap_hash = hash_canonical(snapshot)
    # Recompute and compare
    result2 = monte_carlo_slippage(
        trades,
        n_iter=64,
        seed=555,
        model="normal",
        params={"mu": 0.00005, "sigma": 0.0001},
    )
    dist2 = result2["distribution"]
    snapshot2 = {
        "n": int(dist2.size),
        "head": [float(f"{v:.6g}") for v in dist2[:5]],
        "observed": float(f"{result2['observed_metric']:.6g}"),
        "p": float(f"{result2['p_value']:.6g}"),
    }
    assert snap_hash == hash_canonical(
        snapshot2
    ), "Monte Carlo snapshot hash changed unexpectedly"
