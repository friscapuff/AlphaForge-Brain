"""Versioned market data endpoints (Feature 006 T067).

Implements GET /api/v1/market/candles returning shape matching
`chart-candles.v1.schema.json`:
{
    symbol: str,
    interval: str,
    from: ISO8601 string,
    to: ISO8601 string,
    candles: [ { t: epoch ms, o,h,l,c: float, v: int } ]
}
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pandas as pd
from domain.data.slice import get_candles_slice
from fastapi import APIRouter, HTTPException, Query

router = APIRouter(prefix="/api/v1/market", tags=["market-v1"])  # versioned prefix


_SYMBOL = Query(..., min_length=1, max_length=32)
_INTERVAL = Query(
    "1d", min_length=1, max_length=8, description="Interval code (e.g. 1m,5m,1h,1d)"
)
_FROM = Query(..., description="Start ISO8601 timestamp inclusive")
_TO = Query(..., description="End ISO8601 timestamp inclusive")
_LIMIT = Query(500, ge=1, le=5000)
_PROVIDER = Query("local", description="Provider id")


def _to_epoch_ms(dt: datetime) -> int:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp() * 1000)


@router.get("/candles")
async def get_candles(
    symbol: str = _SYMBOL,
    interval: str = _INTERVAL,
    from_: datetime = _FROM,
    to: datetime = _TO,
    limit: int = _LIMIT,
    provider: str = _PROVIDER,
) -> dict[str, Any]:
    if to < from_:
        raise HTTPException(status_code=400, detail="to must be >= from")
    # Basic interval normalization + validation (T084)
    interval_norm = interval.lower().strip()
    allowed = {"1m", "5m", "15m", "1h", "4h", "1d"}
    if interval_norm not in allowed:
        raise HTTPException(status_code=400, detail="invalid interval")
    import re as _re

    if not _re.fullmatch(r"[A-Za-z0-9_\-]+", symbol):
        raise HTTPException(status_code=400, detail="invalid symbol format")
    try:
        from pathlib import Path as _Path  # local import to keep function scope clean

        frame = get_candles_slice(
            symbol=symbol,
            start=from_ if from_.tzinfo else from_.replace(tzinfo=timezone.utc),
            end=to if to.tzinfo else to.replace(tzinfo=timezone.utc),
            provider=provider,
            cache_dir=_Path(
                "./.cache_market"
            ),  # provide concrete Path to satisfy type checker
            use_cache=False,
        )
    except Exception:
        frame = pd.DataFrame(
            columns=["timestamp", "open", "high", "low", "close", "volume"]
        )  # fallback

    if frame.empty:
        return {
            "symbol": symbol,
            "interval": interval_norm,
            "from": from_.isoformat(),
            "to": to.isoformat(),
            "candles": [],
        }
    # Latest N within requested window
    frame = frame.tail(limit)
    records = frame.to_dict(orient="records")
    candles = [
        {
            "t": _to_epoch_ms(pd.Timestamp(r["timestamp"]).to_pydatetime()),
            "o": float(r["open"]),
            "h": float(r["high"]),
            "l": float(r["low"]),
            "c": float(r["close"]),
            "v": int(r.get("volume", 0) or 0),
        }
        for r in records
    ]
    return {
        "symbol": symbol,
        "interval": interval_norm,
        "from": from_.isoformat(),
        "to": to.isoformat(),
        "candles": candles,
    }


__all__ = ["router"]
