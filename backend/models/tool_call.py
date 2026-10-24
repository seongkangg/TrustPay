"""Tool call contract.

Agents never call tools directly. They submit a `ToolCallRequest` to the governance
layer, which checks the allowlist, executes (or blocks) the call, and records a `ToolCall`.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator

from backend.utils.timestamps import as_utc

from .enums import AgentName, Authorization, ReasonCode, ToolName


class ToolCallRequest(BaseModel):
    agent: AgentName
    tool: ToolName
    purpose: str = Field(..., min_length=5, description="Why the agent needs this call")
    parameters: dict[str, Any] = Field(default_factory=dict)
    invoice_id: str
    correlation_id: str


class ToolCall(BaseModel):
    tool_call_id: str = Field(..., pattern=r"^TOOL-\d{3,}$", examples=["TOOL-001"])
    invoice_id: str
    correlation_id: str
    agent: AgentName
    tool: ToolName
    purpose: str
    parameters: dict[str, Any] = Field(default_factory=dict)
    is_write: bool = Field(False, description="Mutating operations require stricter authorization")
    authorization: Authorization
    denial_reason: ReasonCode | None = None
    result_summary: str | None = Field(None, description="Human-readable, masked summary")
    evidence_id: str | None = Field(
        None, description="ID agents cite as evidence, e.g. VENDOR-LOOKUP-14"
    )
    latency_ms: int | None = Field(None, ge=0)
    timestamp: datetime

    _utc = field_validator("timestamp")(classmethod(lambda cls, v: as_utc(v)))
