"""Clock ledger data model (architecture-spec.md §5), adapted for the
document-date-discrepancy scope: no lawful-status computation, arithmetic
and attorney-review flags only.
"""

from typing import Any, Literal

from pydantic import BaseModel, Field

ClockState = Literal["quiet", "window_open", "action_drafted", "awaiting_user", "resolved"]


class SourceDoc(BaseModel):
    type: str
    parsed_fields: dict[str, Any] = Field(default_factory=dict)
    storage_ref: str | None = None


class Clock(BaseModel):
    clock_id: str
    user_id: str
    module: Literal["immigration", "recalls"]
    rule_id: str
    state: ClockState
    source_docs: list[SourceDoc] = Field(default_factory=list)
    derived: dict[str, Any] = Field(default_factory=dict)
    watch: dict[str, Any] = Field(default_factory=dict)


class Event(BaseModel):
    """A feed event (bulletin published, recall published). Stable
    event_id + rule_version make replay-safe deduplication possible.
    """

    event_id: str
    source: str
    effective_date: str
    rule_version: str
    payload: dict[str, Any] = Field(default_factory=dict)


class Alert(BaseModel):
    clock_id: str
    event_id: str
    rule_version: str
    decision: Literal["surfaced", "silent"]
    reason: str = ""

    def dedup_key(self) -> str:
        return f"{self.clock_id}:{self.event_id}:{self.rule_version}"
