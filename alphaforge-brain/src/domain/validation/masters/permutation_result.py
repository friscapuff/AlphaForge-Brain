from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from infra import orm as _orm


@dataclass(slots=True, frozen=True)
class HistogramSummary:
    """Compact representation of a permutation histogram.

    Stores deterministic histogram counts along with optional descriptive
    statistics so downstream serializers (API, manifest, SSE) can project the
    appropriate subset without recomputing.
    """

    bins: int
    counts: tuple[int, ...]
    mean: float | None = None
    std_dev: float | None = None
    minimum: float | None = None
    maximum: float | None = None
    percentiles: Mapping[str, float] | None = None

    def total_samples(self) -> int:
        return sum(self.counts)

    def to_api_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "bins": self.bins,
            "counts": list(self.counts),
        }
        if self.mean is not None:
            payload["mean"] = self.mean
        if self.std_dev is not None:
            payload["std_dev"] = self.std_dev
        if self.minimum is not None:
            payload["min"] = self.minimum
        if self.maximum is not None:
            payload["max"] = self.maximum
        if self.percentiles:
            payload["percentiles"] = dict(self.percentiles)
        return payload

    def to_metadata(self) -> dict[str, Any]:
        meta = self.to_api_payload()
        meta["total_samples"] = self.total_samples()
        return meta


@dataclass(slots=True, frozen=True)
class PermutationValidationResult:
    """Domain model describing Masters permutation output for a run segment."""

    run_hash: str
    segment_id: str
    p_value: float
    effect_size: float | None
    requested_permutations: int
    executed_permutations: int
    seed_root: int | None
    histogram: HistogramSummary | None
    artifact_path: str | None
    artifact_sha256: str | None = None
    fallback_reason: str | None = None
    extra_metadata: Mapping[str, Any] = field(default_factory=dict)

    VALIDATION_TYPE = "permutation"

    def significance_status(self, threshold: float) -> str:
        if self.p_value <= threshold:
            return "pass"
        return "caution"

    def to_manifest_fragment(self) -> dict[str, Any]:
        fragment: dict[str, Any] = {
            "segment_id": self.segment_id,
            "p_value": self.p_value,
        }
        if self.effect_size is not None:
            fragment["effect_size"] = self.effect_size
        if self.artifact_path:
            fragment["artifact_path"] = self.artifact_path
        if self.artifact_sha256:
            fragment["artifact_sha256"] = self.artifact_sha256
        if self.fallback_reason:
            fragment["fallback_reason"] = self.fallback_reason
        return fragment

    def to_api_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "segment_id": self.segment_id,
            "p_value": self.p_value,
            "effect_size": self.effect_size,
            "requested_permutations": self.requested_permutations,
            "executed_permutations": self.executed_permutations,
        }
        if self.histogram is not None:
            payload["histogram"] = self.histogram.to_api_payload()
        if self.artifact_path:
            payload["artifact"] = self.artifact_path
        if self.fallback_reason:
            payload["fallback_reason"] = self.fallback_reason
        if self.seed_root is not None:
            payload["seed_root"] = self.seed_root
        return payload

    def metadata_payload(self) -> dict[str, Any]:
        base: dict[str, Any] = {
            "requested_permutations": self.requested_permutations,
            "executed_permutations": self.executed_permutations,
        }
        if self.histogram is not None:
            base["histogram"] = self.histogram.to_metadata()
        if self.seed_root is not None:
            base["seed_root"] = self.seed_root
        if self.artifact_path:
            base["artifact_path"] = self.artifact_path
        if self.artifact_sha256:
            base["artifact_sha256"] = self.artifact_sha256
        if self.fallback_reason:
            base["fallback_reason"] = self.fallback_reason
        if self.extra_metadata:
            base.update(dict(self.extra_metadata))
        return base

    def to_orm(self) -> _orm.models.Validation:
        from json import dumps

        return _orm.models.Validation(
            run_hash=self.run_hash,
            validation_type=self.VALIDATION_TYPE,
            segment_id=self.segment_id,
            p_value=self.p_value,
            effect_size=self.effect_size,
            permutation_count=self.executed_permutations,
            metadata_json=dumps(self.metadata_payload(), sort_keys=True),
        )

    @classmethod
    def from_orm(cls, row: _orm.models.Validation) -> PermutationValidationResult:
        from json import loads

        metadata = loads(row.metadata_json or "{}")
        histogram_meta = metadata.get("histogram")
        histogram: HistogramSummary | None = None
        if histogram_meta:
            histogram = HistogramSummary(
                bins=int(histogram_meta.get("bins", 0)),
                counts=tuple(int(v) for v in histogram_meta.get("counts", [])),
                mean=histogram_meta.get("mean"),
                std_dev=histogram_meta.get("std_dev"),
                minimum=histogram_meta.get("min"),
                maximum=histogram_meta.get("max"),
                percentiles=histogram_meta.get("percentiles"),
            )
        extra = {
            k: v
            for k, v in metadata.items()
            if k
            not in {
                "histogram",
                "seed_root",
                "artifact_path",
                "artifact_sha256",
                "fallback_reason",
                "requested_permutations",
                "executed_permutations",
            }
        }
        return cls(
            run_hash=row.run_hash,
            segment_id=row.segment_id or "unknown",
            p_value=row.p_value or 1.0,
            effect_size=row.effect_size,
            requested_permutations=int(metadata.get("requested_permutations", 0)),
            executed_permutations=row.permutation_count or 0,
            seed_root=metadata.get("seed_root"),
            histogram=histogram,
            artifact_path=metadata.get("artifact_path"),
            artifact_sha256=metadata.get("artifact_sha256"),
            fallback_reason=metadata.get("fallback_reason"),
            extra_metadata=extra,
        )


__all__ = ["HistogramSummary", "PermutationValidationResult"]
