from __future__ import annotations

try:  # Support both package and module style import during early development
    from .client import AlphaForgeMindClient
except Exception:  # pragma: no cover - fallback when not a package
    from client import AlphaForgeMindClient  # type: ignore[no-redef]
from functools import lru_cache


@lru_cache(maxsize=1)
def get_client(base_url: str = "http://testserver") -> AlphaForgeMindClient:
    # For tests we rely on FastAPI TestClient mount; in integration a different base_url is provided.
    return AlphaForgeMindClient(base_url=base_url)


__all__ = ["AlphaForgeMindClient", "get_client"]
