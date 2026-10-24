"""Human approval contracts.

The AI recommendation and the human decision are deliberately separate fields so the
dashboard can never conflate them.
"""

from datetime import datetime

from pydantic import BaseModel, Field

from .enums import AgentName, HumanDecision, ReasonCode, Recommendation, RiskLevel


class ApprovalRequest(BaseModel):
    approval_id: str = Field(..., pattern=r"^APR-\d{3,}$", examples=["APR-001"])
    invoice_id: str
    correlation_id: str
    requested_by: AgentName
    recommendation: Recommendation
    recommendation_confidence: float = Field(..., ge=0.0, le=1.0)
    risk_level: RiskLevel
    reason_codes: list[ReasonCode]
    evidence_ids: list[str]
    requested_at: datetime
    expires_at: datetime | None = Field(
        None, description="Timeout → remains blocked, never auto-approves"
    )

    reviewer: str | None = None
    human_decision: HumanDecision | None = None
    reviewer_note: str | None = None
    decided_at: datetime | None = None


class HumanDecisionInput(BaseModel):
    """Body of POST /invoices/{id}/approve and /reject."""

    reviewer: str = Field(..., min_length=1, examples=["finance.reviewer@example.com"])
    note: str | None = Field(None, max_length=500)
