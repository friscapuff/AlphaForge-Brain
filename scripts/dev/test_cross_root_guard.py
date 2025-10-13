#!/usr/bin/env python3
"""Cross-root import guard smoke test.

This script installs the runtime import guard and attempts to import a forbidden
module from the Mind root. It records the outcome to the governance audit log
and a dedicated artifact for quickstart validation.
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter

from services.audit.governance_logger import append_audit_log, record_governance_event

from infra.import_guard import CrossRootImportError, install_import_guard

ARTIFACT_PATH = Path("zz_artifacts/governance/import_guard_smoke.jsonl")


def _persist_outcome(message: str, details: dict[str, object]) -> None:
    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "message": message,
        "details": details,
    }
    append_audit_log(payload=payload, audit_path=ARTIFACT_PATH)
    record_governance_event(message=message, details=details)


def main() -> int:
    start = perf_counter()
    install_import_guard()
    try:
        __import__("alphaforge_mind.prohibited_probe")
    except CrossRootImportError as exc:
        duration_ms = int((perf_counter() - start) * 1000)
        details = {
            "status": "blocked",
            "duration_ms": duration_ms,
            "threshold_ms": 1000,
            "within_sla": duration_ms <= 1000,
            "module": exc.module,
            "importer": exc.importer,
        }
        _persist_outcome("import_guard.smoke", details)
        print("✅ Cross-root import guard blocked forbidden import.")
        return 0
    except ImportError as exc:  # pragma: no cover - unexpected path
        duration_ms = int((perf_counter() - start) * 1000)
        details = {
            "status": "unexpected_import_error",
            "duration_ms": duration_ms,
            "threshold_ms": 1000,
            "within_sla": duration_ms <= 1000,
            "module": "alphaforge_mind.prohibited_probe",
            "error": str(exc),
        }
        _persist_outcome("import_guard.smoke_failure", details)
        print(
            "⚠️ Cross-root import guard did not intercept; received generic ImportError.",
            file=sys.stderr,
        )
        return 1
    else:  # pragma: no cover - indicates guard failure
        duration_ms = int((perf_counter() - start) * 1000)
        details = {
            "status": "failed",
            "duration_ms": duration_ms,
            "threshold_ms": 1000,
            "within_sla": duration_ms <= 1000,
            "module": "alphaforge_mind.prohibited_probe",
        }
        _persist_outcome("import_guard.smoke_failure", details)
        print("❌ Import guard failed to block the forbidden import.", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
