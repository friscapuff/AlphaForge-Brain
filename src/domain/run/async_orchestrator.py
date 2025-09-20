"""Asynchronous orchestrator emitting staged progress events for SSE.

Stages (mirrors planned state machine):
 1. init
 2. data_loading
 3. feature_compute
 4. strategy
 5. risk_sizing
 6. execution
 7. metrics
 8. validation
 9. artifacts
 10. completed

Each stage emits a callback with payload {"stage": <name>, "index": i, "total": N, "progress": i/N}.
When complete a final callback with type 'completed' is emitted containing summary + p_values.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any, Callable

import domain.indicators.sma  # noqa: F401  (ensure registration)
from domain.execution.simulator import simulate
from domain.execution.state import build_state
from domain.risk.engine import apply_risk
from domain.run.event_buffer import get_global_buffer
from domain.schemas.run_config import RunConfig
from domain.strategy.runner import run_strategy
from domain.validation.runner import run_all as validation_run_all

Callback = Callable[[str, dict[str, Any]], None]


STAGES = [
    "init",
    "data_loading",
    "feature_compute",
    "strategy",
    "risk_sizing",
    "execution",
    "metrics",
    "validation",
    "artifacts",
    "completed",
]


@dataclass
class AsyncOrchestrator:
    config: RunConfig
    seed: int | None = None
    _callbacks: list[Callback] = field(default_factory=list)
    _cancel_requested: bool = False
    _result: dict[str, Any] | None = None

    def on(self, cb: Callback) -> None:
        self._callbacks.append(cb)

    def _emit(self, type_: str, payload: dict[str, Any]) -> None:
        # Fire callbacks
        for cb in list(self._callbacks):
            try:
                cb(type_, payload)
            except Exception:  # pragma: no cover - defensive
                pass
        # Also append into global buffer if run_hash known (config hash will be computed externally; here we use id(config) surrogate)
        # Actual run hash not yet known here; the caller (create_or_get) knows final run hash. We allow injection via attribute.
        run_hash = getattr(self, "run_hash", None)
        if run_hash:
            buf = get_global_buffer(run_hash)
            buf.append(type_, payload)

    def cancel(self) -> None:
        self._cancel_requested = True

    async def run(self) -> dict[str, Any]:
        total = len(STAGES)
        # INIT
        self._emit("stage", {"stage": STAGES[0], "index": 1, "total": total, "progress": 1 / total})
        await asyncio.sleep(0)  # yield
        if self._cancel_requested:
            return self._cancel()
        # DATA LOADING (synthetic candles)
        from datetime import timezone

        import pandas as pd
        minutes = 180  # shorter synthetic for async path
        base = pd.Timestamp(self.config.start, tz=timezone.utc) if isinstance(self.config.start, str) else self.config.start
        price = 100.0
        rows = []
        for i in range(minutes):
            price += (1 if i % 30 < 15 else -1) * 0.4
            ts = base + pd.Timedelta(minutes=i)
            rows.append({
                "timestamp": ts,
                "open": price,
                "high": price + 0.2,
                "low": price - 0.2,
                "close": price,
                "volume": 1000 + i,
            })
        candles = pd.DataFrame(rows)
        self._emit("stage", {"stage": STAGES[1], "index": 2, "total": total, "progress": 2 / total})
        await asyncio.sleep(0)
        if self._cancel_requested:
            return self._cancel()
        # FEATURE COMPUTE placeholder (indicators already computed inside strategy runner today)
        self._emit("stage", {"stage": STAGES[2], "index": 3, "total": total, "progress": 3 / total})
        await asyncio.sleep(0)
        if self._cancel_requested:
            return self._cancel()
        # STRATEGY
        signals = run_strategy(self.config, candles, candle_hash="async_orch")
        self._emit("stage", {"stage": STAGES[3], "index": 4, "total": total, "progress": 4 / total})
        await asyncio.sleep(0)
        if self._cancel_requested:
            return self._cancel()
        # RISK SIZING
        sized = apply_risk(self.config, signals)
        self._emit("stage", {"stage": STAGES[4], "index": 5, "total": total, "progress": 5 / total})
        await asyncio.sleep(0)
        if self._cancel_requested:
            return self._cancel()
        # EXECUTION
        fills, positions = simulate(self.config, sized, flatten_end=True)
        self._emit("stage", {"stage": STAGES[5], "index": 6, "total": total, "progress": 6 / total})
        await asyncio.sleep(0)
        if self._cancel_requested:
            return self._cancel()
        # METRICS
        trades, summary = build_state(fills, positions)
        self._emit("stage", {"stage": STAGES[6], "index": 7, "total": total, "progress": 7 / total, "trade_count": summary.get("trade_count")})
        await asyncio.sleep(0)
        if self._cancel_requested:
            return self._cancel()
        # VALIDATION
        val_cfg = self.config.validation.model_dump(mode="python") if hasattr(self.config, "validation") else {}
        validation = validation_run_all(trades, None, seed=self.seed, config=val_cfg)
        self._emit("stage", {"stage": STAGES[7], "index": 8, "total": total, "progress": 8 / total})
        await asyncio.sleep(0)
        if self._cancel_requested:
            return self._cancel()
        # ARTIFACTS (written externally after completion; we just announce stage)
        self._emit("stage", {"stage": STAGES[8], "index": 9, "total": total, "progress": 9 / total})
        await asyncio.sleep(0)
        # COMPLETE
        result: dict[str, Any] = {
            "config": self.config.model_dump(),
            "trades": trades,
            "summary": summary,
            "validation": validation,
        }
        self._result = result
        self._emit(
            "completed",
            {
                "stage": STAGES[9],
                "index": 10,
                "total": total,
                "progress": 1.0,
                "p_values": {
                    "perm": validation["permutation"].get("p_value"),
                    "bb": validation["block_bootstrap"].get("p_value"),
                    "mc": validation["monte_carlo_slippage"].get("p_value"),
                },
                "trade_count": summary.get("trade_count"),
            },
        )
        return result

    def _cancel(self) -> dict[str, Any]:
        self._emit("cancelled", {"progress": 0})
        self._result = {"cancelled": True}
        return self._result


async def orchestrate_async(
    config: RunConfig,
    seed: int | None = None,
    *,
    callbacks: list[Callback] | None = None,
) -> dict[str, Any]:
    orch = AsyncOrchestrator(config, seed=seed)
    for cb in callbacks or []:
        orch.on(cb)
    return await orch.run()

__all__ = ["AsyncOrchestrator", "orchestrate_async"]