from __future__ import annotations

from types import SimpleNamespace
from typing import Any, Mapping

from domain.schemas.run_config import RunConfig as ApiRunConfig

from .pipeline import ValidationRuntimeConfig
from .seeding import ValidationSeedBundle, derive_seed_bundle

_DEFAULT_MODULES: tuple[str, ...] = (
    "permutation",
    "dsr",
    "psr",
    "purged_kfold",
    "cpcv",
    "realism",
)


def build_validation_context(
    api_config: ApiRunConfig,
) -> tuple[SimpleNamespace, ValidationRuntimeConfig, ValidationSeedBundle]:
    """Create runtime validation context from API run configuration."""

    validation_cfg = getattr(api_config, "validation", None)
    permutation_cfg = _normalize_mapping_like(
        getattr(validation_cfg, "permutation", None)
    )
    bias_cfg = _normalize_mapping_like(permutation_cfg.get("bias"))

    permutation_count = int(
        permutation_cfg.get("count")
        or permutation_cfg.get("n")
        or permutation_cfg.get("samples")
        or 256
    )
    significance_threshold = float(
        permutation_cfg.get("significance_threshold")
        or permutation_cfg.get("threshold")
        or 0.01
    )
    leakage_threshold = float(permutation_cfg.get("leakage_threshold") or 0.1)
    capacity_limit = float(permutation_cfg.get("capacity_limit_bps") or 500.0)
    bias_absolute_value = bias_cfg.get("absolute")
    bias_relative_value = bias_cfg.get("relative")

    bias_absolute_threshold = (
        float(bias_absolute_value) if bias_absolute_value is not None else 0.25
    )
    bias_relative_threshold = (
        float(bias_relative_value) if bias_relative_value is not None else 0.20
    )

    modules = set(_DEFAULT_MODULES)
    _apply_module_toggle(modules, "permutation", permutation_cfg)
    walk_forward_cfg = _normalize_mapping_like(
        getattr(validation_cfg, "walk_forward", None)
    )
    _apply_module_toggle(modules, "realism", walk_forward_cfg)

    seed_root = int(api_config.seed) if api_config.seed is not None else 0x010AF043
    runtime_config = ValidationRuntimeConfig(
        permutation_count=permutation_count,
        significance_threshold=significance_threshold,
        leakage_threshold=leakage_threshold,
        realism_capacity_bps_limit=capacity_limit,
        bias_absolute_threshold=bias_absolute_threshold,
        bias_relative_threshold=bias_relative_threshold,
        modules=tuple(sorted(modules)),
        seed_root=seed_root,
    )

    seed_bundle = derive_seed_bundle(
        seed_root=runtime_config.seed_root,
        permutation_trials=max(runtime_config.permutation_count, 128),
    )

    run_config = _build_run_config_adapter(
        api_config=api_config,
        runtime_config=runtime_config,
        seed_bundle=seed_bundle,
    )
    return run_config, runtime_config, seed_bundle


def _apply_module_toggle(modules: set[str], module: str, config: Any) -> None:
    if not isinstance(config, Mapping):
        return
    enabled = config.get("enabled")
    if enabled is None:
        return
    if bool(enabled):
        modules.add(module)
    else:
        modules.discard(module)


def _build_run_config_adapter(
    *,
    api_config: ApiRunConfig,
    runtime_config: ValidationRuntimeConfig,
    seed_bundle: ValidationSeedBundle,
) -> SimpleNamespace:
    strategy_cfg = getattr(api_config, "strategy", None)
    strategy_params = _normalize_mapping_like(getattr(strategy_cfg, "params", None))
    strategy = SimpleNamespace(parameters=strategy_params)
    validation = SimpleNamespace(
        permutation_trials=runtime_config.permutation_count,
        permutation_count=runtime_config.permutation_count,
        seed=runtime_config.seed_root,
        significance_threshold=runtime_config.significance_threshold,
        leakage_threshold=runtime_config.leakage_threshold,
        realism_capacity_bps_limit=runtime_config.realism_capacity_bps_limit,
        bias_absolute_threshold=runtime_config.bias_absolute_threshold,
        bias_relative_threshold=runtime_config.bias_relative_threshold,
    )

    validation_cfg = getattr(api_config, "validation", None)
    walk_forward_cfg = _normalize_mapping_like(
        getattr(validation_cfg, "walk_forward", None)
    )
    segment_cfg = _normalize_mapping_like(walk_forward_cfg.get("segment"))
    optimization_cfg = _normalize_mapping_like(walk_forward_cfg.get("optimization"))

    segment = SimpleNamespace(
        train_bars=int(segment_cfg.get("train_bars", 160)),
        test_bars=int(segment_cfg.get("test_bars", 40)),
        warmup_bars=int(segment_cfg.get("warmup_bars", 20)),
    )
    optimization = SimpleNamespace(
        enabled=bool(optimization_cfg.get("enabled", True)),
        param_grid=dict(optimization_cfg.get("param_grid", {})),
    )
    walk_forward = SimpleNamespace(segment=segment, optimization=optimization)

    execution_cfg = getattr(api_config, "execution", None)
    slippage_bps = _coerce_float(getattr(execution_cfg, "slippage_bps", None))
    fee_bps = _coerce_float(getattr(execution_cfg, "fee_bps", None))
    borrow_bps = _coerce_float(getattr(execution_cfg, "borrow_cost_bps", None))

    execution = SimpleNamespace(
        slippage_bps=slippage_bps,
        fee_bps=fee_bps,
        borrow_cost_bps=borrow_bps,
        slippage_model=getattr(api_config.execution, "slippage_model", None),
        costs_included=False,
    )
    cost = SimpleNamespace(
        slippage_bps=slippage_bps,
        fee_bps=fee_bps,
        borrow_cost_bps=borrow_bps,
    )

    return SimpleNamespace(
        strategy=strategy,
        validation=validation,
        walk_forward=walk_forward,
        execution=execution,
        cost=cost,
        symbol=api_config.symbol,
        seed_bundle=seed_bundle,
    )


def _coerce_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return float(default)
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _normalize_mapping_like(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    if hasattr(value, "model_dump"):
        dumped = value.model_dump()
        if isinstance(dumped, Mapping):
            return dict(dumped)
    return {}


__all__ = ["build_validation_context"]
