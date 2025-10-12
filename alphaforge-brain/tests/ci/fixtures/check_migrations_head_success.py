#!/usr/bin/env python3
from __future__ import annotations

import sys


def main() -> int:
    print("MIGRATIONS HEAD OK: fixture success", file=sys.stdout)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
