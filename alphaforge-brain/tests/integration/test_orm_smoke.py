from __future__ import annotations

import pytest

# Skip gracefully if SQLAlchemy not available in current environment
pytest.importorskip("sqlalchemy")


@pytest.mark.integration
def test_orm_smoke_sqlite_tmp(sqlite_tmp_path, monkeypatch):
    # Point settings to temporary DB and reset cache
    monkeypatch.setenv("APP_SQLITE_PATH", str(sqlite_tmp_path))
    # Invalidate cached settings so new env takes effect
    import infra.config as cfg

    cfg.get_settings.cache_clear()  # type: ignore[attr-defined]

    # Now import ORM after settings are configured
    from infra.orm import Base, RunRepository, get_engine
    from infra.orm.models import Run

    eng = get_engine()
    Base.metadata.create_all(eng)

    # Insert minimal run and check retrieval
    from infra.orm.session import session_scope

    run = Run(run_hash="run_smoke_1", created_at=0, status="ok", manifest_json="{}")
    with session_scope() as s:
        rr = RunRepository(s)
        rr.upsert(run)

    with session_scope() as s:
        rr = RunRepository(s)
        got = rr.get("run_smoke_1")
        assert got is not None
        assert got.run_hash == "run_smoke_1"
