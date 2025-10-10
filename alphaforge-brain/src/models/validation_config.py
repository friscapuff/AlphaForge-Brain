from __future__ import annotations

from typing import Any, Iterable

from pydantic import Field, field_validator, model_validator

from .base import BaseModelStrict

_DEFAULT_MODULES: tuple[str, ...] = (
    "permutation",
    "dsr",
    "psr",
    "purged_kfold",
    "cpcv",
    "realism",
)


class ValidationConfig(BaseModelStrict):  # FR-007, FR-014
    seed: int = Field(ge=0)
    permutation_count: int = Field(default=0, ge=0)
    significance_threshold: float = Field(default=0.01, ge=0, le=1)
    leakage_threshold: float = Field(default=0.1, ge=0, le=1)
    realism_capacity_bps_limit: int = Field(default=500, ge=0)
    bias_absolute_threshold: float = Field(default=0.25, ge=0)
    bias_relative_threshold: float = Field(default=0.20, ge=0, le=1)
    permutation_enabled: bool = True
    dsr_enabled: bool = True
    psr_enabled: bool = True
    purged_kfold_enabled: bool = True
    cpcv_enabled: bool = True
    realism_enabled: bool = True
    modules: tuple[str, ...] = Field(default_factory=lambda: _DEFAULT_MODULES)

    @model_validator(mode="before")
    @classmethod
    def _upgrade_legacy(
        cls, data: Any
    ) -> Any:  # pragma: no cover - exercised indirectly
        if not isinstance(data, dict):
            return data
        upgraded = dict(data)
        if "permutation_trials" in upgraded and "permutation_count" not in upgraded:
            upgraded["permutation_count"] = upgraded.pop("permutation_trials")
        if (
            "caution_p_threshold" in upgraded
            and "significance_threshold" not in upgraded
        ):
            upgraded["significance_threshold"] = upgraded.pop("caution_p_threshold")
        modules = upgraded.get("modules")
        if modules is not None and not isinstance(modules, (list, tuple)):
            modules = cls._normalise_modules(str(modules).split(","))
            upgraded["modules"] = modules
        elif isinstance(modules, (list, tuple)):
            upgraded["modules"] = cls._normalise_modules(modules)
        if "modules" in upgraded:
            active_set = set(upgraded["modules"])
            for name in _DEFAULT_MODULES:
                key = f"{name}_enabled"
                if key not in upgraded:
                    upgraded[key] = name in active_set
        return upgraded

    @model_validator(mode="after")
    def _enforce_consistency(self) -> ValidationConfig:
        normalised = self._normalise_modules(self.modules)
        object.__setattr__(self, "modules", normalised)

        module_flags = {
            "permutation": self.permutation_enabled,
            "dsr": self.dsr_enabled,
            "psr": self.psr_enabled,
            "purged_kfold": self.purged_kfold_enabled,
            "cpcv": self.cpcv_enabled,
            "realism": self.realism_enabled,
        }
        active = tuple(
            sorted(name for name, enabled in module_flags.items() if enabled)
        )
        if set(active) != set(normalised):
            object.__setattr__(self, "modules", active or _DEFAULT_MODULES)
        if self.significance_threshold == 0:
            raise ValueError(
                "significance_threshold must be > 0 for meaningful warning"
            )
        return self

    @field_validator("permutation_count")
    @classmethod
    def _check_permutation_count(cls, value: int) -> int:
        if value < 0:
            raise ValueError("permutation_count cannot be negative")
        return value

    @staticmethod
    def _normalise_modules(modules: Iterable[str]) -> tuple[str, ...]:
        seen: dict[str, None] = {}
        for module in modules:
            key = module.strip()
            if not key:
                continue
            seen[key] = None
        return tuple(sorted(seen)) if seen else _DEFAULT_MODULES

    @property
    def permutation_trials(self) -> int:
        return self.permutation_count

    @property
    def caution_p_threshold(self) -> float:
        return self.significance_threshold

    def module_enabled(self, name: str) -> bool:
        return name in self.modules

    def enabled_modules(self) -> tuple[str, ...]:
        return self.modules

    def to_manifest_fragment(self) -> dict[str, Any]:
        return {
            "modules": list(self.modules),
            "permutation_count": self.permutation_count,
            "significance_threshold": self.significance_threshold,
            "leakage_threshold": self.leakage_threshold,
            "realism_capacity_bps_limit": self.realism_capacity_bps_limit,
            "bias_absolute_threshold": self.bias_absolute_threshold,
            "bias_relative_threshold": self.bias_relative_threshold,
        }


__all__ = ["ValidationConfig"]
