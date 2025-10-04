from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class BaseModelStrict(BaseModel):
    """Base Pydantic model enforcing immutability & assignment validation.

    Matches plan requirement for frozen models & strict typing.
    Extend this for all domain entities (RunConfig, Trade, etc.).
    """

    model_config = ConfigDict(frozen=True, validate_assignment=True, extra="forbid")
