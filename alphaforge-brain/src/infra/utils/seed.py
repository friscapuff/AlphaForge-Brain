from __future__ import annotations

import hashlib


def derive_seed(root: int, *, namespace: str, index: int = 0) -> int:
    """Derive a deterministic uint32 seed from root, namespace, and index.

    Formula: sha256(f"{root}|{namespace}|{index}") mod 2**32
    """
    material = f"{int(root)}|{namespace}|{int(index)}".encode()
    h = hashlib.sha256(material).digest()
    return int.from_bytes(h[:4], "big", signed=False)


__all__ = ["derive_seed"]
