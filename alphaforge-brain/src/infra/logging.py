from __future__ import annotations

import logging
from typing import Any, cast

import structlog

from . import config as _config_mod


def _configure_structlog() -> None:
    settings = _config_mod.get_settings()

    timestamper = structlog.processors.TimeStamper(fmt="iso", utc=True)

    # Shared processors (typing simplified for mypy compatibility)
    shared_processors: list[Any] = [
        timestamper,
        structlog.processors.add_log_level,
        structlog.processors.EventRenamer("message"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, settings.log_level.upper(), logging.INFO)
        ),
        context_class=dict,
        cache_logger_on_first_use=True,
    )

    # Sync standard logging to structlog
    class StructlogHandler(logging.Handler):
        def emit(
            self, record: logging.LogRecord
        ) -> None:  # pragma: no cover - passthrough
            logger = structlog.get_logger(record.name)
            logger.log(record.levelno, record.getMessage())

    root = logging.getLogger()
    root.setLevel(settings.log_level.upper())
    root.handlers[:] = [StructlogHandler()]


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    if not structlog.is_configured():  # Defensive, but normally configured via init_app
        _configure_structlog()
    logger = structlog.get_logger(name) if name else structlog.get_logger()
    return cast(structlog.stdlib.BoundLogger, logger)


def init_logging() -> None:
    _configure_structlog()
    structlog.get_logger("startup").info("logging_initialized")


__all__ = ["get_logger", "init_logging"]
