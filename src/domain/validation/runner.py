from __future__ import annotations

import random
from typing import Any

import pandas as pd

from .block_bootstrap import block_bootstrap
from .monte_carlo import monte_carlo_slippage
from .permutation import permutation_test
from .walk_forward import walk_forward_report


def run_all(
    trades_df: pd.DataFrame,
    positions_df: pd.DataFrame | None = None,
    *,
    seed: int | None = None,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Execute all validation methods and return aggregated dict.

    config keys (optional) with defaults:
      permutation.n (200)
      block_bootstrap.n_iter (300)
      block_bootstrap.block_size (5)
      monte_carlo.n_iter (300)
      monte_carlo.model ("normal")
      monte_carlo.params ({})
      walk_forward.n_folds (4)
    Deterministic with seed controlling sub-method seeds (simple offset scheme).
    """
    config = config or {}
    base_seed = seed if seed is not None else random.randint(1, 1_000_000_000)
    def sub_seed(offset: int) -> int:
        return (base_seed + offset * 9973) % 2_147_483_647

    results: dict[str, Any] = {}
    # Permutation
    perm_cfg = config.get("permutation")
    if perm_cfg is not None:
        perm_n = int(perm_cfg.get("samples") or perm_cfg.get("n") or 200)
        results["permutation"] = permutation_test(trades_df, positions_df, n=perm_n, seed=sub_seed(1))
    else:
        results["permutation"] = {"p_value": None, "distribution": [], "observed": None}
    # Block bootstrap
    bb_cfg = config.get("block_bootstrap")
    if bb_cfg is not None:
        results["block_bootstrap"] = block_bootstrap(
            trades_df,
            positions_df,
            n_iter=int(bb_cfg.get("samples") or bb_cfg.get("n_iter") or 300),
            block_size=int(bb_cfg.get("blocks") or bb_cfg.get("block_size") or 5),
            seed=sub_seed(2),
        )
    else:
        results["block_bootstrap"] = {"p_value": None, "distribution": [], "observed": None}
    # Monte Carlo slippage
    mc_cfg = config.get("monte_carlo")
    if mc_cfg is not None:
        results["monte_carlo_slippage"] = monte_carlo_slippage(
            trades_df,
            positions_df,
            n_iter=int(mc_cfg.get("paths") or mc_cfg.get("n_iter") or 300),
            model=mc_cfg.get("model", "normal"),
            params=mc_cfg.get("params", {}),
            seed=sub_seed(3),
        )
    else:
        results["monte_carlo_slippage"] = {"p_value": None, "distribution": [], "observed": None}
    # Walk-forward
    wf_cfg = config.get("walk_forward")
    if wf_cfg is not None:
        wf_folds = walk_forward_report(
            trades_df,
            positions_df,
            n_folds=int(wf_cfg.get("folds") or wf_cfg.get("n_folds") or 4),
            method=wf_cfg.get("method", "expanding"),
        )
    else:
        wf_folds = []
    results["walk_forward"] = {"folds": wf_folds, "summary": {"n_folds": len(wf_folds)}}
    # Summary top-level convenience metrics
    # e.g., collect p-values or distribution means
    results["summary"] = {
        "permutation_p": results["permutation"].get("p_value"),
        "block_bootstrap_p": results["block_bootstrap"].get("p_value"),
        "monte_carlo_p": results["monte_carlo_slippage"].get("p_value"),
    "walk_forward_folds": len(results["walk_forward"]["folds"]),
    }
    results["seed"] = base_seed
    return results


__all__ = ["run_all"]
