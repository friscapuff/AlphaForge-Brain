#!/usr/bin/env python3
from __future__ import annotations

import sys


def main() -> int:
    print("MIGRATIONS HEAD MISMATCH: fixtures simulated failure", file=sys.stdout)
    return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
