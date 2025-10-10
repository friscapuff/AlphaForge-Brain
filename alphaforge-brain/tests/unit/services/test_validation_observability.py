from __future__ import annotations

from typing import Any

import pytest

from infra.observability import tracing


class _DummyLogger:
    def __init__(self, sink: list[tuple[str, dict[str, Any]]]) -> None:
        self._sink = sink

    def info(self, event: str, **payload: Any) -> None:
        self._sink.append((event, payload))

    def warning(self, event: str, **payload: Any) -> None:
        self._sink.append((event, payload))


def test_trace_validation_span_logs_and_persists(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[tuple[str, dict[str, Any]]] = []
    logger = _DummyLogger(events)
    monkeypatch.setattr(tracing, "get_logger", lambda _: logger)

    recorded: dict[str, Any] = {}

    def fake_record_trace_span(**kwargs: Any) -> None:
        recorded.update(kwargs)

    monkeypatch.setattr(tracing, "record_trace_span", fake_record_trace_span)

    with tracing.trace_validation_span("permutation", run_hash="run123") as span:
        span["permutations_executed"] = 64
        span["fallbacks"] = 1

    assert events
    event, payload = events[0]
    assert event == "validation_span"
    assert payload["span"] == "validation.permutation"
    assert payload["run_hash"] == "run123"
    assert payload["permutations_executed"] == 64
    assert payload["fallbacks"] == 1
    assert "duration_ms" in payload
    assert recorded["name"] == "validation.permutation"
    assert recorded["run_hash"] == "run123"
    assert recorded["attributes"]["permutations_executed"] == 64


def test_trace_validation_span_handles_exceptions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[tuple[str, dict[str, Any]]] = []
    logger = _DummyLogger(events)
    monkeypatch.setattr(tracing, "get_logger", lambda _: logger)

    def fail_record_trace_span(
        **_: Any,
    ) -> None:  # Should not be invoked when persist=False
        raise AssertionError("record_trace_span should not be called")

    monkeypatch.setattr(tracing, "record_trace_span", fail_record_trace_span)

    with pytest.raises(RuntimeError):
        with tracing.trace_validation_span(
            "aggregate", run_hash="runABC", persist=False
        ) as span:
            span["status"] = "fail"
            raise RuntimeError("boom")

    assert events
    event, payload = events[0]
    assert event == "validation_span"
    assert payload["span"] == "validation.aggregate"
    assert payload["run_hash"] == "runABC"
    assert payload["status"] == "fail"
    assert payload["exception"] == "RuntimeError"
    assert "duration_ms" in payload
