"""Invoice lifecycle: create (ingest + mask), process (run the workflow), read views.

Every response model built here is already masked: `Invoice` refuses raw identifiers,
and the stored row never held them in the first place.
"""

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.database.tables import AgentDecisionRow, ApprovalRow, AuditEventRow, InvoiceRow
from backend.governance import GovernanceEngine
from backend.llm.granite_client import LLMClient
from backend.models import (
    AgentDecision,
    AgentName,
    EventType,
    Invoice,
    InvoiceStatus,
    InvoiceSummary,
    InvoiceUpload,
    Severity,
)
from backend.orchestration.invoice_workflow import InvoiceWorkflow, WorkflowResult
from backend.services.errors import InvalidStateError, NotFoundError
from backend.utils.timestamps import now_utc

FIRST_INVOICE_NUMBER = 1001


def _utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


def row_to_invoice(row: InvoiceRow) -> Invoice:
    return Invoice(
        invoice_id=row.invoice_id,
        vendor_invoice_number=row.vendor_invoice_number,
        vendor_id=row.vendor_id,
        vendor_name=row.vendor_name,
        amount=row.amount,
        currency=row.currency,
        due_date=row.due_date,
        purchase_order_id=row.purchase_order_id,
        bank_account=row.bank_account,
        routing_number=row.routing_number,
        tax_id=row.tax_id,
        source_document=row.source_document,
        status=row.status,
        risk_level=row.risk_level,
        recommendation=row.recommendation,
        recommendation_confidence=row.recommendation_confidence,
        sensitive_data_detected=row.sensitive_data_detected,
        correlation_id=row.correlation_id,
        extraction=row.extraction or [],
        created_at=_utc(row.created_at),
        updated_at=_utc(row.updated_at),
    )


def row_to_summary(row: InvoiceRow) -> InvoiceSummary:
    return InvoiceSummary(
        invoice_id=row.invoice_id,
        vendor_name=row.vendor_name,
        amount=row.amount,
        currency=row.currency,
        status=row.status,
        risk_level=row.risk_level,
        recommendation=row.recommendation,
        sensitive_data_detected=row.sensitive_data_detected,
        updated_at=_utc(row.updated_at),
    )


class InvoiceService:
    def __init__(self, session: Session, gov: GovernanceEngine, llm: LLMClient | None = None):
        self.session = session
        self.gov = gov
        self.llm = llm

    # ---------------------------------------------------------------- create

    def create(self, upload: InvoiceUpload) -> Invoice:
        invoice_id = self._next_invoice_id()
        correlation_id = str(uuid.uuid4())
        self.gov.record(
            actor=AgentName.SYSTEM,
            invoice_id=invoice_id,
            correlation_id=correlation_id,
            event_type=EventType.INVOICE_RECEIVED,
            severity=Severity.LOW,
            input_summary=f"upload {upload.source_document or '(structured)'} for {upload.vendor_name or upload.vendor_id}",
        )
        scan = self.gov.ingest(
            upload.model_dump(), invoice_id=invoice_id, correlation_id=correlation_id
        )
        masked = scan.masked
        now = now_utc()
        row = InvoiceRow(
            invoice_id=invoice_id,
            correlation_id=correlation_id,
            vendor_invoice_number=masked["vendor_invoice_number"],
            vendor_id=masked.get("vendor_id"),
            vendor_name=masked.get("vendor_name"),
            amount=masked.get("amount"),
            currency=(masked.get("currency") or "USD"),
            due_date=masked.get("due_date"),
            purchase_order_id=masked.get("purchase_order_id"),
            bank_account=masked.get("bank_account"),
            routing_number=masked.get("routing_number"),
            tax_id=masked.get("tax_id"),
            source_document=masked.get("source_document"),
            raw_text=masked.get("raw_text"),
            status=InvoiceStatus.RECEIVED.value,
            sensitive_data_detected=scan.found,
            created_at=now,
            updated_at=now,
        )
        if hasattr(row.currency, "value"):
            row.currency = row.currency.value
        self.session.add(row)
        self.session.commit()
        return row_to_invoice(row)

    # ----------------------------------------------------------------- read

    def get_row(self, invoice_id: str) -> InvoiceRow:
        row = self.session.get(InvoiceRow, invoice_id)
        if row is None:
            raise NotFoundError(f"invoice {invoice_id} not found", invoice_id=invoice_id)
        return row

    def get(self, invoice_id: str) -> Invoice:
        return row_to_invoice(self.get_row(invoice_id))

    def list_invoices(
        self,
        *,
        status: InvoiceStatus | None = None,
        risk_level: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[InvoiceSummary], int]:
        stmt = select(InvoiceRow)
        if status:
            stmt = stmt.where(InvoiceRow.status == InvoiceStatus(status).value)
        if risk_level:
            stmt = stmt.where(InvoiceRow.risk_level == risk_level)
        total = self.session.scalar(select(func.count()).select_from(stmt.subquery())) or 0
        rows = self.session.scalars(
            stmt.order_by(InvoiceRow.created_at.desc()).offset(offset).limit(limit)
        )
        return [row_to_summary(r) for r in rows], total

    # -------------------------------------------------------------- process

    def process(self, invoice_id: str) -> WorkflowResult:
        row = self.get_row(invoice_id)
        if row.status != InvoiceStatus.RECEIVED.value:
            raise InvalidStateError(
                f"invoice {invoice_id} is {row.status}; only RECEIVED invoices can be processed",
                invoice_id=invoice_id,
                correlation_id=row.correlation_id,
            )
        return InvoiceWorkflow(self.session, self.gov, self.llm).run(row)

    # ---------------------------------------------------------------- views

    def decisions(self, invoice_id: str) -> list[AgentDecision]:
        stmt = (
            select(AgentDecisionRow)
            .where(AgentDecisionRow.invoice_id == invoice_id)
            .order_by(AgentDecisionRow.timestamp, AgentDecisionRow.decision_id)
        )
        return [
            AgentDecision.model_validate(r, from_attributes=True)
            for r in self.session.scalars(stmt)
        ]

    def open_approval(self, invoice_id: str) -> dict[str, Any] | None:
        stmt = (
            select(ApprovalRow)
            .where(ApprovalRow.invoice_id == invoice_id)
            .order_by(ApprovalRow.requested_at.desc())
            .limit(1)
        )
        row = self.session.scalars(stmt).first()
        return GovernanceEngine._approval_dict(row) if row else None

    def timeline(self, invoice_id: str) -> dict[str, Any]:
        self.get_row(invoice_id)
        entries: list[dict[str, Any]] = []
        for d in self.decisions(invoice_id):
            entries.append({"kind": "decision", "timestamp": _utc(d.timestamp), "data": d})
        for c in self.gov.interceptor.calls_for(invoice_id):
            entries.append({"kind": "tool_call", "timestamp": _utc(c.timestamp), "data": c})
        for e in self.gov.audit.list_for_invoice(invoice_id):
            entries.append(
                {"kind": "event", "timestamp": _utc(e.timestamp), "data": e, "sequence": e.sequence}
            )
        order = {"event": 0, "tool_call": 1, "decision": 2}
        entries.sort(key=lambda x: (x["timestamp"], x.get("sequence", 0), order[x["kind"]]))
        for x in entries:
            x.pop("sequence", None)
        return {"invoice_id": invoice_id, "entries": entries}

    def dashboard_summary(self, recent: int = 5) -> dict[str, Any]:
        rows = list(self.session.scalars(select(InvoiceRow)))
        by_risk = {"low": 0, "medium": 0, "high": 0}
        by_status: dict[str, int] = {}
        for r in rows:
            if r.risk_level in by_risk:
                by_risk[r.risk_level] += 1
            by_status[r.status] = by_status.get(r.status, 0) + 1

        blocked_types = (EventType.PAYMENT_BLOCKED.value, EventType.TOOL_CALL_DENIED.value)
        blocked_actions = (
            self.session.scalar(
                select(func.count())
                .select_from(AuditEventRow)
                .where(AuditEventRow.event_type.in_(blocked_types))
            )
            or 0
        )
        pending_approvals = (
            self.session.scalar(
                select(func.count())
                .select_from(ApprovalRow)
                .where(ApprovalRow.human_decision.is_(None))
            )
            or 0
        )
        violations_stmt = (
            select(AuditEventRow)
            .where(AuditEventRow.event_type == EventType.PAYMENT_BLOCKED.value)
            .order_by(AuditEventRow.timestamp.desc())
            .limit(recent)
        )
        recent_violations = [
            {
                "invoice_id": e.invoice_id,
                "reason_codes": e.reason_codes,
                "timestamp": _utc(e.timestamp),
            }
            for e in self.session.scalars(violations_stmt)
        ]
        return {
            "total_invoices": len(rows),
            "by_risk": by_risk,
            "by_status": by_status,
            "blocked_actions": blocked_actions,
            "pending_approvals": pending_approvals,
            "sensitive_data_detections": sum(1 for r in rows if r.sensitive_data_detected),
            "recent_violations": recent_violations,
        }

    # ------------------------------------------------------------ internals

    def _next_invoice_id(self) -> str:
        count = self.session.scalar(select(func.count()).select_from(InvoiceRow)) or 0
        return f"INV-{FIRST_INVOICE_NUMBER + count}"
