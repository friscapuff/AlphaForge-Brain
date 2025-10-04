from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
from domain.data.slice import get_candles_slice
from domain.features.engine import build_features
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(prefix="", tags=["features"])  # mounted at root

_DEFAULT_CANDLE_CACHE = Path("cache") / "candles"
_DEFAULT_CANDLE_CACHE.mkdir(parents=True, exist_ok=True)


class FeaturePreviewRequest(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=32)
    start: datetime
    end: datetime
    limit: int = Field(300, ge=1, le=2000)


class FeaturePreviewResponse(BaseModel):
    symbol: str
    count: int
    columns: list[str]
    items: list[dict[str, Any]]


@router.post("/features/preview", response_model=FeaturePreviewResponse)
async def features_preview(req: FeaturePreviewRequest) -> FeaturePreviewResponse:
    if req.end < req.start:
        raise HTTPException(status_code=400, detail="end must be >= start")
    try:
        frame = get_candles_slice(
            symbol=req.symbol,
            start=(
                req.start
                if req.start.tzinfo
                else req.start.replace(tzinfo=timezone.utc)
            ),
            end=req.end if req.end.tzinfo else req.end.replace(tzinfo=timezone.utc),
            provider="local",
            cache_dir=_DEFAULT_CANDLE_CACHE,
            use_cache=False,
        )
    except Exception:
        frame = pd.DataFrame(
            columns=["timestamp", "open", "high", "low", "close", "volume"],
        )

    if frame.empty:
        return FeaturePreviewResponse(symbol=req.symbol, count=0, columns=[], items=[])

    # Tail limit rows (latest)
    frame = frame.tail(req.limit)

    # Build features (no cache; small slice)
    try:
        feat_df = build_features(frame, use_cache=False)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"feature build failed: {e}") from e

    # Return only the last row's features? For preview better to show per-row.
    # Convert to primitive JSON (avoid numpy types)
    records = feat_df.to_dict(orient="records")
    # Downcast timestamps
    for r in records:
        if "timestamp" in r:
            r["timestamp"] = int(pd.Timestamp(r["timestamp"]).timestamp())
    return FeaturePreviewResponse(
        symbol=req.symbol,
        count=len(records),
        columns=list(feat_df.columns),
        items=records,
    )
