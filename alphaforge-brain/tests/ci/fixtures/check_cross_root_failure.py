#!/usr/bin/env python3
from __future__ import annotations

import sys


def main() -> int:
    print("cross-root integrity check failed: fixture mismatch", file=sys.stdout)
    return 4


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
