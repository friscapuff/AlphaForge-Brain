from __future__ import annotations

import pytest

from domain.schemas.artifacts import ArtifactEntry, ArtifactManifest

# Will fail until implemented
from domain.schemas.metrics import MetricsSummary


def test_metrics_summary_defaults() -> None:
    ms = MetricsSummary()
    assert ms.trades == 0
    assert ms.returns_total == 0.0


def test_metrics_summary_custom() -> None:
    ms = MetricsSummary(trades=10, returns_total=0.12, sharpe=1.5, max_drawdown=-0.2)
    assert ms.trades == 10
    assert ms.max_drawdown < 0


def test_artifact_manifest_entry() -> None:
    e = ArtifactEntry(name="equity_curve.json", kind="equity_curve", sha256="abc", bytes=123)
    assert e.bytes == 123


def test_artifact_manifest_hash_stability() -> None:
    m1 = ArtifactManifest(entries=[ArtifactEntry(name="metrics.json", kind="metrics", sha256="dead", bytes=50)])
    m2 = ArtifactManifest(entries=[ArtifactEntry(name="metrics.json", kind="metrics", sha256="dead", bytes=50)])
    assert m1.canonical_hash() == m2.canonical_hash()


def test_artifact_manifest_duplicate_name_rejected() -> None:
    with pytest.raises(ValueError):
        ArtifactManifest(entries=[
            ArtifactEntry(name="a.txt", kind="metrics", sha256="1", bytes=1),
            ArtifactEntry(name="a.txt", kind="equity", sha256="2", bytes=2),
        ])
