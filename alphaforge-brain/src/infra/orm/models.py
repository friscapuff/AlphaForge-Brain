from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class Run(Base):
    __tablename__ = "runs"

    run_hash: Mapped[str] = mapped_column(String, primary_key=True)
    created_at: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String)
    manifest_json: Mapped[str] = mapped_column(Text)


class Trade(Base):
    __tablename__ = "trades"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_hash: Mapped[str] = mapped_column(String, ForeignKey("runs.run_hash"))
    ts: Mapped[int] = mapped_column(Integer)
    side: Mapped[str] = mapped_column(String)
    qty: Mapped[float] = mapped_column()
    fill_price: Mapped[float | None] = mapped_column(default=None)
    fees: Mapped[float | None] = mapped_column(default=None)
    slippage: Mapped[float | None] = mapped_column(default=None)
    pnl: Mapped[float | None] = mapped_column(default=None)
    position_after: Mapped[float | None] = mapped_column(default=None)
    bar_index: Mapped[int | None] = mapped_column(default=None)
    content_hash: Mapped[str | None] = mapped_column(String, default=None)


class Equity(Base):
    __tablename__ = "equity"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_hash: Mapped[str] = mapped_column(String, ForeignKey("runs.run_hash"))
    ts: Mapped[int] = mapped_column(Integer)
    equity: Mapped[float | None] = mapped_column(default=None)
    drawdown: Mapped[float | None] = mapped_column(default=None)
    realized_pnl: Mapped[float | None] = mapped_column(default=None)
    unrealized_pnl: Mapped[float | None] = mapped_column(default=None)
    content_hash: Mapped[str | None] = mapped_column(String, default=None)


class Feature(Base):
    __tablename__ = "features"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_hash: Mapped[str] = mapped_column(String, ForeignKey("runs.run_hash"))
    spec_hash: Mapped[str] = mapped_column(String)
    rows: Mapped[int | None] = mapped_column(default=None)
    cols: Mapped[int | None] = mapped_column(default=None)
    digest: Mapped[str | None] = mapped_column(String, default=None)
    build_policy: Mapped[str | None] = mapped_column(Text, default=None)  # JSON
    cache_link: Mapped[str | None] = mapped_column(String, default=None)

    __table_args__ = (
        UniqueConstraint("run_hash", "spec_hash", name="uq_features_run_spec"),
    )


class Validation(Base):
    __tablename__ = "validation"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_hash: Mapped[str] = mapped_column(String, ForeignKey("runs.run_hash"))
    method: Mapped[str | None] = mapped_column(String, default=None)
    params_json: Mapped[str | None] = mapped_column(Text, default=None)
    results_json: Mapped[str | None] = mapped_column(Text, default=None)
    ci_width: Mapped[float | None] = mapped_column(default=None)
    p_value: Mapped[float | None] = mapped_column(default=None)
    content_hash: Mapped[str | None] = mapped_column(String, default=None)


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_type: Mapped[str] = mapped_column(String)
    run_hash: Mapped[str] = mapped_column(String, ForeignKey("runs.run_hash"))
    actor: Mapped[str | None] = mapped_column(String, default=None)
    ts: Mapped[int] = mapped_column(Integer)
    details_json: Mapped[str | None] = mapped_column(Text, default=None)
