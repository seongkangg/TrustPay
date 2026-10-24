"""Audit event contract.

The audit trail is append-only. Each event stores the hash of the previous event for
the same invoice, so tampering or gaps are detectable. Duplicate `event_id`s are
rejected; out-of-order arrivals are flagged (`out_of_order=True`) rather than reordered.
"""

from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from backend.utils.timestamps import as_utc

from .enums import AgentName, Authorization, EventType, ReasonCode, Severity


class AuditEvent(BaseModel):
    event_id: str = Field(..., pattern=r"^EVT-\d{3,}$", examples=["EVT-001"])
    invoice_id: str
    correlation_id: str
    sequence: int = Field(..., ge=1, description="Per-invoice monotonic counter")
    event_type: EventType
    severity: Severity
    actor: AgentName
    reason_codes: list[ReasonCode] = Field(default_factory=list)
    policy_result: Authorization | None = None
    input_summary: str | None = Field(None, description="Masked")
    output_summary: str | None = Field(None, description="Masked")
    evidence_refs: list[str] = Field(default_factory=list)
    related_decision_id: str | None = None
    related_tool_call_id: str | None = None
    previous_event_hash: str | None = Field(
        None, description="SHA-256 of prior event; null for first"
    )
    event_hash: str = Field(..., description="SHA-256 over this event's canonical fields")
    out_of_order: bool = False
    timestamp: datetime

    _utc = field_validator("timestamp")(classmethod(lambda cls, v: as_utc(v)))


class AuditTrail(BaseModel):
    invoice_id: str
    events: list[AuditEvent]
    chain_valid: bool = Field(..., description="True when every previous_event_hash matches")
