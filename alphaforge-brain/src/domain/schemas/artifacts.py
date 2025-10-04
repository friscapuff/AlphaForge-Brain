from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, model_validator

from infra.utils.hash import canonical_json, hash_canonical


class ArtifactEntry(BaseModel):
    name: str
    kind: str
    sha256: str
    bytes: int


class ArtifactManifest(BaseModel):
    entries: list[ArtifactEntry] = Field(default_factory=list)
    # Optional hash of previous manifest (integrity chain). When present, it
    # represents the canonical hash (ArtifactManifest.canonical_hash()) of
    # the previous run's manifest at the time it was finalized.
    chain_prev: str | None = None
    # Dataset characteristics for reproducibility / provenance (added T017)
    data_hash: str | None = None
    calendar_id: str | None = None
    # Phase J (G06): symbol & timeframe enrichment (additive, nullable for backward compatibility)
    symbol: str | None = None
    timeframe: str | None = None

    @model_validator(mode="after")
    def _unique_names(self) -> ArtifactManifest:
        names = [e.name for e in self.entries]
        if len(names) != len(set(names)):
            raise ValueError("Duplicate artifact name detected")
        return self

    def canonical_dict(self) -> dict[str, Any]:
        # Sort entries by name for stable hashing; include chain_prev when set
        entries_list: list[dict[str, Any]] = [
            e.model_dump(mode="python")
            for e in sorted(self.entries, key=lambda x: x.name)
        ]
        base: dict[str, Any] = {"entries": entries_list}
        if self.chain_prev is not None:
            base["chain_prev"] = self.chain_prev
        if self.data_hash is not None:
            base["data_hash"] = self.data_hash
        if self.calendar_id is not None:
            base["calendar_id"] = self.calendar_id
        if self.symbol is not None:
            base["symbol"] = self.symbol
        if self.timeframe is not None:
            base["timeframe"] = self.timeframe
        return base

    def canonical_hash(self) -> str:
        h: str = hash_canonical(self.canonical_dict())
        return h

    def canonical_json(self) -> str:
        s: str = canonical_json(self.canonical_dict())
        return s


__all__: list[str] = ["ArtifactEntry", "ArtifactManifest"]
