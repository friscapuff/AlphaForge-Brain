# HADJ‑BB Heuristic and CI Width Policy (Plain Language)

This document explains two important pieces of AlphaForge Brain’s validation system in simple terms: the HADJ‑BB heuristic and the CI width policy.

## 1) What is HADJ‑BB?
HADJ‑BB is a method for choosing the “block length” when we do block bootstrap sampling. Think of block bootstrap as shuffling chunks of historical data to simulate alternate histories while keeping nearby points correlated like real markets.

- Why blocks? Prices close in time tend to be related. Sampling by blocks respects this.
- Why a heuristic? We need a practical rule to pick a reasonable block size from the data itself.

Our heuristic (summarized):
1) Measure how related the series is to itself at different lags (autocorrelation for lag 1 to L)
2) Find the smallest lag where this relatedness becomes small after the first dip
3) Use that as the block size, with a tiny deterministic jitter (+/‑1) to avoid brittle edges
4) If the data is too short or shows very weak relatedness, fall back to simple (IID) sampling

Why this matters: Good block sizes produce realistic simulations and trustworthy confidence intervals (uncertainty ranges).

## 2) CI Width Policy
When we run many bootstrap simulations, we get a distribution of outcomes (for example, returns). The width of the confidence interval (CI) tells us how uncertain the result is. If the CI is very wide, the strategy may be unstable.

Policy in AlphaForge Brain:
- STRICT mode: If any monitored metric’s CI width is above the allowed threshold, the check fails
- WARN mode: The system records a warning but does not fail the check

Why this matters: This gate prevents risky changes from being merged if they make results less stable.

## 3) Determinism and Reproducibility
Both the heuristic and the bootstrap process use fixed random seeds. This means the same inputs produce the same outputs. It helps with fairness and auditing.

## 4) Where Are These Used?
- In local runs: You’ll see validation summaries recorded alongside your results
- In CI (automated checks): The width gate runs as part of the acceptance suite to guard quality

## 5) Practical Tips
- If a CI width gate fails, review recent changes to features, data preprocessing, or strategy parameters
- Check the chosen block length and whether fallback to IID occurred; extreme fallbacks may indicate too little data
- Consider running the validation locally to compare behavior
