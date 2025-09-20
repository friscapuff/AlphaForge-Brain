from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable

import pandas as pd

from domain.execution.simulator import simulate
from domain.execution.state import build_state
from domain.risk.engine import apply_risk
from domain.schemas.run_config import RunConfig
from domain.strategy.runner import run_strategy
from domain.validation.runner import run_all as validation_run_all


class OrchestratorState(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    VALIDATING = "VALIDATING"
    COMPLETE = "COMPLETE"
    CANCELLED = "CANCELLED"
    ERROR = "ERROR"


Callback = Callable[[OrchestratorState, dict[str, Any]], None]


@dataclass
class Orchestrator:
    config: RunConfig
    seed: int | None = None
    _state: OrchestratorState = OrchestratorState.PENDING
    _callbacks: list[Callback] = field(default_factory=list)
    _started: bool = False
    _cancel_requested: bool = False
    _result: dict[str, Any] | None = None

    def on_progress(self, cb: Callback) -> None:
        self._callbacks.append(cb)

    def _emit(self, state: OrchestratorState, payload: dict[str, Any] | None = None) -> None:
        for cb in list(self._callbacks):
            try:
                cb(state, payload or {})
            except Exception:
                # Ignore callback errors for baseline implementation
                pass

    @property
    def state(self) -> OrchestratorState:
        return self._state

    def cancel(self) -> None:
        if self._state in {OrchestratorState.COMPLETE, OrchestratorState.CANCELLED, OrchestratorState.ERROR}:
            return
        self._cancel_requested = True

    def run(self) -> dict[str, Any]:
        if self._started:
            return self._result or {}
        self._started = True
        try:
            self._transition(OrchestratorState.RUNNING)
            if self._cancel_requested:
                return self._finish_cancel()
            # Build candles inline (future: provider integration) using timeframe & start/end durations placeholder
            # For deterministic placeholder we create fixed number of synthetic candles (similar to tests generating candles externally)
            candles = self._synthetic_candles()
            # Precompute any function-style indicators (e.g., dual_sma) to align with run_strategy expectations
            # so strategy has required SMA columns when using legacy dual_sma config entries.
            # Derive dual SMA columns expected by strategy if config supplies at least two SMA windows or fast/slow params.
            # Tests post /runs with indicators: [{"name":"sma","params":{"window":5}},{"name":"sma","params":{"window":15}}]
            # and strategy: {"name":"dual_sma","params":{"fast":5,"slow":15}}
            sma_windows: list[int] = []
            for spec in self.config.indicators:
                if spec.name == "sma":
                    w = int(spec.params.get("window", 0))
                    if w > 0:
                        sma_windows.append(w)
            sma_windows = sorted(set(sma_windows))
            if self.config.strategy.name == "dual_sma":
                strat_fast = int(self.config.strategy.params.get("fast", self.config.strategy.params.get("short_window", 10)))
                strat_slow = int(self.config.strategy.params.get("slow", self.config.strategy.params.get("long_window", 50)))
                # If only one SMA indicator window supplied, augment with strategy windows.
                if len(sma_windows) < 2:
                    sma_windows = sorted({*sma_windows, strat_fast, strat_slow})
            if len(sma_windows) >= 2:
                short_w = min(sma_windows)
                long_w = max(sma_windows)
                candles[f"sma_short_{short_w}"] = candles["close"].rolling(window=short_w, min_periods=short_w).mean()
                candles[f"sma_long_{long_w}"] = candles["close"].rolling(window=long_w, min_periods=long_w).mean()
            signals = run_strategy(self.config, candles, candle_hash="orchestrator")
            if self._cancel_requested:
                return self._finish_cancel()
            sized = apply_risk(self.config, signals)
            fills, positions = simulate(self.config, sized, flatten_end=True)
            trades, summary = build_state(fills, positions)

            self._transition(OrchestratorState.VALIDATING, {"trade_count": summary.get("trade_count", 0)})
            if self._cancel_requested:
                return self._finish_cancel()
            # Provide raw validation config dict for parameterization
            val_cfg = self.config.validation.model_dump(mode="python") if hasattr(self.config, "validation") else {}
            validation = validation_run_all(trades, None, seed=self.seed, config=val_cfg)
            result: dict[str, Any] = {
                "config": self.config.model_dump(),
                "trades": trades,
                "summary": summary,
                "validation": validation,  # raw validation with distributions (where provided)
            }
            self._result = result
            self._transition(OrchestratorState.COMPLETE, {"p_values": {
                "perm": validation["permutation"].get("p_value"),
                "bb": validation["block_bootstrap"].get("p_value"),
                "mc": validation["monte_carlo_slippage"].get("p_value"),
            }})
            return result
        except Exception as e:  # pragma: no cover (edge path)
            self._state = OrchestratorState.ERROR
            self._emit(self._state, {"error": str(e)})
            raise

    def _finish_cancel(self) -> dict[str, Any]:
        self._state = OrchestratorState.CANCELLED
        self._emit(self._state, {})
        self._result = {"cancelled": True}
        return self._result

    def _transition(self, new_state: OrchestratorState, payload: dict[str, Any] | None = None) -> None:
        self._state = new_state
        self._emit(new_state, payload)

    def _synthetic_candles(self) -> pd.DataFrame:
        from datetime import timezone

        import pandas as pd
        minutes = 360
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
        return pd.DataFrame(rows)


def orchestrate(config: RunConfig, seed: int | None = None, *, callbacks: list[Callback] | None = None) -> dict[str, Any]:
    orch = Orchestrator(config, seed=seed)
    for cb in callbacks or []:
        orch.on_progress(cb)
    return orch.run()


__all__ = ["Orchestrator", "orchestrate", "OrchestratorState"]
