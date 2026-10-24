"""ORM tables mirroring the Pydantic contracts in backend/models/.

`audit_events` is append-only: nothing in the codebase updates or deletes rows there.
List/dict fields are stored as JSON columns to keep the prototype simple.
"""

from datetime import date, datetime

from sqlalchemy import JSON, Boolean, Date, DateTime, Float, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from backend.database.database import Base


class InvoiceRow(Base):
    __tablename__ = "invoices"

    invoice_id: Mapped[str] = mapped_column(String, primary_key=True)
    correlation_id: Mapped[str] = mapped_column(String, index=True)
    vendor_invoice_number: Mapped[str] = mapped_column(String, index=True)
    vendor_id: Mapped[str | None] = mapped_column(String, index=True, nullable=True)
    vendor_name: Mapped[str | None] = mapped_column(String, nullable=True)
    amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    currency: Mapped[str] = mapped_column(String, default="USD")
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    purchase_order_id: Mapped[str | None] = mapped_column(String, nullable=True)
    bank_account: Mapped[str | None] = mapped_column(String, nullable=True)  # masked
    routing_number: Mapped[str | None] = mapped_column(String, nullable=True)  # masked
    tax_id: Mapped[str | None] = mapped_column(String, nullable=True)  # masked
    source_document: Mapped[str | None] = mapped_column(String, nullable=True)
    raw_text: Mapped[str | None] = mapped_column(String, nullable=True)  # masked

    status: Mapped[str] = mapped_column(String, default="RECEIVED", index=True)
    risk_level: Mapped[str | None] = mapped_column(String, nullable=True)
    recommendation: Mapped[str | None] = mapped_column(String, nullable=True)
    recommendation_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    sensitive_data_detected: Mapped[bool] = mapped_column(Boolean, default=False)
    extraction: Mapped[list] = mapped_column(JSON, default=list)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class AgentDecisionRow(Base):
    __tablename__ = "agent_decisions"

    decision_id: Mapped[str] = mapped_column(String, primary_key=True)
    invoice_id: Mapped[str] = mapped_column(String, index=True)
    correlation_id: Mapped[str] = mapped_column(String)
    agent: Mapped[str] = mapped_column(String)
    decision: Mapped[str] = mapped_column(String)
    confidence: Mapped[float] = mapped_column(Float)
    risk_level: Mapped[str | None] = mapped_column(String, nullable=True)
    recommendation: Mapped[str | None] = mapped_column(String, nullable=True)
    reason_codes: Mapped[list] = mapped_column(JSON, default=list)
    evidence_ids: Mapped[list] = mapped_column(JSON, default=list)
    explanation: Mapped[dict] = mapped_column(JSON, default=dict)
    governance_result: Mapped[str | None] = mapped_column(String, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ToolCallRow(Base):
    __tablename__ = "tool_calls"

    tool_call_id: Mapped[str] = mapped_column(String, primary_key=True)
    invoice_id: Mapped[str] = mapped_column(String, index=True)
    correlation_id: Mapped[str] = mapped_column(String)
    agent: Mapped[str] = mapped_column(String)
    tool: Mapped[str] = mapped_column(String)
    purpose: Mapped[str] = mapped_column(String)
    parameters: Mapped[dict] = mapped_column(JSON, default=dict)
    is_write: Mapped[bool] = mapped_column(Boolean, default=False)
    authorization: Mapped[str] = mapped_column(String)
    denial_reason: Mapped[str | None] = mapped_column(String, nullable=True)
    result_summary: Mapped[str | None] = mapped_column(String, nullable=True)
    evidence_id: Mapped[str | None] = mapped_column(String, nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class AuditEventRow(Base):
    __tablename__ = "audit_events"
    __table_args__ = (UniqueConstraint("invoice_id", "sequence", name="uq_audit_invoice_sequence"),)

    event_id: Mapped[str] = mapped_column(String, primary_key=True)
    invoice_id: Mapped[str] = mapped_column(String, index=True)
    correlation_id: Mapped[str] = mapped_column(String)
    sequence: Mapped[int] = mapped_column(Integer)
    event_type: Mapped[str] = mapped_column(String)
    severity: Mapped[str] = mapped_column(String)
    actor: Mapped[str] = mapped_column(String)
    reason_codes: Mapped[list] = mapped_column(JSON, default=list)
    policy_result: Mapped[str | None] = mapped_column(String, nullable=True)
    input_summary: Mapped[str | None] = mapped_column(String, nullable=True)
    output_summary: Mapped[str | None] = mapped_column(String, nullable=True)
    evidence_refs: Mapped[list] = mapped_column(JSON, default=list)
    related_decision_id: Mapped[str | None] = mapped_column(String, nullable=True)
    related_tool_call_id: Mapped[str | None] = mapped_column(String, nullable=True)
    previous_event_hash: Mapped[str | None] = mapped_column(String, nullable=True)
    event_hash: Mapped[str] = mapped_column(String)
    out_of_order: Mapped[bool] = mapped_column(Boolean, default=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ApprovalRow(Base):
    __tablename__ = "approvals"

    approval_id: Mapped[str] = mapped_column(String, primary_key=True)
    invoice_id: Mapped[str] = mapped_column(String, index=True)
    correlation_id: Mapped[str] = mapped_column(String)
    requested_by: Mapped[str] = mapped_column(String)
    recommendation: Mapped[str] = mapped_column(String)
    recommendation_confidence: Mapped[float] = mapped_column(Float)
    risk_level: Mapped[str] = mapped_column(String)
    reason_codes: Mapped[list] = mapped_column(JSON, default=list)
    evidence_ids: Mapped[list] = mapped_column(JSON, default=list)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reviewer: Mapped[str | None] = mapped_column(String, nullable=True)
    human_decision: Mapped[str | None] = mapped_column(String, nullable=True)
    reviewer_note: Mapped[str | None] = mapped_column(String, nullable=True)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
