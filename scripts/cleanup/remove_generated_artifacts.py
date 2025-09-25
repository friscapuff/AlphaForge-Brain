"""
Remove known generated/transient artifacts from the repo root.

This script is intended to run locally pre-commit to keep the working tree clean.
It removes files if they exist (ignoring errors), and prints a summary.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def main() -> int:
    patterns = [
        "coverage.xml",
        "typing_timing.json",
        "typing_timing.md",
        "mypy_baseline.txt",
        "mypy_final.txt",
        "mypy_diff.md",
        "diff_test.md",
        "virt_report.json",
        # glob patterns handled below
        "base-*.yaml",
        "head-*.json",
    ]

    removed: list[Path] = []

    for pat in patterns:
        # Treat simple names and glob patterns uniformly
        for p in ROOT.glob(pat):
            try:
                if p.is_file():
                    p.unlink(missing_ok=True)  # type: ignore[arg-type]
                    removed.append(p)
            except Exception:
                # Best-effort cleanup; continue
                pass

    if removed:
        print("Removed generated artifacts:")
        for p in removed:
            try:
                rel = p.relative_to(ROOT)
            except Exception:
                rel = p
            print(f" - {rel}")
    else:
        print("No generated artifacts found to remove.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
