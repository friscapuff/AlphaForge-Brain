import os
import time

from infra import persistence
from infra.config import get_settings


def test_finalize_run_empty_batches(tmp_path, monkeypatch):
    # Ensure DB path is isolated by pointing settings env (if supported) to a temp file
    # (If settings module uses env var like ALPHAFORGEB_DB_PATH we could set it; relying on default ephemeral path otherwise.)
    run_hash = "rh_empty"
    # Force fresh DB so migrations with canonical schema (including updated_at) apply
    db_path = tmp_path / "fresh_test.db"
    os.environ["APP_SQLITE_PATH"] = str(db_path)
    # Clear cached settings so new APP_SQLITE_PATH takes effect
    try:
        get_settings.cache_clear()  # type: ignore[attr-defined]
    except Exception:
        pass
    # Initialize run row via persistence API (ensures migrations ran)
    persistence.init_run(
        run_hash=run_hash,
        created_at_ms=int(time.time() * 1000),
        status="PENDING",
        config_json={"k": 1},
        manifest_json={"files": []},
        data_hash="dhash",
        seed_root=1,
        db_version=1,
        bootstrap_seed=1,
    )
    n_trades, n_equity = persistence.finalize_run(
        run_hash=run_hash, trades_rows=[], equity_rows=[]
    )
    assert n_trades == 0 and n_equity == 0
