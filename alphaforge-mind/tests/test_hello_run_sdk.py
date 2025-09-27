from __future__ import annotations

import pathlib
import sys

_R = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_R / "alphaforge-brain" / "src"))
sys.path.insert(0, str(_R / "alphaforge-mind" / "src"))
import client as mind_client  # type: ignore
from api.app import create_app  # type: ignore
from fastapi.testclient import TestClient  # type: ignore


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
