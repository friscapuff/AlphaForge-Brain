from __future__ import annotations

import pathlib
import sys
from typing import Any


def _bootstrap() -> tuple[Any, Any, Any]:
    """Bootstrap PYTHONPATH and import mind client, app factory, TestClient.

    Wrapped in a function so imports occur after sys.path mutation without
    triggering E402 (imports after non-import statements) and without noqa.
    """
    _r = pathlib.Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(_r / "alphaforge-brain" / "src"))
    sys.path.insert(0, str(_r / "alphaforge-mind" / "src"))
    try:
        import client as _mind_client  # primary path (mind project root)
    except Exception:  # pragma: no cover - fallback when executed differently
        try:
            from alphaforge_mind import (
                alphaforge_mind_client as _mind_client,
            )  # runtime fallback
        except Exception as e:  # pragma: no cover - give clearer message
            raise ImportError("Unable to import mind client module") from e
    from api.app import create_app as _create_app  # relies on brain src on sys.path
    from fastapi.testclient import TestClient as _TestClient

    return _mind_client, _create_app, _TestClient


mind_client, create_app, TestClient = _bootstrap()


def test_hello_run_deterministic(tmp_path):
    app = create_app()
    tc = TestClient(app)
    client = mind_client.AlphaForgeMindClient(base_url="http://testserver", session=tc)
    cfg = {
        "indicators": [{"name": "sma", "params": {"window": 5}}],
        "strategy": {"name": "dual_sma", "params": {"fast": 5, "slow": 20}},
        "risk": {"model": "fixed_fraction", "params": {"fraction": 0.1}},
        "execution": {"mode": "sim", "slippage_bps": 0.0, "fee_bps": 0.0},
        "validation": {},
        "symbol": "NVDA",
        "timeframe": "1d",
        "start": "2024-01-01",
        "end": "2024-02-01",
        "seed": 999,
    }
    sub1 = client.submit_run(cfg)
    sub2 = client.submit_run(cfg)
    assert sub1.run_hash == sub2.run_hash
    detail1 = client.get_run(sub1.run_hash)
    detail2 = client.get_run(sub2.run_hash)
    assert detail1 == detail2
