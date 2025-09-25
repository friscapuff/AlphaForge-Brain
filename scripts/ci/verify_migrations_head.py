from __future__ import annotations

import hashlib
from importlib import resources

PACKAGE = "infra.migrations"


def normalize_sql(sql: str) -> str:
    lines = []
    for line in sql.splitlines():
        s = line.strip()
        if not s or s.startswith("--"):
            continue
        lines.append(s)
    return "\n".join(lines)


def compute_head_checksum() -> tuple[str, str]:
    # returns (head_id, sha256)
    files = [
        e.name for e in resources.files(PACKAGE).iterdir() if e.name.endswith(".sql")
    ]
    files.sort()
    head = files[-1] if files else ""
    blob = "\n\n".join(
        normalize_sql(resources.files(PACKAGE).joinpath(f).read_text(encoding="utf-8"))
        for f in files
    )
    sha = hashlib.sha256(blob.encode("utf-8")).hexdigest()
    return head.rsplit(".", 1)[0], sha


if __name__ == "__main__":
    head, sha = compute_head_checksum()
    print(f"HEAD={head}")
    print(f"SHA256={sha}")
