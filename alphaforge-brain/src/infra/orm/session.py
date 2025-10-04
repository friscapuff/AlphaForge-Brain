from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from .. import config as _config


def _build_sqlalchemy_url() -> str:
    # For now, derive from existing sqlite_path setting; switchable later.
    path = _config.get_settings().sqlite_path
    return f"sqlite:///{path}"


def get_engine(echo: bool = False):
    return create_engine(_build_sqlalchemy_url(), echo=echo, future=True)


def get_sessionmaker(echo: bool = False) -> sessionmaker[Session]:
    eng = get_engine(echo=echo)
    return sessionmaker(bind=eng, autoflush=False, autocommit=False, future=True)


@contextmanager
def session_scope(echo: bool = False) -> Iterator[Session]:
    SessionLocal = get_sessionmaker(echo=echo)
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
