"""Cross-root integrity check.

Fails if:
- `alphaforge-brain` imports from `alphaforge_mind` (placeholder) directly.
- (Future) `alphaforge-mind` imports non-contract internals from brain.

Current implementation: placeholder scanning for forbidden patterns so migration
can land before Mind implementation exists.
"""

from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]

FORBIDDEN_SUBSTRINGS = [
    "from alphaforge_mind",  # brain importing mind (mind not yet implemented)
    "import alphaforge_mind",  # direct import
]


def scan() -> int:
    brain_src = ROOT / "alphaforge-brain" / "src"
    if not brain_src.exists():
        print("[WARN] alphaforge-brain/src not present yet; skipping scan")
        return 0
    violations: list[str] = []
    for py in brain_src.rglob("*.py"):
        try:
            text = py.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for token in FORBIDDEN_SUBSTRINGS:
            if token in text:
                rel = py.relative_to(ROOT)
                violations.append(f"{rel}: contains forbidden token '{token}'")
    if violations:
        print("Cross-root Integrity Violations Detected:")
        for v in violations:
            print(" - " + v)
        return 1
    print("Cross-root integrity check: PASS")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(scan())
