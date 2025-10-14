from __future__ import annotations

from typing import Any, Mapping, Sequence

from api.error_codes import to_kebab
from api.errors_contract import ErrorDetail, ErrorResponse

_OPTIMIZATION_SWEEP_LIMIT_CODE = "OPTIMIZATION_SWEEP_LIMIT_HIT"


def sweep_limit_hit_error(
    *,
    cap: int,
    requested: int,
    tickers: Sequence[str] | None = None,
    docs_url: str | None = None,
) -> Mapping[str, Any]:
    """Build an ErrorResponse payload for sweep cap violations."""

    normalized_cap = max(cap, 0)
    normalized_requested = max(requested, 0)
    ticker_list = sorted({ticker for ticker in (tickers or []) if ticker})

    message = (
        "Sweep rejected: optimization sweep limit exceeded"
        if normalized_cap
        else "Sweep rejected: optimization sweep limit policy requires manual approval"
    )
    detail_message = (
        f"requested {normalized_requested} combinations but cap is {normalized_cap}"
        if normalized_cap
        else f"requested {normalized_requested} combinations"
    )

    description = (
        f"Optimization sweep requested {normalized_requested} combinations while the cap is {normalized_cap}."
        if normalized_cap
        else f"Optimization sweep requested {normalized_requested} combinations with cap enforcement disabled."
    )

    if ticker_list:
        description += f" Affected tickers: {', '.join(ticker_list)}."

    details = [
        ErrorDetail(
            field="combination_count",
            message=detail_message,
            code=_OPTIMIZATION_SWEEP_LIMIT_CODE,
        )
    ]
    if ticker_list:
        details.append(
            ErrorDetail(
                field="tickers",
                message="cap exceeded for tickers",
                code=_OPTIMIZATION_SWEEP_LIMIT_CODE,
            )
        )

    payload = ErrorResponse(
        error_code=to_kebab(_OPTIMIZATION_SWEEP_LIMIT_CODE),
        message=message,
        details=details,
        docs_url=docs_url,
    ).model_dump(exclude_none=True)

    payload.setdefault(
        "error",
        {
            "code": _OPTIMIZATION_SWEEP_LIMIT_CODE,
            "message": description,
            "retryable": False,
        },
    )
    payload.setdefault("detail", description)
    return payload


__all__ = ["sweep_limit_hit_error"]
