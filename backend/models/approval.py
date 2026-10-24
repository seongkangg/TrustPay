"""Human approval contracts.

The AI recommendation and the human decision are deliberately separate fields so the
dashboard can never conflate them.
"""

from datetime import datetime
from typing import Optional

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
    expires_at: Optional[datetime] = Field(None, description="Timeout → remains blocked, never auto-approves")

    reviewer: Optional[str] = None
    human_decision: Optional[HumanDecision] = None
    reviewer_note: Optional[str] = None
    decided_at: Optional[datetime] = None


class HumanDecisionInput(BaseModel):
    """Body of POST /invoices/{id}/approve and /reject."""

    reviewer: str = Field(..., min_length=1, examples=["finance.reviewer@example.com"])
    note: Optional[str] = Field(None, max_length=500)
