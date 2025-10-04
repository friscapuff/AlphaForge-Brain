"""Feature registry loading & shift enforcement (T034).

Goals:
* Load feature specifications (FeatureSpec) from a provided mapping or list
* Enforce that each declared feature has `shift_applied=True` if global shift policy requires
* Provide deterministic ordering and validation utilities
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence

from pydantic import BaseModel

from ..models.feature_spec import FeatureSpec


class FeatureRegistry(BaseModel):
    features: list[FeatureSpec]
    global_shift: int = 1  # we currently only support +1 forward shift enforcement

    def model_post_init(
        self, __context: dict[str, object]
    ) -> None:  # pydantic v2 model hook
        # Deduplicate & sort deterministically by name
        unique: dict[str, FeatureSpec] = {f.name: f for f in self.features}
        self.features = sorted(unique.values(), key=lambda f: f.name)
        if self.global_shift == 1:
            missing = [f.name for f in self.features if not f.shift_applied]
            if missing:
                raise ValueError(
                    "Shift policy requires all features to have shift_applied=True; missing: "
                    + ", ".join(missing)
                )

    def names(self) -> list[str]:
        return [f.name for f in self.features]

    def get(self, name: str) -> FeatureSpec:
        for f in self.features:
            if f.name == name:
                return f
        raise KeyError(name)


def build_registry(
    specs: Sequence[FeatureSpec] | Iterable[FeatureSpec], *, global_shift: int = 1
) -> FeatureRegistry:
    return FeatureRegistry(features=list(specs), global_shift=global_shift)


__all__ = ["FeatureRegistry", "build_registry"]
