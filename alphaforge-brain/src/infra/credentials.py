from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Credential:
    key: str
    value: str


def get_env_credential(key: str, *, default: str | None = None) -> Credential | None:
    """Return credential from environment if present.

    Parameters
    - key: environment variable name
    - default: optional default value

    Returns a Credential if found or default provided; otherwise None.
    """
    val = os.getenv(key, default)
    if val is None:
        return None
    return Credential(key=key, value=val)
