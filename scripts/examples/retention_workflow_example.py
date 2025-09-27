from __future__ import annotations

"""Retention workflow example using AlphaForgeMindClient.

Steps:
1. Submit a few runs.
2. Inspect baseline retention metrics.
3. Diff plan with hypothetical tighter keep_last.
4. Apply retention.
5. Attempt cold storage restore for a demoted run.
"""
import os
from pprint import pprint

from client import (
    AlphaForgeMindClient,
)  # assumes PYTHONPATH includes alphaforge-mind/src


def main():
    base_url = os.environ.get("ALPHAFORGE_API", "http://localhost:8000")
    client = AlphaForgeMindClient(base_url)

    # 1. Create runs
    cfg_base = {
        "indicators": [],
        "strategy": {"name": "dual_sma", "params": {"fast": 5, "slow": 20}},
        "risk": {"model": "fixed_fraction", "params": {"fraction": 0.1}},
        "execution": {"mode": "sim"},
        "validation": {},
        "symbol": "NVDA",
        "timeframe": "1d",
        "start": "2024-01-01",
        "end": "2024-02-01",
    }
    run_hashes = []
    for seed in range(7000, 7005):
        cfg = dict(cfg_base)
        cfg["seed"] = seed
        sub = client.submit_run(cfg)
        run_hashes.append(sub.run_hash)
    print("Created runs:", run_hashes)

    # 2. Baseline metrics
    metrics_before = client.get_retention_metrics()
    print("\nBaseline retention metrics:")
    pprint(metrics_before)

    # 3. Plan diff (tighter keep_last = 1)
    diff = client.diff_retention_plan(keep_last=1)
    print("\nPlan diff (keep_last=1):")
    pprint(diff)

    # 4. Apply retention (after updating settings)
    client.update_retention_settings(keep_last=1, top_k_per_strategy=0)
    applied = client.apply_retention()
    print("\nApplied retention:")
    pprint(applied)

    # 5. Attempt restore on first demoted run
    demoted = applied.get("demoted", [])
    if demoted:
        target = demoted[0]
        print(f"\nAttempting restore for {target}...")
        restored = client.restore(target)
        pprint(restored)
    else:
        print("No runs demoted; nothing to restore.")

    # 6. Metrics after
    metrics_after = client.get_retention_metrics()
    print("\nPost-retention metrics:")
    pprint(metrics_after)


if __name__ == "__main__":  # pragma: no cover
    main()
