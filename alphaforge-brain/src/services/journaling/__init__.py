"""Journaling services package.

Phase 016 introduces enriched journaling pipelines and helpers. Modules in
this package must respect deterministic hashing requirements (Decision 4)
while targeting the `zz_artifacts/journaling` root.
"""

from __future__ import annotations

from models.journaling_aggregate import JournalingAggregate

from .artifact_paths import JOURNALING_ROOT, resolve_journaling_root
from .enrichment import JournalingArtifacts, prepare_enriched_payload
from .writer import JournalingWriteResult, write_journaling_artifacts

__all__ = [
    "JOURNALING_ROOT",
    "resolve_journaling_root",
    "JournalingArtifacts",
    "JournalingAggregate",
    "prepare_enriched_payload",
    "JournalingWriteResult",
    "write_journaling_artifacts",
]
