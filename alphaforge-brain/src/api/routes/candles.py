from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
from domain.data.slice import get_candles_slice
from fastapi import APIRouter, HTTPException, Query

router = APIRouter(prefix="", tags=["candles"])  # root prefix; mounted under app

# Simple deterministic cache directory (can be overridden later via settings)
_DEFAULT_CACHE_DIR = Path("cache") / "candles"
_DEFAULT_CACHE_DIR.mkdir(parents=True, exist_ok=True)

_SYMBOL_Q = Query(..., min_length=1, max_length=32)
_START_Q = Query(..., description="ISO8601 start timestamp (inclusive)")
_END_Q = Query(..., description="ISO8601 end timestamp (inclusive)")
_LIMIT_Q = Query(500, ge=1, le=5000)
_PROVIDER_Q = Query("local", description="Registered provider name")


@router.get("/candles")
async def candles(
    symbol: str = _SYMBOL_Q,
    start: datetime = _START_Q,
    end: datetime = _END_Q,
    limit: int = _LIMIT_Q,
    provider: str = _PROVIDER_Q,
) -> dict[str, Any]:
    if end < start:
        raise HTTPException(status_code=400, detail="end must be >= start")
    try:
        frame = get_candles_slice(
            symbol=symbol,
            start=start if start.tzinfo else start.replace(tzinfo=timezone.utc),
            end=end if end.tzinfo else end.replace(tzinfo=timezone.utc),
            provider=provider,
            cache_dir=_DEFAULT_CACHE_DIR,
            use_cache=False,
        )
    except Exception:
        frame = pd.DataFrame(
            columns=["timestamp", "open", "high", "low", "close", "volume"],
        )

    if frame.empty:
        return {"symbol": symbol, "items": []}

    # Enforce limit (latest rows)
    frame = frame.tail(limit)

    # Return normalized JSON-ready list
    records = frame.to_dict(orient="records")
    # Minimal shape: ts (epoch seconds), o,h,l,c,v
    items = [
        {
            "timestamp": int(pd.Timestamp(r["timestamp"]).timestamp()),
            "open": float(r["open"]),
            "high": float(r["high"]),
            "low": float(r["low"]),
            "close": float(r["close"]),
            "volume": float(r.get("volume", 0.0)),
        }
        for r in records
    ]
    return {"symbol": symbol, "count": len(items), "items": items}
