from __future__ import annotations

from typing import Any, Mapping

from pydantic import BaseModel, ConfigDict, Field, RootModel


class ValidationArtifactDescriptor(BaseModel):
    sha256: str
    size: int

    model_config = ConfigDict(extra="allow")


class ValidationModules(BaseModel):
    permutation: bool
    bias_adjustments: bool
    cross_validation: bool | str
    execution_realism: bool

    model_config = ConfigDict(extra="allow")


class ValidationConfig(BaseModel):
    modules: list[str]
    permutation_count: int
    significance_threshold: float
    leakage_threshold: float
    realism_capacity_bps_limit: float
    bias_absolute_threshold: float
    bias_relative_threshold: float

    model_config = ConfigDict(extra="allow")


class ValidationHistogramSummary(BaseModel):
    bins: int
    counts: list[int]
    mean: float | None = None
    std_dev: float | None = None
    min: float | None = None
    max: float | None = None
    percentiles: dict[str, float] | None = None

    model_config = ConfigDict(extra="allow")


class ValidationPermutationSegment(BaseModel):
    segment_id: str
    p_value: float
    effect_size: float | None = None
    requested_permutations: int
    executed_permutations: int
    observed_metric: float | None = None
    histogram: ValidationHistogramSummary | None = None
    artifact: str | None = None
    fallback_reason: str | None = None
    seed_root: int | None = None

    model_config = ConfigDict(extra="allow")


class ValidationPermutationPayload(BaseModel):
    segments: list[ValidationPermutationSegment] = Field(default_factory=list)

    model_config = ConfigDict(extra="allow")


class ValidationBiasAdjustments(BaseModel):
    observed_sharpe: float
    deflated_sharpe: float
    probabilistic_sharpe: float
    assumed_trials: int
    benchmark_sharpe: float
    status: str
    absolute_threshold: float
    relative_threshold: float
    cscv_adjusted_sharpe: float | None = None
    bias_flag: bool | None = None
    skewness: float | None = None
    kurtosis: float | None = None

    model_config = ConfigDict(extra="allow")


class ValidationFoldRange(BaseModel):
    start: str
    end: str

    model_config = ConfigDict(extra="allow")


class ValidationCrossValidationFold(BaseModel):
    fold_id: str
    train: ValidationFoldRange
    test: ValidationFoldRange
    purge_span: str
    metrics: Mapping[str, float]
    leakage_score: float | None = None

    model_config = ConfigDict(extra="allow")


class ValidationCrossValidationPayload(BaseModel):
    mode: str
    seed_root: int | None = None
    folds: list[ValidationCrossValidationFold] = Field(default_factory=list)
    leakage_score: float | None = None
    bias_flag: bool | None = None
    cscv_adjusted_sharpe: float | None = None
    folds_artifact: str | None = None
    folds_artifact_sha256: str | None = None

    model_config = ConfigDict(extra="allow")


class ValidationExecutionRealismPayload(BaseModel):
    status: str
    transaction_cost_bps: float
    market_impact_bps: float
    capacity_ratio: float
    warnings: list[str] = Field(default_factory=list)
    guidance: list[str] = Field(default_factory=list)
    assumptions: Mapping[str, Any] = Field(default_factory=dict)
    artifact: str | None = None
    artifact_sha256: str | None = None

    model_config = ConfigDict(extra="allow")


class ValidationManifestModuleConfig(BaseModel):
    enabled: bool
    executed_permutations: int | None = None

    model_config = ConfigDict(extra="allow")


class ValidationManifestModules(BaseModel):
    permutation: ValidationManifestModuleConfig
    dsr: ValidationManifestModuleConfig
    psr: ValidationManifestModuleConfig
    purged_kfold: ValidationManifestModuleConfig
    cpcv: ValidationManifestModuleConfig
    realism: ValidationManifestModuleConfig

    model_config = ConfigDict(extra="allow")


class ValidationManifestPermutationSegment(BaseModel):
    segment_id: str
    p_value: float
    effect_size: float | None = None
    artifact_path: str | None = None
    artifact_sha256: str | None = None
    fallback_reason: str | None = None

    model_config = ConfigDict(extra="allow")


class ValidationManifestPermutationSummary(BaseModel):
    segments: list[ValidationManifestPermutationSegment] = Field(default_factory=list)

    model_config = ConfigDict(extra="allow")


class ValidationManifestFragment(BaseModel):
    validation_schema_version: int
    validation_significance: str
    modules: ValidationManifestModules
    permutation_summary: ValidationManifestPermutationSummary
    sharpe_adjustments: Mapping[str, Any] | None = None
    cross_validation: Mapping[str, Any] | None = None
    execution_realism: Mapping[str, Any] | None = None

    model_config = ConfigDict(extra="allow")


class ValidationArtifacts(RootModel[dict[str, ValidationArtifactDescriptor]]):
    root: dict[str, ValidationArtifactDescriptor] = Field(default_factory=dict)


class ValidationPayload(BaseModel):
    schema_version: int
    significance_status: str
    failed_checks: list[str] = Field(default_factory=list)
    caution_checks: list[str] = Field(default_factory=list)
    metadata: Mapping[str, Any] = Field(default_factory=dict)
    modules: ValidationModules
    config: ValidationConfig
    permutation: ValidationPermutationPayload
    bias_adjustments: ValidationBiasAdjustments | None = None
    cross_validation: ValidationCrossValidationPayload | None = None
    execution_realism: ValidationExecutionRealismPayload | None = None
    manifest: ValidationManifestFragment | None = None
    artifacts: dict[str, ValidationArtifactDescriptor] = Field(default_factory=dict)
    manifest_hash: str | None = None

    model_config = ConfigDict(extra="allow")


__all__ = [
    "ValidationArtifactDescriptor",
    "ValidationArtifacts",
    "ValidationBiasAdjustments",
    "ValidationConfig",
    "ValidationCrossValidationFold",
    "ValidationCrossValidationPayload",
    "ValidationExecutionRealismPayload",
    "ValidationHistogramSummary",
    "ValidationManifestFragment",
    "ValidationManifestModules",
    "ValidationManifestPermutationSegment",
    "ValidationManifestPermutationSummary",
    "ValidationModules",
    "ValidationPayload",
    "ValidationPermutationPayload",
    "ValidationPermutationSegment",
]
