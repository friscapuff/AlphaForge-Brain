"""CI type-check entrypoint (T085).

Runs mypy over src/ and tests/ and exits non-zero on any error.
Captures simple timing & error count summary so we can persist a baseline hash/timing
in typing_timing.json (updated manually after gate passes).
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def run_mypy() -> dict[str, Any]:
    start = time.perf_counter()
    proc = subprocess.run(
        ["poetry", "run", "mypy", "src", "tests"], capture_output=True, text=True
    )
    duration = time.perf_counter() - start
    stdout = proc.stdout
    stderr = proc.stderr
    errors = 0
    for line in stdout.splitlines():
        if line.strip().endswith("error") or ": error:" in line:
            errors += 1
    result: dict[str, Any] = {
        "duration_sec": round(duration, 3),
        "return_code": proc.returncode,
        "errors_detected": errors,
    }
    print(json.dumps(result))
    if proc.returncode != 0:
        # Echo mypy output for developer visibility
        sys.stderr.write(stdout)
        sys.stderr.write(stderr)
    return result


def main() -> None:
    res = run_mypy()
    if res["return_code"] != 0:
        raise SystemExit(1)


if __name__ == "__main__":  # pragma: no cover
    main()
