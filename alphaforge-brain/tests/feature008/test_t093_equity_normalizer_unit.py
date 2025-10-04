import pytest

pytestmark = pytest.mark.feature008


def _make_bar(nav: float, peak: float | None = None):
    from datetime import datetime, timezone

    from models.equity_bar import EquityBar

    peak_nav = peak if peak is not None else nav
    # drawdown = (peak-nav)/peak
    dd = (peak_nav - nav) / peak_nav if peak_nav > 0 else 0.0
    return EquityBar(
        ts=datetime.now(timezone.utc),
        nav=nav,
        peak_nav=peak_nav,
        drawdown=dd,
        gross_exposure=0.0,
        net_exposure=0.0,
        trade_count_cum=0,
    )


def test_t093_normalize_equity_compare_scaled():
    from services.equity_normalizer import SCALE_FACTOR, normalize_equity

    # Construct a clearly scaled sequence (median > heuristic threshold)
    bars = [
        _make_bar(1_200_000.0, 1_200_000.0),
        _make_bar(1_250_000.0, 1_250_000.0),
        _make_bar(1_300_000.0, 1_300_000.0),
    ]
    legacy, normalized = normalize_equity(bars, mode="compare")
    assert len(legacy) == len(normalized) == 3
    # Legacy retains large magnitude
    assert legacy[0].nav == 1_200_000.0
    # Normalized should be scaled down
    assert normalized[0].nav == pytest.approx(1_200_000.0 / SCALE_FACTOR)
    # Peak nav scaled as well
    assert normalized[0].peak_nav == pytest.approx(legacy[0].peak_nav / SCALE_FACTOR)
    # Drawdown invariant
    assert normalized[0].drawdown == legacy[0].drawdown


def test_t093_normalize_equity_compare_already_normal():
    from services.equity_normalizer import normalize_equity

    bars = [_make_bar(100.0, 100.0), _make_bar(105.0, 105.0), _make_bar(110.0, 110.0)]
    legacy, normalized = normalize_equity(bars, mode="compare")
    assert [b.nav for b in legacy] == [b.nav for b in normalized]
    assert [b.peak_nav for b in legacy] == [b.peak_nav for b in normalized]


def test_t093_normalize_equity_single_mode():
    from services.equity_normalizer import normalize_equity

    bars = [_make_bar(50.0, 55.0), _make_bar(60.0, 60.0)]
    normalized_only = normalize_equity(bars, mode="normalized")
    assert len(normalized_only) == 2
    assert [b.nav for b in normalized_only] == [50.0, 60.0]


def test_t093_normalize_equity_empty():
    from services.equity_normalizer import normalize_equity

    legacy, normalized = normalize_equity([], mode="compare")
    assert legacy == [] and normalized == []
