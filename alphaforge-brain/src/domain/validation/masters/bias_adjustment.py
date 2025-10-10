from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from infra import orm as _orm

BIAS_ABSOLUTE_THRESHOLD_DEFAULT = 0.25
BIAS_RELATIVE_THRESHOLD_DEFAULT = 0.20


@dataclass(slots=True, frozen=True)
class SharpeBiasAdjustment:
    """Deflated & probabilistic Sharpe diagnostics for Masters validation."""

    run_hash: str
    observed_sharpe: float
    deflated_sharpe: float
    probabilistic_sharpe: float
    assumed_trials: int
    benchmark_sharpe: float
    skewness: float | None = None
    kurtosis: float | None = None
    cscv_adjusted_sharpe: float | None = None
    bias_flag: bool = False
    status: str = "pass"
    absolute_threshold: float = BIAS_ABSOLUTE_THRESHOLD_DEFAULT
    relative_threshold: float = BIAS_RELATIVE_THRESHOLD_DEFAULT
    extra_metadata: Mapping[str, Any] = field(default_factory=dict)

    VALIDATION_TYPE = "bias_adjustment"

    def with_bias_evaluation(
        self,
        *,
        absolute_threshold: float | None = None,
        relative_threshold: float | None = None,
    ) -> SharpeBiasAdjustment:
        abs_thr = absolute_threshold or self.absolute_threshold
        rel_thr = relative_threshold or self.relative_threshold
        cscv = self.cscv_adjusted_sharpe
        breach = False
        if cscv is not None:
            breach_abs = cscv <= self.observed_sharpe - abs_thr
            breach_rel = cscv <= self.observed_sharpe * (1 - rel_thr)
            breach = breach_abs and breach_rel
        status = "fail" if breach else self.status
        return SharpeBiasAdjustment(
            run_hash=self.run_hash,
            observed_sharpe=self.observed_sharpe,
            deflated_sharpe=self.deflated_sharpe,
            probabilistic_sharpe=self.probabilistic_sharpe,
            assumed_trials=self.assumed_trials,
            benchmark_sharpe=self.benchmark_sharpe,
            skewness=self.skewness,
            kurtosis=self.kurtosis,
            cscv_adjusted_sharpe=cscv,
            bias_flag=breach,
            status=status,
            absolute_threshold=abs_thr,
            relative_threshold=rel_thr,
            extra_metadata=self.extra_metadata,
        )

    def to_manifest_fragment(self) -> dict[str, Any]:
        fragment: dict[str, Any] = {
            "observed_sharpe": self.observed_sharpe,
            "deflated_sharpe": self.deflated_sharpe,
            "probabilistic_sharpe": self.probabilistic_sharpe,
            "assumed_trials": self.assumed_trials,
            "benchmark_sharpe": self.benchmark_sharpe,
        }
        if self.cscv_adjusted_sharpe is not None:
            fragment["cscv_adjusted_sharpe"] = self.cscv_adjusted_sharpe
        if self.bias_flag:
            fragment["bias_flag"] = True
        if self.skewness is not None:
            fragment["skewness"] = self.skewness
        if self.kurtosis is not None:
            fragment["kurtosis"] = self.kurtosis
        return fragment

    def to_api_payload(self) -> dict[str, Any]:
        payload = self.to_manifest_fragment()
        payload["status"] = self.status
        payload["absolute_threshold"] = self.absolute_threshold
        payload["relative_threshold"] = self.relative_threshold
        return payload

    def metadata_payload(self) -> dict[str, Any]:
        meta = {
            "observed_sharpe": self.observed_sharpe,
            "assumed_trials": self.assumed_trials,
            "benchmark_sharpe": self.benchmark_sharpe,
            "bias_flag": self.bias_flag,
            "status": self.status,
            "absolute_threshold": self.absolute_threshold,
            "relative_threshold": self.relative_threshold,
        }
        if self.cscv_adjusted_sharpe is not None:
            meta["cscv_adjusted_sharpe"] = self.cscv_adjusted_sharpe
        if self.skewness is not None:
            meta["skewness"] = self.skewness
        if self.kurtosis is not None:
            meta["kurtosis"] = self.kurtosis
        if self.extra_metadata:
            meta.update(dict(self.extra_metadata))
        return meta

    def to_orm(self) -> _orm.models.Validation:
        from json import dumps

        return _orm.models.Validation(
            run_hash=self.run_hash,
            validation_type=self.VALIDATION_TYPE,
            dsr=self.deflated_sharpe,
            psr=self.probabilistic_sharpe,
            bias_flag=self.bias_flag,
            p_value=None,
            effect_size=None,
            permutation_count=None,
            metadata_json=dumps(self.metadata_payload(), sort_keys=True),
        )

    @classmethod
    def from_orm(cls, row: _orm.models.Validation) -> SharpeBiasAdjustment:
        from json import loads

        meta = loads(row.metadata_json or "{}")
        return cls(
            run_hash=row.run_hash,
            observed_sharpe=meta.get("observed_sharpe", 0.0),
            deflated_sharpe=row.dsr or 0.0,
            probabilistic_sharpe=row.psr or 0.0,
            assumed_trials=int(meta.get("assumed_trials", 0)),
            benchmark_sharpe=meta.get("benchmark_sharpe", 0.0),
            skewness=meta.get("skewness"),
            kurtosis=meta.get("kurtosis"),
            cscv_adjusted_sharpe=meta.get("cscv_adjusted_sharpe"),
            bias_flag=bool(
                row.bias_flag
                if row.bias_flag is not None
                else meta.get("bias_flag", False)
            ),
            status=meta.get("status", "pass"),
            absolute_threshold=meta.get(
                "absolute_threshold", BIAS_ABSOLUTE_THRESHOLD_DEFAULT
            ),
            relative_threshold=meta.get(
                "relative_threshold", BIAS_RELATIVE_THRESHOLD_DEFAULT
            ),
            extra_metadata={
                k: v
                for k, v in meta.items()
                if k
                not in {
                    "observed_sharpe",
                    "assumed_trials",
                    "benchmark_sharpe",
                    "skewness",
                    "kurtosis",
                    "cscv_adjusted_sharpe",
                    "bias_flag",
                    "status",
                    "absolute_threshold",
                    "relative_threshold",
                }
            },
        )


__all__ = [
    "BIAS_ABSOLUTE_THRESHOLD_DEFAULT",
    "BIAS_RELATIVE_THRESHOLD_DEFAULT",
    "SharpeBiasAdjustment",
]
