"""Deterministic signatures for validation manifest payloads."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, cast

from infra.utils.hash import hash_canonical


def compute_validation_manifest_hash(payload: Mapping[str, Any] | None) -> str | None:
    """Return a canonical hash for a validation manifest payload.

    The payload is expected to match the structure emitted by
    ``services.validation.manifest_v2.build_validation_payload``. The hash
    covers both the manifest fragment and the artifact index so that any
    change to validation outputs or their backing files is reflected while
    historical runs without schema v2 payloads remain unaffected (returning
    ``None``).
    """

    if not isinstance(payload, Mapping):
        return None

    manifest = payload.get("manifest")
    if not isinstance(manifest, Mapping):
        return None

    normalized_manifest = _normalize_manifest(manifest)

    artifacts = payload.get("artifacts")
    normalized_artifacts = _normalize_artifacts(artifacts)

    modules = _normalize_optional_mapping(payload.get("modules"))
    config = _normalize_optional_mapping(payload.get("config"))
    permutation = _normalize_permutation_section(payload.get("permutation"))
    bias_adjustments = _normalize_optional_mapping(payload.get("bias_adjustments"))
    cross_validation = _normalize_cross_validation_section(
        payload.get("cross_validation")
    )
    execution_realism = _normalize_execution_realism_section(
        payload.get("execution_realism")
    )
    metadata = _normalize_metadata_section(payload.get("metadata"))
    failed_checks = _normalize_checks(payload.get("failed_checks"))
    caution_checks = _normalize_checks(payload.get("caution_checks"))

    signature_source: dict[str, Any] = {"manifest": normalized_manifest}
    if normalized_artifacts:
        signature_source["artifacts"] = normalized_artifacts
    if isinstance(payload.get("significance_status"), str):
        signature_source["significance_status"] = str(payload["significance_status"])
    if modules:
        signature_source["modules"] = modules
    if config:
        signature_source["config"] = config
    if permutation:
        signature_source["permutation"] = permutation
    if bias_adjustments:
        signature_source["bias_adjustments"] = bias_adjustments
    if cross_validation:
        signature_source["cross_validation"] = cross_validation
    if execution_realism:
        signature_source["execution_realism"] = execution_realism
    if metadata:
        signature_source["metadata"] = metadata
    if failed_checks:
        signature_source["failed_checks"] = failed_checks
    if caution_checks:
        signature_source["caution_checks"] = caution_checks

    # Guard against recursive fields being included in the signature source.
    signature_source.pop("manifest_hash", None)

    return hash_canonical(signature_source)


def _normalize_manifest(manifest: Mapping[str, Any]) -> dict[str, Any]:
    normalized: dict[str, Any] = {
        key: _normalize(value) for key, value in manifest.items()
    }

    permutation_summary = normalized.get("permutation_summary")
    if isinstance(permutation_summary, Mapping):
        segments = permutation_summary.get("segments")
        if isinstance(segments, list):
            segments.sort(
                key=lambda seg: (
                    str(seg.get("segment_id", "")),
                    hash_canonical(seg),
                )
            )

    cross_validation = normalized.get("cross_validation")
    if isinstance(cross_validation, Mapping):
        folds = cross_validation.get("folds")
        if isinstance(folds, list):
            folds.sort(
                key=lambda fold: (
                    str(fold.get("fold_id", "")),
                    hash_canonical(fold),
                )
            )

    execution_realism = normalized.get("execution_realism")
    if isinstance(execution_realism, Mapping):
        execution_realism_dict = cast(dict[str, Any], execution_realism)
        _sort_string_list(execution_realism_dict, "warnings")
        normalized["execution_realism"] = execution_realism_dict

    return normalized


def _normalize_artifacts(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, Mapping):
        return []
    entries: list[dict[str, Any]] = []
    for rel_path, meta in value.items():
        if not isinstance(meta, Mapping):
            continue
        entry = {
            "path": str(rel_path),
            "sha256": meta.get("sha256"),
            "size": meta.get("size"),
        }
        entries.append(entry)
    entries.sort(key=lambda item: item["path"])
    return entries


def _normalize(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _normalize(value[key]) for key in sorted(value)}
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [_normalize(item) for item in value]
    return value


def _normalize_optional_mapping(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        return {}
    return cast(dict[str, Any], _normalize(value))


def _normalize_checks(value: Any) -> list[str]:
    if isinstance(value, (list, tuple, set)):
        normalised = [str(item) for item in value if item is not None]
        normalised.sort()
        return normalised
    return []


def _normalize_permutation_section(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        return {}
    normalised: dict[str, Any] = cast(dict[str, Any], _normalize(value))
    segments = normalised.get("segments")
    if isinstance(segments, list):
        segments.sort(
            key=lambda seg: (
                str(seg.get("segment_id", "")),
                hash_canonical(seg),
            )
        )
    return normalised


def _normalize_cross_validation_section(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        return {}
    normalised: dict[str, Any] = cast(dict[str, Any], _normalize(value))
    folds = normalised.get("folds")
    if isinstance(folds, list):
        folds.sort(
            key=lambda fold: (
                str(fold.get("fold_id", "")),
                hash_canonical(fold),
            )
        )
    return normalised


def _normalize_execution_realism_section(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        return {}
    normalised: dict[str, Any] = cast(dict[str, Any], _normalize(value))
    _sort_string_list(normalised, "warnings")
    _sort_string_list(normalised, "guidance")
    return normalised


def _normalize_metadata_section(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        return {}
    normalised: dict[str, Any] = cast(dict[str, Any], _normalize(value))
    _sort_mapping_list(
        normalised, "permutation_shortfalls", ("segment_id", "requested", "executed")
    )
    _sort_mapping_list(normalised, "permutation_fallbacks", ("segment_id", "reason"))
    return normalised


def _sort_string_list(container: dict[str, Any], key: str) -> None:
    values = container.get(key)
    if isinstance(values, list):
        container[key] = sorted(str(item) for item in values)


def _sort_mapping_list(
    container: dict[str, Any],
    key: str,
    fields: tuple[str, ...],
) -> None:
    values = container.get(key)
    if not isinstance(values, list):
        return

    def _sort_key(item: Mapping[str, Any]) -> tuple[Any, ...]:
        extracted = [str(item.get(field, "")) for field in fields]
        extracted.append(hash_canonical(item))
        return tuple(extracted)

    container[key] = sorted(
        [
            cast(dict[str, Any], _normalize(entry))
            for entry in values
            if isinstance(entry, Mapping)
        ],
        key=_sort_key,
    )


__all__ = ["compute_validation_manifest_hash"]
