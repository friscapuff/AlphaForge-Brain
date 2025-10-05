from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

import requests

API_VERSION = "0.1"
DEFAULT_TIMEOUT = 30


@dataclass(slots=True)
class RunSubmission:
    run_hash: str
    created: bool
    status: str


class AlphaForgeMindClient:
    """Thin deterministic client for AlphaForge Brain API (v0.1).

    Provides minimal convenience wrappers; avoids hidden retries to preserve
    deterministic timing characteristics for tests.
    """

    def __init__(
        self,
        base_url: str,
        timeout: float = DEFAULT_TIMEOUT,
        session: Any | None = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        # Accept either requests module, a requests.Session, or FastAPI TestClient (compatible API)
        self._session = session or requests

    # --- Core Runs API ---
    def submit_run(self, config: dict[str, Any]) -> RunSubmission:
        r = self._session.post(
            f"{self.base_url}/runs", json=config, timeout=self.timeout
        )
        r.raise_for_status()
        data = r.json()
        return RunSubmission(
            run_hash=data["run_hash"],
            created=data.get("created", True),
            status=data.get("status", ""),
        )

    def get_run(self, run_hash: str) -> dict[str, Any]:
        r = self._session.get(f"{self.base_url}/runs/{run_hash}", timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def list_artifacts(self, run_hash: str) -> list[dict[str, Any]]:
        r = self._session.get(
            f"{self.base_url}/runs/{run_hash}/artifacts", timeout=self.timeout
        )
        r.raise_for_status()
        body = r.json()
        return body.get("files", [])

    def pin(self, run_hash: str, reason: str | None = None) -> dict[str, Any]:
        payload = {"reason": reason} if reason else {}
        r = self._session.post(
            f"{self.base_url}/runs/{run_hash}/pin", json=payload, timeout=self.timeout
        )
        r.raise_for_status()
        return r.json()

    def unpin(self, run_hash: str) -> dict[str, Any]:
        r = self._session.post(
            f"{self.base_url}/runs/{run_hash}/unpin", timeout=self.timeout
        )
        r.raise_for_status()
        return r.json()

    def rehydrate(self, run_hash: str) -> dict[str, Any]:
        r = self._session.post(
            f"{self.base_url}/runs/{run_hash}/rehydrate", timeout=self.timeout
        )
        r.raise_for_status()
        return r.json()

    def restore(self, run_hash: str) -> dict[str, Any]:
        """Attempt cold storage restore (no-op if already full)."""
        r = self._session.post(
            f"{self.base_url}/runs/{run_hash}/restore", timeout=self.timeout
        )
        r.raise_for_status()
        return r.json()

    # --- Retention Settings & Planning ---
    def get_retention_settings(self) -> dict[str, Any]:
        r = self._session.get(
            f"{self.base_url}/settings/retention", timeout=self.timeout
        )
        r.raise_for_status()
        return r.json()

    def update_retention_settings(self, **kwargs: Any) -> dict[str, Any]:
        # kwargs allowed: keep_last, top_k_per_strategy, max_full_bytes
        body = {k: v for k, v in kwargs.items() if v is not None}
        r = self._session.post(
            f"{self.base_url}/settings/retention", json=body, timeout=self.timeout
        )
        r.raise_for_status()
        return r.json()

    def get_retention_metrics(self) -> dict[str, Any]:
        r = self._session.get(
            f"{self.base_url}/retention/metrics", timeout=self.timeout
        )
        r.raise_for_status()
        return r.json()

    def get_retention_plan(self) -> dict[str, Any]:
        r = self._session.get(f"{self.base_url}/retention/plan", timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def diff_retention_plan(self, **overrides: Any) -> dict[str, Any]:
        body = {k: v for k, v in overrides.items() if v is not None}
        r = self._session.post(
            f"{self.base_url}/retention/plan/diff", json=body, timeout=self.timeout
        )
        r.raise_for_status()
        return r.json()

    def apply_retention(self) -> dict[str, Any]:
        r = self._session.post(
            f"{self.base_url}/runs/retention/apply", timeout=self.timeout
        )
        r.raise_for_status()
        return r.json()

    # --- Events (legacy snapshot stream) ---
    def stream_events(
        self, run_hash: str, after_id: int | None = None
    ) -> list[dict[str, Any]]:
        params = {} if after_id is None else {"after_id": after_id}
        r = self._session.get(
            f"{self.base_url}/runs/{run_hash}/events",
            params=params,
            timeout=self.timeout,
        )
        if r.status_code == 304:
            return []
        r.raise_for_status()
        # Parse SSE text body into list of {id,event,data}
        events: list[dict[str, Any]] = []
        current: dict[str, Any] = {}
        for line in r.text.splitlines():
            if not line.strip():
                if current:
                    events.append(current)
                    current = {}
                continue
            if line.startswith("id: "):
                current["id"] = int(line[4:].strip())
            elif line.startswith("event: "):
                current["event"] = line[7:].strip()
            elif line.startswith("data: "):
                try:
                    payload = json.loads(line[6:])
                except json.JSONDecodeError:
                    payload = line[6:]
                current["data"] = payload
        if current:
            events.append(current)
        return events


__all__ = ["AlphaForgeMindClient", "RunSubmission"]
