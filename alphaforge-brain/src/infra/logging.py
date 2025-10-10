from __future__ import annotations

import logging
from collections.abc import Callable, MutableMapping
from typing import Any, cast

import structlog
from structlog.stdlib import add_logger_name as _add_logger_name

from . import config as _config_mod

MergeContextVars = Callable[
    [Any, str, MutableMapping[str, Any]], MutableMapping[str, Any]
]

try:  # structlog >= 20 exposes contextvars helpers
    from structlog.contextvars import merge_contextvars as _merge_contextvars_fn
except Exception:  # pragma: no cover - optional feature
    _merge_contextvars: MergeContextVars | None = None
else:
    _merge_contextvars = cast(MergeContextVars, _merge_contextvars_fn)


def _configure_structlog() -> None:
    settings = _config_mod.get_settings()

    timestamper = structlog.processors.TimeStamper(fmt="iso", utc=True)

    def _safe_add_logger_name(
        logger: Any, method_name: str, event_dict: MutableMapping[str, Any]
    ) -> MutableMapping[str, Any]:
        try:
            return _add_logger_name(logger, method_name, event_dict)
        except AttributeError:
            name = getattr(logger, "name", None)
            if name is None:
                underlying = getattr(logger, "_logger", None)
                name = getattr(underlying, "name", None)
            if name is not None:
                event_dict["logger"] = name
            return event_dict

    # Shared processors (typing simplified for mypy compatibility)
    shared_processors: list[Any] = []
    if _merge_contextvars is not None:
        shared_processors.append(_merge_contextvars)
    shared_processors.extend(
        [
            timestamper,
            _safe_add_logger_name,
            structlog.processors.add_log_level,
            structlog.processors.EventRenamer("message"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
        ]
    )

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
    # Do not clobber existing handlers (e.g., pytest caplog); append ours if missing
    if not any(isinstance(h, StructlogHandler) for h in root.handlers):
        root.addHandler(StructlogHandler())


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    if not structlog.is_configured():  # Defensive, but normally configured via init_app
        _configure_structlog()
    logger = structlog.get_logger(name) if name else structlog.get_logger()
    return cast(structlog.stdlib.BoundLogger, logger)


def init_logging() -> None:
    _configure_structlog()
    structlog.get_logger("startup").info("logging_initialized")


__all__ = ["get_logger", "init_logging"]
