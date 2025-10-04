"""Aggregate immutable configuration for a single historical simulation run.

T026 - RunConfig model

Responsibilities (per spec / tasks):
* Collect all atomic config/value objects required to execute a run
* Enforce internal consistency (feature name uniqueness, strategy requirements satisfied)
* Provide a deterministic signature helper for provenance & manifest hashing
* Remain a pure data container (no side-effects / service wiring)

This precedes services so ONLY cross-model validation + lightweight helpers live here.
"""

from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256

from pydantic import Field, model_validator

from .base import BaseModelStrict
from .cost_model_config import CostModelConfig
from .dataset_snapshot import DatasetSnapshot
from .execution_config import ExecutionConfig
from .feature_spec import FeatureSpec
from .strategy_config import StrategyConfig
from .validation_config import ValidationConfig
from .walk_forward_config import WalkForwardConfig


class RunConfig(BaseModelStrict):  # FR aggregate (references many FR groups)
    dataset: DatasetSnapshot
    features: list[FeatureSpec] = Field(default_factory=list)
    strategy: StrategyConfig
    execution: ExecutionConfig
    cost: CostModelConfig
    validation: ValidationConfig
    walk_forward: WalkForwardConfig | None = Field(
        default=None, description="Optional walk-forward validation configuration"
    )
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    run_label: str | None = Field(
        default=None, description="Optional human label (not used in hashing)"
    )

    @model_validator(mode="after")
    def _check_consistency(self) -> RunConfig:
        names = [f.name for f in self.features]
        if len(names) != len(set(names)):
            raise ValueError("Feature names must be unique")
        missing = [r for r in self.strategy.required_features if r not in names]
        if missing:
            raise ValueError(f"Strategy required_features missing: {missing}")
        return self

    # ---- Convenience helpers (pure / deterministic) ----
    def feature_names(self) -> list[str]:
        return [f.name for f in self.features]

    def deterministic_signature(self) -> str:
        """Return stable SHA-256 hex digest representing this configuration.

        Excludes created_at and run_label (human / temporal). Order of features
        is normalized by feature name to avoid incidental ordering diffs.
        """
        parts: list[str] = []

        def add(k: str, v: str | int | float | None) -> None:
            parts.append(f"{k}={v}")

        add("dataset_hash", self.dataset.data_hash)
        add("calendar", self.dataset.calendar_id)
        # Normalize feature ordering
        for fs in sorted(self.features, key=lambda x: x.name):
            add(
                "feature",
                f"{fs.name}:{fs.version}:{sorted(fs.inputs)}:{sorted(fs.params.items())}:{fs.shift_applied}",
            )
        add("strategy_id", self.strategy.id)
        add("strategy_params", str(sorted(self.strategy.parameters.items())))
        add("exec_fill", self.execution.fill_policy.value)
        add("exec_lot", self.execution.lot_size)
        add("exec_round", self.execution.rounding_mode.value)
        add("cost_slip", self.cost.slippage_bps)
        add("cost_fee", self.cost.fee_bps)
        add("cost_borrow", self.cost.borrow_cost_bps)
        add("valid_perm", self.validation.permutation_trials)
        add("valid_seed", self.validation.seed)
        add("valid_thresh", self.validation.caution_p_threshold)
        if self.walk_forward:
            wf = self.walk_forward
            add("wf_train", wf.segment.train_bars)
            add("wf_test", wf.segment.test_bars)
            add("wf_warm", wf.segment.warmup_bars)
            add("wf_opt_enabled", wf.optimization.enabled)
            add(
                "wf_opt_grid",
                str(
                    sorted((k, tuple(v)) for k, v in wf.optimization.param_grid.items())
                ),
            )
            add("wf_robust", wf.robustness.compute)

        blob = "|".join(parts)
        return sha256(blob.encode("utf-8")).hexdigest()

    def provenance_tuple(self) -> tuple[str, ...]:
        """Compact tuple of stable fields for external manifest composition.

        Provided separately from deterministic_signature for easier unit-level
        assertions / diffs in tests.
        """
        base: list[str | int | float] = [
            self.dataset.data_hash,
            self.dataset.calendar_id,
            self.strategy.id,
            self.execution.fill_policy.value,
            self.execution.rounding_mode.value,
            self.cost.slippage_bps,
            self.cost.fee_bps,
            self.cost.borrow_cost_bps,
            self.validation.permutation_trials,
            self.validation.seed,
            self.validation.caution_p_threshold,
        ]
        if self.walk_forward:
            base.extend(
                [
                    self.walk_forward.segment.train_bars,
                    self.walk_forward.segment.test_bars,
                    self.walk_forward.segment.warmup_bars,
                    int(self.walk_forward.optimization.enabled),
                    int(self.walk_forward.robustness.compute),
                ]
            )
        # features appended last (normalized by name)
        for fs in sorted(self.features, key=lambda x: x.name):
            base.append(f"{fs.name}:{fs.version}")
        return tuple(str(x) for x in base)


__all__ = ["RunConfig"]
