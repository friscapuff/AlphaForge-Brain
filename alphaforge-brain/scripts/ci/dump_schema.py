# ruff: noqa: E402
#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Ensure package path available when running as a script
SYS_ROOT = Path(__file__).resolve().parents[2] / "src"
if str(SYS_ROOT) not in sys.path:
    sys.path.insert(0, str(SYS_ROOT))

from src.infra.db import get_connection


def dump_schema() -> str:
    with get_connection() as conn:
        cur = conn.execute(
            """
            SELECT name, type, sql
            FROM sqlite_master
            WHERE type IN ('table','index','view','trigger') AND name NOT LIKE 'sqlite_%'
            ORDER BY type, name
            """
        )
        rows = list(cur.fetchall())
    parts: list[str] = []
    for row in rows:
        name = row[0]
        typ = row[1]
        sql = row[2]
        if not isinstance(sql, str):
            continue
        parts.append(f"-- {typ}: {name}\n{sql.strip()};\n")
    return "\n".join(parts)


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Dump SQLite schema DDL for artifact review (FR-153)"
    )
    ap.add_argument("--out", type=str, default="zz_artifacts/schema.sql")
    args = ap.parse_args()

    ddl = dump_schema()
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(ddl, encoding="utf-8")
    print(f"Schema written: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
