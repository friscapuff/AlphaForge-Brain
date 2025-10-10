from __future__ import annotations

import argparse
from dataclasses import dataclass
from typing import Mapping, Sequence, cast

from ...infra.utils.hash import hash_canonical

DEFAULT_VALIDATION_MODULES = (
    "permutation",
    "dsr",
    "psr",
    "purged_kfold",
    "cpcv",
    "realism",
)


@dataclass(frozen=True)
class ValidationConfigFlags:
    modules: list[str]
    permutation_count: int
    significance_threshold: float
    leakage_threshold: float
    capacity_limit_bps: float

    def to_manifest_fragment(self) -> dict[str, object]:
        return {
            "modules": list(self.modules),
            "permutation_count": self.permutation_count,
            "significance_threshold": self.significance_threshold,
            "leakage_threshold": self.leakage_threshold,
            "capacity_limit_bps": self.capacity_limit_bps,
        }

    def stable_hash(self) -> str:
        return cast(
            str,
            hash_canonical(
                {
                    "modules": self.modules,
                    "permutation_count": self.permutation_count,
                    "significance_threshold": self.significance_threshold,
                    "leakage_threshold": self.leakage_threshold,
                    "capacity_limit_bps": self.capacity_limit_bps,
                }
            ),
        )


def resolve_validation_config(
    cli_args: Sequence[str],
    env: Mapping[str, str],
) -> ValidationConfigFlags:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--validation-modules")
    parser.add_argument("--permutation-count", type=int)
    parser.add_argument("--significance-threshold", type=float)
    parser.add_argument("--leakage-threshold", type=float)
    parser.add_argument("--capacity-limit-bps", type=float)

    parsed, _ = parser.parse_known_args(cli_args)

    modules: list[str] = list(DEFAULT_VALIDATION_MODULES)
    env_modules = env.get("AF_VALIDATION_MODULES")
    if env_modules:
        modules = _normalize_modules(env_modules)

    if parsed.validation_modules:
        modules = _normalize_modules(parsed.validation_modules)

    permutation_count = _resolve_int(
        parsed.permutation_count,
        env.get("AF_VALIDATION_PERMUTATION_COUNT"),
        default=500,
    )
    significance_threshold = _resolve_float(
        parsed.significance_threshold,
        env.get("AF_VALIDATION_SIGNIFICANCE_THRESHOLD"),
        default=0.01,
    )
    leakage_threshold = _resolve_float(
        parsed.leakage_threshold,
        env.get("AF_LEAKAGE_THRESHOLD"),
        default=0.1,
    )
    capacity_limit_bps = _resolve_float(
        parsed.capacity_limit_bps,
        env.get("AF_REALISM_CAPACITY_BPS_LIMIT"),
        default=500.0,
    )

    return ValidationConfigFlags(
        modules=list(modules),
        permutation_count=permutation_count,
        significance_threshold=significance_threshold,
        leakage_threshold=leakage_threshold,
        capacity_limit_bps=float(capacity_limit_bps),
    )


def _normalize_modules(value: str) -> list[str]:
    modules = [part.strip().lower() for part in value.split(",") if part.strip()]
    return sorted(dict.fromkeys(modules))


def _resolve_int(cli_value: int | None, env_value: str | None, *, default: int) -> int:
    if cli_value is not None:
        return cli_value
    if env_value:
        try:
            return int(env_value)
        except ValueError:
            pass
    return default


def _resolve_float(
    cli_value: float | None,
    env_value: str | None,
    *,
    default: float,
) -> float:
    if cli_value is not None:
        return cli_value
    if env_value:
        try:
            return float(env_value)
        except ValueError:
            pass
    return default
