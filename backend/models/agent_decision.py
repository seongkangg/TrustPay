"""Agent decision contract.

Every agent output is one of these. The governance layer's `decision_validator`
rejects any decision whose `evidence_ids` do not reference real tool calls or scans,
or whose `explanation` contains unmasked sensitive values.
"""

from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from backend.utils.timestamps import as_utc

from .enums import AgentName, Authorization, ReasonCode, Recommendation, RiskLevel

# Below this, the governance layer escalates with LOW_CONFIDENCE regardless of outcome.
CONFIDENCE_THRESHOLD = 0.75


class Explanation(BaseModel):
    """Structured 'why' shown next to every major decision in the dashboard."""

    decision: str
    reasons: list[str] = Field(default_factory=list)
    evidence: list[str] = Field(
        default_factory=list, description="Evidence IDs, e.g. VENDOR-LOOKUP-14"
    )
    policy_rules_triggered: list[str] = Field(default_factory=list, description="e.g. POLICY-003")
    missing_information: list[str] = Field(default_factory=list)
    recommended_next_step: str | None = None


class AgentDecision(BaseModel):
    decision_id: str = Field(..., pattern=r"^DEC-\d{3,}$", examples=["DEC-001"])
    invoice_id: str
    correlation_id: str
    agent: AgentName
    decision: str = Field(
        ..., description="Agent-specific outcome, e.g. 'vendor_unverified', 'fields_extracted'"
    )
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Advisory only; never overrides policy"
    )
    risk_level: RiskLevel | None = None
    recommendation: Recommendation | None = None
    reason_codes: list[ReasonCode] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    explanation: Explanation
    governance_result: Authorization | None = Field(
        None, description="Set by the governance layer after validation"
    )
    timestamp: datetime

    _utc = field_validator("timestamp")(classmethod(lambda cls, v: as_utc(v)))
