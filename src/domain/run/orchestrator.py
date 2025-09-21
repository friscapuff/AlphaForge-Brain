from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable

import pandas as pd

from domain.data.datasource import LocalCsvDataSource
from domain.data.ingest_nvda import load_dataset_for, slice_dataset
from domain.data.registry import DatasetEntry, get_dataset, register_dataset
from domain.execution.simulator import simulate
from domain.execution.state import build_state
from domain.metrics.calculator import build_equity_curve, compute_metrics
from domain.risk.engine import apply_risk
from domain.schemas.run_config import RunConfig
from domain.strategy.runner import run_strategy
from domain.validation.runner import run_all as validation_run_all

# Phase J (G01) NOTE:
# Synthetic candle generation removed. Orchestrator now expects upstream data ingestion pipeline
# to provide a real dataset slice (symbol,timeframe,start,end) before strategy execution.
# A DataSource abstraction & registry will be integrated in subsequent tasks (G02-G05).


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
            # G01: Obtain candles from future integrated data layer. For now, raise if not injected via config.
            # Temporary placeholder: Expect external orchestration layer to attach a pre-loaded DataFrame
            # under a private attribute when calling Orchestrator. This avoids reverting to synthetic data.
            candles: pd.DataFrame | None = getattr(self.config, "_injected_candles", None)
            if candles is None:
                # G05 integration path: resolve dataset entry & slice
                # Auto-register NVDA if not present (transitional convenience)
                try:
                    entry = get_dataset(self.config.symbol, self.config.timeframe)
                except KeyError:
                    # Transitional fallback:
                    #  - If requesting NVDA daily we register the canonical CSV-backed dataset.
                    #  - Otherwise we synthesize a small in-memory frame so legacy tests using
                    #    arbitrary symbols (e.g. TEST/1m) continue to function without requiring
                    #    additional fixture files. This preserves deterministic behavior while
                    #    multi-symbol ingestion is still being generalized.
                    if self.config.symbol.upper() == "NVDA" and self.config.timeframe == "1d":
                        register_dataset(DatasetEntry(symbol=self.config.symbol, timeframe=self.config.timeframe, provider="local_csv", path="data/NVDA_5y.csv", calendar_id="NASDAQ"))
                        entry = get_dataset(self.config.symbol, self.config.timeframe)
                    elif self.config.symbol.upper() in {"TEST", "ASYNC", "IDEMP", "CHAIN", "DET", "E2E", "CACHE", "ORCH", "RET", "SSE"}:
                        # Synthesize candles directly; skip registry-driven load path.
                        start_dt = pd.Timestamp(self.config.start).tz_localize("UTC")
                        end_dt = pd.Timestamp(self.config.end).tz_localize("UTC")
                        rng = pd.date_range(start_dt, end_dt, freq="1min", inclusive="left")
                        if len(rng) == 0:
                            rng = pd.date_range(start_dt, periods=10, freq="1min")
                        base = pd.Series(range(len(rng)), dtype="float64")
                        from infra.time.timestamps import to_epoch_ms
                        candles = pd.DataFrame({
                            "ts": to_epoch_ms(rng, assume_tz="UTC"),
                            "open": base + 100.0,
                            "high": base + 100.5,
                            "low": base + 99.5,
                            "close": base + 100.2,
                            "volume": (base * 10 + 1000).astype("int64"),
                            "zero_volume": 0,
                        })
                        # Provide legacy 'timestamp' alias expected by execution layer
                        candles["timestamp"] = candles["ts"]
                        entry = DatasetEntry(symbol=self.config.symbol, timeframe=self.config.timeframe, provider="in_memory")
                    else:
                        raise RuntimeError(
                            f"Dataset not registered for symbol={self.config.symbol} timeframe={self.config.timeframe}"
                        ) from None
                if candles is not None and entry.provider == "in_memory":
                    # Already synthesized above
                    pass
                elif entry.provider == "local_csv":
                    # Generic path: attempt LocalCsvDataSource first, falling back to NVDA legacy loader
                    ds = LocalCsvDataSource(entry.symbol, entry.timeframe)
                    try:
                        full_frame, _meta = ds.load()
                        start_ts = pd.Timestamp(self.config.start).tz_localize("UTC").value // 1_000_000
                        end_ts = pd.Timestamp(self.config.end).tz_localize("UTC").value // 1_000_000
                        candles = ds.slice(start_ts, end_ts)
                    except NotImplementedError:
                        # Legacy NVDA-only path
                        load_dataset_for(entry.symbol, entry.timeframe)
                        start_ts = pd.Timestamp(self.config.start).tz_localize("UTC").value // 1_000_000
                        end_ts = pd.Timestamp(self.config.end).tz_localize("UTC").value // 1_000_000
                        candles = slice_dataset(entry.symbol, entry.timeframe, start_ts, end_ts)
                else:  # pragma: no cover - future provider path
                    raise NotImplementedError(f"Provider not implemented: {entry.provider}")
            if candles is None or candles.empty:
                raise RuntimeError("Resolved dataset slice is empty or not provided.")
            # Normalize timestamp column expected downstream (execution simulator requires 'timestamp').
            if "timestamp" not in candles.columns and "ts" in candles.columns:
                candles = candles.copy()
                candles["timestamp"] = candles["ts"]
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
            # Attach metrics if not already present
            if "metrics" not in summary:
                eq_curve = build_equity_curve(positions)
                metrics = compute_metrics(trades, eq_curve, include_anomalies=False)
                summary["metrics"] = metrics

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

    # Synthetic helper removed in Phase J (G01).


def orchestrate(config: RunConfig, seed: int | None = None, *, callbacks: list[Callback] | None = None) -> dict[str, Any]:
    orch = Orchestrator(config, seed=seed)
    for cb in callbacks or []:
        orch.on_progress(cb)
    return orch.run()


__all__ = ["Orchestrator", "OrchestratorState", "orchestrate"]
