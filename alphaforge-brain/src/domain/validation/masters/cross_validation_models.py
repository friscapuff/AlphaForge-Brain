from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Mapping

from infra import orm as _orm


class CrossValidationMode(str, Enum):
    PURGED_KFOLD = "purged_kfold"
    CPCV = "cpcv"
    AUTO = "auto"


@dataclass(slots=True, frozen=True)
class TimeRange:
    start: datetime
    end: datetime

    def to_api_payload(self) -> dict[str, str]:
        return {
            "start": self.start.isoformat(),
            "end": self.end.isoformat(),
        }


@dataclass(slots=True, frozen=True)
class CrossValidationFold:
    fold_id: str
    train: TimeRange
    test: TimeRange
    purge_span: timedelta
    metrics: Mapping[str, float]
    leakage_score: float | None = None
    extra_metadata: Mapping[str, Any] = field(default_factory=dict)

    def to_api_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "fold_id": self.fold_id,
            "train": self.train.to_api_payload(),
            "test": self.test.to_api_payload(),
            "purge_span": _format_timedelta(self.purge_span),
            "metrics": dict(self.metrics),
        }
        if self.leakage_score is not None:
            payload["leakage_score"] = self.leakage_score
        if self.extra_metadata:
            payload.update(dict(self.extra_metadata))
        return payload

    def metadata_payload(self) -> dict[str, Any]:
        meta: dict[str, Any] = {
            "fold_id": self.fold_id,
            "train": self.train.to_api_payload(),
            "test": self.test.to_api_payload(),
            "purge_span": _format_timedelta(self.purge_span),
            "metrics": dict(self.metrics),
        }
        if self.leakage_score is not None:
            meta["leakage_score"] = self.leakage_score
        if self.extra_metadata:
            meta.update(dict(self.extra_metadata))
        return meta

    @property
    def train_start(self) -> datetime:
        return self.train.start

    @property
    def train_end(self) -> datetime:
        return self.train.end

    @property
    def test_start(self) -> datetime:
        return self.test.start

    @property
    def test_end(self) -> datetime:
        return self.test.end


@dataclass(slots=True, frozen=True)
class CrossValidationSummary:
    run_hash: str
    mode: CrossValidationMode
    seed_root: int
    folds: tuple[CrossValidationFold, ...]
    leakage_score: float | None = None
    bias_flag: bool = False
    cscv_adjusted_sharpe: float | None = None
    extra_metadata: Mapping[str, Any] = field(default_factory=dict)

    VALIDATION_TYPE = "cross_validation"

    def to_api_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "mode": self.mode.value,
            "seed_root": self.seed_root,
            "folds": [fold.to_api_payload() for fold in self.folds],
        }
        if self.leakage_score is not None:
            payload["leakage_score"] = self.leakage_score
        if self.bias_flag:
            payload["bias_flag"] = True
        if self.cscv_adjusted_sharpe is not None:
            payload["cscv_adjusted_sharpe"] = self.cscv_adjusted_sharpe
        if self.extra_metadata:
            payload.update(dict(self.extra_metadata))
        return payload

    def metadata_payload(self) -> dict[str, Any]:
        meta: dict[str, Any] = {
            "mode": self.mode.value,
            "seed_root": self.seed_root,
            "folds": [fold.metadata_payload() for fold in self.folds],
        }
        if self.leakage_score is not None:
            meta["leakage_score"] = self.leakage_score
        if self.bias_flag:
            meta["bias_flag"] = True
        if self.cscv_adjusted_sharpe is not None:
            meta["cscv_adjusted_sharpe"] = self.cscv_adjusted_sharpe
        if self.extra_metadata:
            meta.update(dict(self.extra_metadata))
        return meta

    def to_orm(self) -> _orm.models.Validation:
        from json import dumps

        return _orm.models.Validation(
            run_hash=self.run_hash,
            validation_type=self.VALIDATION_TYPE,
            leakage_score=self.leakage_score,
            bias_flag=self.bias_flag,
            metadata_json=dumps(self.metadata_payload(), sort_keys=True),
        )

    @classmethod
    def from_orm(cls, row: _orm.models.Validation) -> CrossValidationSummary:
        from json import loads

        metadata_raw = loads(row.metadata_json or "{}")
        metadata: dict[str, Any]
        if isinstance(metadata_raw, Mapping):
            metadata = dict(metadata_raw)
        else:
            metadata = {}

        folds_meta_raw = metadata.get("folds", [])
        if isinstance(folds_meta_raw, list):
            fold_entries = [
                entry for entry in folds_meta_raw if isinstance(entry, Mapping)
            ]
        else:
            fold_entries = []

        folds: list[CrossValidationFold] = []
        for idx, fold_mapping in enumerate(fold_entries):
            fold_payload = dict(fold_mapping)
            metrics_payload = fold_payload.get("metrics")
            folded = CrossValidationFold(
                fold_id=str(fold_payload.get("fold_id", f"F{idx:02d}")),
                train=_parse_range(fold_payload.get("train")),
                test=_parse_range(fold_payload.get("test")),
                purge_span=_parse_timedelta(fold_payload.get("purge_span")),
                metrics=_coerce_metrics(metrics_payload),
                leakage_score=_maybe_float(fold_payload.get("leakage_score")),
                extra_metadata={
                    k: v
                    for k, v in fold_payload.items()
                    if k
                    not in {
                        "fold_id",
                        "train",
                        "test",
                        "purge_span",
                        "metrics",
                        "leakage_score",
                    }
                },
            )
            folds.append(folded)

        mode_value_raw = metadata.get("mode")
        mode_value: str
        if isinstance(mode_value_raw, str):
            mode_value = mode_value_raw
        else:
            mode_value = CrossValidationMode.PURGED_KFOLD.value

        leakage_value = row.leakage_score
        if leakage_value is None:
            leakage_value = _maybe_float(metadata.get("leakage_score"))

        bias_meta = metadata.get("bias_flag")
        bias_flag = bool(bias_meta) if bias_meta is not None else row.bias_flag

        cscv_adjusted_sharpe = _maybe_float(metadata.get("cscv_adjusted_sharpe"))
        return cls(
            run_hash=row.run_hash,
            mode=CrossValidationMode(mode_value),
            seed_root=int(metadata.get("seed_root", 0)),
            folds=tuple(folds),
            leakage_score=leakage_value,
            bias_flag=bool(bias_flag),
            cscv_adjusted_sharpe=cscv_adjusted_sharpe,
            extra_metadata={
                k: v
                for k, v in metadata.items()
                if k
                not in {
                    "mode",
                    "seed_root",
                    "folds",
                    "leakage_score",
                    "bias_flag",
                    "cscv_adjusted_sharpe",
                }
            },
        )


def _format_timedelta(delta: timedelta) -> str:
    # Represent timedelta in ISO 8601-ish format (e.g., "30D") to align with contracts.
    total_days = delta.total_seconds() / 86400
    if total_days.is_integer():
        return f"{int(total_days)}D"
    return f"{total_days:.6f}D"


def _parse_timedelta(payload: Any) -> timedelta:
    if isinstance(payload, timedelta):
        return payload
    if isinstance(payload, str) and payload.endswith("D"):
        value = float(payload[:-1])
        return timedelta(days=value)
    if isinstance(payload, (int, float)):
        return timedelta(days=float(payload))
    return timedelta(0)


def _parse_range(payload: Any) -> TimeRange:
    if isinstance(payload, dict):
        start_raw = payload.get("start")
        end_raw = payload.get("end")
    else:
        start_raw = None
        end_raw = None
    start = _coerce_datetime(start_raw)
    end = _coerce_datetime(end_raw)
    return TimeRange(start=start, end=end)


def _coerce_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            pass
    return datetime.fromtimestamp(0)


def _coerce_metrics(value: Any) -> Mapping[str, float]:
    if isinstance(value, Mapping):
        cleaned: dict[str, float] = {}
        for key, raw in value.items():
            maybe = _maybe_float(raw)
            if maybe is not None:
                cleaned[str(key)] = maybe
        return cleaned
    return {}


def _maybe_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


__all__ = [
    "CrossValidationFold",
    "CrossValidationMode",
    "CrossValidationSummary",
    "TimeRange",
]
