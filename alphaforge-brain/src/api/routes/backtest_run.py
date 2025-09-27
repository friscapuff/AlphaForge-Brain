from __future__ import annotations

from typing import Any

from domain.run.create import InMemoryRunRegistry, create_or_get
from domain.schemas.run_config import (
    ExecutionSpec,
    RiskSpec,
    RunConfig,
    StrategySpec,
    ValidationSpec,
)
from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response
from pydantic import BaseModel, Field, field_validator

# NOTE: Existing API style mounts routes at root without explicit version segment.
# Future task may introduce versioned grouping (e.g., /api/v1). For now align with current candles/features patterns.
router = APIRouter(prefix="", tags=["backtest"])  # future: prefix="/api/v1"


class BacktestRunRequestModel(BaseModel):
    # Map to domain RunConfig expectations
    ticker: str = Field(..., min_length=1, max_length=32)
    timeframe: str = Field("1d", description="Timeframe code (e.g., 1m, 1h, 1d)")
    start: str = Field(..., description="Start date YYYY-MM-DD")
    end: str = Field(..., description="End date YYYY-MM-DD")
    strategy_name: str = Field(..., min_length=1, max_length=64)
    strategy_params: dict[str, Any] = Field(default_factory=dict)
    risk_model: str = Field("basic", description="Risk model identifier")
    risk_params: dict[str, Any] = Field(default_factory=dict)
    validation: dict[str, Any] = Field(
        default_factory=lambda: {
            "permutation": None,
            "block_bootstrap": None,
            "monte_carlo": None,
            "walk_forward": None,
        }
    )
    seed: int | None = None

    @field_validator("end")
    @classmethod
    def end_not_before_start(cls, v: str, info):
        # Access previously validated data via info.data
        start = info.data.get("start") if hasattr(info, "data") else None
        if isinstance(start, str) and v < start:
            raise ValueError("end must be >= start")
        return v


class BacktestRunCreateResponse(BaseModel):
    run_id: str
    created: bool


def get_registry(request: Request) -> InMemoryRunRegistry:
    reg = getattr(request.app.state, "registry", None)
    if reg is None:  # pragma: no cover - defensive
        raise HTTPException(status_code=500, detail="registry not initialized")
    assert isinstance(reg, InMemoryRunRegistry)
    return reg


@router.post("/backtest/run", response_model=BacktestRunCreateResponse, status_code=201)
async def create_backtest_run(
    payload: BacktestRunRequestModel,
    response: Response,
    registry: InMemoryRunRegistry = Depends(get_registry),
    x_correlation_id: str | None = Header(default=None, alias="x-correlation-id"),
) -> BacktestRunCreateResponse:
    # Echo correlation id header if provided for observability chain
    if x_correlation_id:
        response.headers["x-correlation-id"] = x_correlation_id

    # Map incoming model to domain RunConfig
    try:
        run_config = RunConfig(
            symbol=payload.ticker,
            timeframe=payload.timeframe,
            start=payload.start,
            end=payload.end,
            strategy=StrategySpec(
                name=payload.strategy_name, params=payload.strategy_params
            ),
            risk=RiskSpec(model=payload.risk_model, params=payload.risk_params),
            execution=ExecutionSpec(),
            validation=ValidationSpec(**payload.validation),
            seed=payload.seed,
        )
    except Exception as e:  # pragma: no cover
        raise HTTPException(status_code=400, detail=f"invalid configuration: {e}")

    run_id, record, created = create_or_get(run_config, registry)
    return BacktestRunCreateResponse(run_id=run_id, created=created)


class BacktestRunStatusResponse(BaseModel):
    run_id: str
    status: str
    created_at: float | None = None


@router.get("/backtests/{run_id}", response_model=BacktestRunStatusResponse)
async def get_backtest_run_status(
    run_id: str, registry: InMemoryRunRegistry = Depends(get_registry)
) -> BacktestRunStatusResponse:  # T104
    rec = registry.get(run_id)
    if rec is None:
        raise HTTPException(status_code=404, detail="run not found")
    # For synchronous baseline all runs are effectively completed immediately.
    status = "completed"
    created_at = rec.get("created_at") if isinstance(rec, dict) else None
    return BacktestRunStatusResponse(
        run_id=run_id, status=status, created_at=created_at
    )
