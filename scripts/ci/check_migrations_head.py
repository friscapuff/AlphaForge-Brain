from __future__ import annotations

import sys
from pathlib import Path

from verify_migrations_head import compute_head_checksum

HERE = Path(__file__).parent
TRACK = HERE / "MIGRATIONS_HEAD.txt"


def parse_tracking(fp: Path) -> tuple[str, str]:
    head = ""
    sha = ""
    for line in fp.read_text(encoding="utf-8").splitlines():
        if line.startswith("HEAD="):
            head = line.split("=", 1)[1].strip()
        elif line.startswith("SHA256="):
            sha = line.split("=", 1)[1].strip()
    return head, sha


def main() -> int:
    exp_head, exp_sha = parse_tracking(TRACK)
    head, sha = compute_head_checksum()
    ok = (head == exp_head) and (sha == exp_sha)
    if not ok:
        print(f"EXPECTED {exp_head} {exp_sha}\nACTUAL   {head} {sha}")
        return 2
    print(f"OK {head} {sha}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
