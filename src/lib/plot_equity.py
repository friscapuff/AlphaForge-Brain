"""Deterministic equity curve plotting (FR-014, FR-041).

Applies fixed Matplotlib rcParams and produces a single figure with:
- Top: equity curve
- Bottom: drawdown series if provided (else omitted)

Determinism strategies:
- Fixed style parameters (font, dpi, figure size)
- No timestamps in output
- Agg backend (caller responsibility if running in server context)
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # enforce non-interactive
import matplotlib.pyplot as plt
from typing import Any, Protocol

class Axes(Protocol):  # pragma: no cover - minimal protocol for typing
    def plot(self, *args: Any, **kwargs: Any) -> Any: ...
    def set_title(self, *args: Any, **kwargs: Any) -> Any: ...
    def legend(self, *args: Any, **kwargs: Any) -> Any: ...
import pandas as pd

_RC = {
    "figure.figsize": (10, 6),
    "figure.dpi": 100,
    "axes.grid": True,
    "axes.titlesize": 12,
    "axes.labelsize": 10,
    "font.size": 9,
    "legend.fontsize": 9,
    "lines.linewidth": 1.2,
}

_APPLIED = False

def _apply_rc() -> None:
    global _APPLIED
    if _APPLIED:
        return
    for k, v in _RC.items():
        plt.rcParams[k] = v
    _APPLIED = True


def plot_equity(run_hash: str, equity: pd.DataFrame, out_dir: Path) -> Path:
    _apply_rc()
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "plots.png"
    fig, ax_main = plt.subplots(nrows=2 if "drawdown" in equity.columns else 1, ncols=1, sharex=True)
    if isinstance(ax_main, (list, tuple)):
        ax_equity = ax_main[0]
        ax_dd: Axes | None = ax_main[1] if len(ax_main) > 1 else None
    else:
        ax_equity = ax_main
        ax_dd = None
    if "equity" in equity.columns:
        ax_equity.plot(equity.index, equity["equity"], label="equity", color="#1f77b4")
    else:
        # Fallback: first column
        first_col = equity.columns[0]
        ax_equity.plot(equity.index, equity[first_col], label=first_col, color="#1f77b4")
    ax_equity.set_title("Equity Curve")
    ax_equity.legend(loc="upper left")
    if ax_dd is not None and "drawdown" in equity.columns:
        ax_dd.plot(equity.index, equity["drawdown"], label="drawdown", color="#d62728")
        ax_dd.set_title("Drawdown")
        ax_dd.legend(loc="upper left")
    fig.tight_layout()
    fig.savefig(path, format="png")
    plt.close(fig)
    return path

__all__ = ["plot_equity"]
