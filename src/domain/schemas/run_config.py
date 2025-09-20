from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, model_validator

from infra.utils.hash import canonical_json, hash_canonical


class IndicatorSpec(BaseModel):
    name: str
    params: dict[str, Any] = Field(default_factory=dict)


class StrategySpec(BaseModel):
    name: str
    params: dict[str, Any] = Field(default_factory=dict)


class RiskSpec(BaseModel):
    model: str
    params: dict[str, Any] = Field(default_factory=dict)


class ExecutionSpec(BaseModel):
    mode: str = "sim"  # future: "live"
    slippage_bps: float = 0.0
    fee_bps: float = 0.0
    borrow_cost_bps: float = 0.0
    # Optional extended slippage model override: {"model":"spread_pct","params":{...}} or participation_rate
    slippage_model: dict[str, Any] | None = None


class ValidationSpec(BaseModel):
    # Allow either simple enable flags (legacy) or parameter dicts provided directly.
    # For baseline we store raw sub-configs; validation runner will interpret presence.
    permutation: dict[str, Any] | None = None
    block_bootstrap: dict[str, Any] | None = None
    monte_carlo: dict[str, Any] | None = None
    walk_forward: dict[str, Any] | None = None


class RunConfig(BaseModel):
    indicators: list[IndicatorSpec] = Field(default_factory=list)
    strategy: StrategySpec
    risk: RiskSpec
    execution: ExecutionSpec = Field(default_factory=ExecutionSpec)
    validation: ValidationSpec = Field(default_factory=ValidationSpec)

    symbol: str
    timeframe: str
    start: str  # ISO date (YYYY-MM-DD)
    end: str    # ISO date
    seed: int | None = None

    @model_validator(mode="after")
    def _validate_strategy_params(self) -> RunConfig:
        # Domain validation example for dual_sma
        if self.strategy.name == "dual_sma":
            fast = self.strategy.params.get("fast")
            slow = self.strategy.params.get("slow")
            if isinstance(fast, int) and isinstance(slow, int) and fast >= slow:
                raise ValueError("dual_sma fast must be < slow")
        return self

    def canonical_dict(self) -> dict[str, Any]:
        # Provide deterministic dict (pydantic already orders fields, but we round-trip canonical JSON to apply float precision rules)
        data = self.model_dump(mode="python")
        # Remove any transient / non-deterministic fields in future here
        return data

    def canonical_hash(self) -> str:
        h: str = hash_canonical(self.canonical_dict())
        return h

    def canonical_json(self) -> str:
        s: str = canonical_json(self.canonical_dict())
        return s


__all__ = [
    "IndicatorSpec",
    "StrategySpec",
    "RiskSpec",
    "ExecutionSpec",
    "ValidationSpec",
    "RunConfig",
]
