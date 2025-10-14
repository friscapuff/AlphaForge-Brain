from __future__ import annotations

from typing import Any

from .expander import SweepCombination, SweepExpansion, expand_parameter_grid

__all__ = [
    "expand_parameter_grid",
    "SweepCombination",
    "SweepExpansion",
    "DEFAULT_SWEEP_ROOT",
    "SweepExecutionResult",
    "SweepTickerSpec",
    "execute_sweep",
    "SweepManifestRecord",
    "get_sweep_status",
    "list_sweeps",
    "load_manifest",
    "manifest_to_status",
]


def __getattr__(name: str) -> Any:
    if name in {
        "DEFAULT_SWEEP_ROOT",
        "SweepExecutionResult",
        "SweepTickerSpec",
        "execute_sweep",
    }:
        from . import orchestrator as _orchestrator

        value = getattr(_orchestrator, name)
        globals()[name] = value
        return value
    if name in {
        "SweepManifestRecord",
        "get_sweep_status",
        "list_sweeps",
        "load_manifest",
        "manifest_to_status",
    }:
        from . import repository as _repository

        value = getattr(_repository, name)
        globals()[name] = value
        return value
    raise AttributeError(f"module 'services.sweeps' has no attribute '{name}'")


def __dir__() -> list[str]:
    return sorted(__all__)
