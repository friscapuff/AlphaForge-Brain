from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

import numpy as np
import pandas as pd

from infra import orm as _orm


@dataclass(slots=True, frozen=True)
class ExecutionRealismReport:
    """Aggregate execution realism diagnostics for a run."""

    run_hash: str
    status: str
    transaction_cost_bps: float
    market_impact_bps: float
    capacity_ratio: float
    warnings: tuple[str, ...] = field(default_factory=tuple)
    guidance: tuple[str, ...] = field(default_factory=tuple)
    assumptions: Mapping[str, Any] = field(default_factory=dict)
    extra_metadata: Mapping[str, Any] = field(default_factory=dict)

    VALIDATION_TYPE = "execution_realism"

    def to_api_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "status": self.status,
            "transaction_cost_bps": self.transaction_cost_bps,
            "market_impact_bps": self.market_impact_bps,
            "capacity_ratio": self.capacity_ratio,
            "warnings": list(self.warnings),
            "guidance": list(self.guidance),
            "assumptions": dict(self.assumptions),
        }
        if self.extra_metadata:
            payload.update(dict(self.extra_metadata))
        return payload

    def to_manifest_fragment(self) -> dict[str, Any]:
        fragment: dict[str, Any] = {
            "status": self.status,
            "transaction_cost_bps": self.transaction_cost_bps,
            "market_impact_bps": self.market_impact_bps,
            "capacity_ratio": self.capacity_ratio,
            "warnings": list(self.warnings),
        }
        if self.extra_metadata:
            fragment.update(dict(self.extra_metadata))
        return fragment

    def metadata_payload(self) -> dict[str, Any]:
        meta = {
            "status": self.status,
            "transaction_cost_bps": self.transaction_cost_bps,
            "market_impact_bps": self.market_impact_bps,
            "capacity_ratio": self.capacity_ratio,
            "warnings": list(self.warnings),
            "guidance": list(self.guidance),
            "assumptions": dict(self.assumptions),
        }
        if self.extra_metadata:
            meta.update(dict(self.extra_metadata))
        return meta

    def to_orm(self) -> _orm.models.Validation:
        from json import dumps

        return _orm.models.Validation(
            run_hash=self.run_hash,
            validation_type=self.VALIDATION_TYPE,
            realism_status=self.status,
            metadata_json=dumps(self.metadata_payload(), sort_keys=True),
        )

    @classmethod
    def from_orm(cls, row: _orm.models.Validation) -> ExecutionRealismReport:
        from json import loads

        metadata = loads(row.metadata_json or "{}")
        warnings = metadata.get("warnings", [])
        guidance = metadata.get("guidance", [])
        assumptions = metadata.get("assumptions", {})
        return cls(
            run_hash=row.run_hash,
            status=row.realism_status or metadata.get("status", "unknown"),
            transaction_cost_bps=metadata.get("transaction_cost_bps", 0.0),
            market_impact_bps=metadata.get("market_impact_bps", 0.0),
            capacity_ratio=metadata.get("capacity_ratio", 0.0),
            warnings=tuple(str(w) for w in warnings),
            guidance=tuple(str(g) for g in guidance),
            assumptions=dict(assumptions),
            extra_metadata={
                k: v
                for k, v in metadata.items()
                if k
                not in {
                    "warnings",
                    "guidance",
                    "assumptions",
                    "transaction_cost_bps",
                    "market_impact_bps",
                    "capacity_ratio",
                    "status",
                }
            },
        )


__all__ = ["ExecutionRealismReport"]


class ExecutionRealismAnalyzer:
    """Evaluate execution realism overlays for Masters validation."""

    def __init__(self, *, seed: int | None = None) -> None:
        self._rng = np.random.default_rng(seed if seed is not None else 0)

    def evaluate(
        self,
        *,
        fills: pd.DataFrame,
        run_config: Any,
        bars: pd.DataFrame,
        budget_bps: float,
        capacity_limit: float,
        strategy_costs_applied: bool = False,
    ) -> ExecutionRealismReport:
        fills = self._ensure_dataframe(fills)
        budget_bps = float(max(budget_bps, 0.0))
        capacity_limit = float(max(capacity_limit, 0.0))

        total_qty = float(fills["quantity"].abs().sum()) if not fills.empty else 0.0
        adv = float(fills.get("adv", pd.Series([np.nan])).mean())
        adv = max(adv if not np.isnan(adv) else 1.0, 1.0)
        participation = min(total_qty / adv, 2.0)

        base_slippage = float(getattr(run_config.cost, "slippage_bps", 0.0))
        fee_bps = float(getattr(run_config.cost, "fee_bps", 0.0))
        participation_penalty = participation * 40.0
        transaction_cost_bps = base_slippage + fee_bps + participation_penalty

        if strategy_costs_applied:
            transaction_cost_bps *= 0.6

        volatility_proxy = self._volatility_proxy(bars)
        market_impact_bps = (
            max(transaction_cost_bps * 0.5, 5.0) + volatility_proxy * 10.0
        )
        if strategy_costs_applied:
            market_impact_bps *= 0.7

        capacity_ratio = min(participation * (1.0 + volatility_proxy), 2.0)

        warnings: list[str] = []
        guidance: list[str] = []

        if transaction_cost_bps + market_impact_bps > budget_bps:
            warnings.append(
                "Combined transaction costs and market impact exceed configured budget."
            )
            guidance.append(
                "Reduce participation or widen execution schedule to lower cost footprint."
            )
        if capacity_ratio > capacity_limit:
            warnings.append(
                "Capacity ratio breaches configured limit; liquidity may be insufficient."
            )
            guidance.append(
                "Capacity guidance: trim order size or stage execution to remain within limits."
            )

        if not guidance:
            guidance.append(
                "Capacity guidance: maintain current sizing; costs within budgeted tolerance."
            )

        status = self._derive_status(
            transaction_cost_bps + market_impact_bps,
            budget_bps,
            capacity_ratio,
            capacity_limit,
        )

        report = ExecutionRealismReport(
            run_hash="",
            status=status,
            transaction_cost_bps=round(transaction_cost_bps, 3),
            market_impact_bps=round(market_impact_bps, 3),
            capacity_ratio=round(capacity_ratio, 3),
            warnings=tuple(warnings),
            guidance=tuple(guidance),
            assumptions={
                "budget_bps": budget_bps,
                "capacity_limit": capacity_limit,
                "strategy_costs_applied": bool(strategy_costs_applied),
            },
            extra_metadata={
                "volatility_proxy": round(volatility_proxy, 4),
                "participation": round(participation, 4),
                "fills_count": int(len(fills)),
            },
        )
        return report

    @staticmethod
    def _ensure_dataframe(fills: Any) -> pd.DataFrame:
        if isinstance(fills, pd.DataFrame):
            return fills.copy()
        if fills is None:
            return pd.DataFrame(columns=["quantity", "price", "adv"])
        return pd.DataFrame(fills)

    @staticmethod
    def _volatility_proxy(bars: pd.DataFrame) -> float:
        if bars is None or bars.empty:
            return 0.0
        closes = bars.get("close")
        if closes is None:
            return 0.0
        returns = pd.Series(closes).pct_change().dropna()
        if returns.empty:
            return 0.0
        return float(np.clip(np.std(returns), 0.0, 0.05))

    @staticmethod
    def _derive_status(
        total_cost_bps: float,
        budget_bps: float,
        capacity_ratio: float,
        capacity_limit: float,
    ) -> str:
        over_cost = total_cost_bps > budget_bps
        over_capacity = capacity_ratio > capacity_limit
        severe_cost = total_cost_bps > budget_bps * 1.25 if budget_bps > 0 else False
        severe_capacity = (
            capacity_ratio > capacity_limit * 1.25 if capacity_limit > 0 else False
        )
        if severe_cost or severe_capacity:
            return "fail"
        if over_cost or over_capacity:
            return "caution"
        return "pass"


__all__ = ["ExecutionRealismAnalyzer", "ExecutionRealismReport"]
