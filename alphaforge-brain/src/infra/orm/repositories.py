from __future__ import annotations

from collections.abc import Iterable, Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from . import models as m


class RunRepository:
    def __init__(self, session: Session):
        self.s = session

    def get(self, run_hash: str) -> m.Run | None:
        return self.s.get(m.Run, run_hash)

    def upsert(self, run: m.Run) -> m.Run:
        self.s.merge(run)
        return run


class TradeRepository:
    def __init__(self, session: Session):
        self.s = session

    def list_for_run(self, run_hash: str) -> Sequence[m.Trade]:
        return (
            self.s.execute(select(m.Trade).where(m.Trade.run_hash == run_hash))
            .scalars()
            .all()
        )

    def add_all(self, trades: Iterable[m.Trade]) -> None:
        self.s.add_all(list(trades))


class EquityRepository:
    def __init__(self, session: Session):
        self.s = session

    def list_for_run(self, run_hash: str) -> Sequence[m.Equity]:
        return (
            self.s.execute(select(m.Equity).where(m.Equity.run_hash == run_hash))
            .scalars()
            .all()
        )

    def add_all(self, rows: Iterable[m.Equity]) -> None:
        self.s.add_all(list(rows))


class FeatureRepository:
    def __init__(self, session: Session):
        self.s = session

    def list_for_run(self, run_hash: str) -> Sequence[m.Feature]:
        return (
            self.s.execute(select(m.Feature).where(m.Feature.run_hash == run_hash))
            .scalars()
            .all()
        )

    def add(self, feature: m.Feature) -> m.Feature:
        self.s.add(feature)
        return feature


class ValidationRepository:
    def __init__(self, session: Session):
        self.s = session

    def list_for_run(self, run_hash: str) -> Sequence[m.Validation]:
        return (
            self.s.execute(
                select(m.Validation).where(m.Validation.run_hash == run_hash)
            )
            .scalars()
            .all()
        )

    def add(self, row: m.Validation) -> m.Validation:
        self.s.add(row)
        return row


class AuditLogRepository:
    def __init__(self, session: Session):
        self.s = session

    def list_for_run(self, run_hash: str) -> Sequence[m.AuditLog]:
        return (
            self.s.execute(select(m.AuditLog).where(m.AuditLog.run_hash == run_hash))
            .scalars()
            .all()
        )

    def add(self, entry: m.AuditLog) -> m.AuditLog:
        self.s.add(entry)
        return entry
