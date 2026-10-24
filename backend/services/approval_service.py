"""Human approve / reject on escalated invoices.

Rules (acceptance B5):
- only PENDING_APPROVAL or BLOCKED invoices can be decided
- the reviewer may approve up to the human_reviewer limit; above that the invoice stays put
- the AI recommendation and the human decision are stored separately
- a recorded approval triggers the (simulated) payment as the human reviewer, then COMPLETED
- a timeout never auto-approves: an expired request simply stays open and unpaid
"""

from typing import Any

from sqlalchemy.orm import Session

from backend.governance import GovernanceEngine
from backend.models import (
    AgentName,
    EventType,
    HumanDecision,
    HumanDecisionInput,
    Invoice,
    InvoiceStatus,
    Severity,
)
from backend.orchestration.state_machine import AWAITING_HUMAN, transition
from backend.services.errors import ForbiddenError, InvalidStateError, UpstreamUnavailableError
from backend.services.invoice_service import InvoiceService, row_to_invoice
from backend.utils.timestamps import now_utc


class ApprovalService:
    def __init__(self, session: Session, gov: GovernanceEngine, invoices: InvoiceService):
        self.session = session
        self.gov = gov
        self.invoices = invoices

    def approve(self, invoice_id: str, body: HumanDecisionInput) -> tuple[Invoice, dict[str, Any]]:
        row = self._awaiting(invoice_id)
        limit = float(self.gov.ref.approval_limits[AgentName.HUMAN_REVIEWER.value]["max_amount"])
        if (row.amount or 0.0) > limit:
            raise ForbiddenError(
                f"amount {row.amount} exceeds the human reviewer limit {limit}; invoice stays {row.status}",
                invoice_id=invoice_id,
                correlation_id=row.correlation_id,
            )
        approval = self.gov.record_human_decision(
            invoice_id=invoice_id,
            correlation_id=row.correlation_id,
            reviewer=body.reviewer,
            decision=HumanDecision.APPROVED,
            note=body.note,
        )
        payment = self.gov.execute_human_payment(
            invoice_id=invoice_id,
            correlation_id=row.correlation_id,
            amount=float(row.amount or 0.0),
            currency=row.currency,
            reviewer=body.reviewer,
        )
        if not payment.ok:
            raise UpstreamUnavailableError(
                "payment service unavailable; approval recorded, invoice remains unpaid",
                invoice_id=invoice_id,
                correlation_id=row.correlation_id,
            )
        self._set_status(row, InvoiceStatus.APPROVED)
        self._set_status(row, InvoiceStatus.COMPLETED)
        self._close(row, "approved")
        return row_to_invoice(row), approval

    def reject(self, invoice_id: str, body: HumanDecisionInput) -> tuple[Invoice, dict[str, Any]]:
        row = self._awaiting(invoice_id)
        approval = self.gov.record_human_decision(
            invoice_id=invoice_id,
            correlation_id=row.correlation_id,
            reviewer=body.reviewer,
            decision=HumanDecision.REJECTED,
            note=body.note,
        )
        self._set_status(row, InvoiceStatus.REJECTED)
        self._close(row, "rejected")
        return row_to_invoice(row), approval

    # ------------------------------------------------------------------

    def _awaiting(self, invoice_id: str):
        row = self.invoices.get_row(invoice_id)
        if InvoiceStatus(row.status) not in AWAITING_HUMAN:
            raise InvalidStateError(
                f"invoice {invoice_id} is {row.status}; only PENDING_APPROVAL or BLOCKED invoices can be decided",
                invoice_id=invoice_id,
                correlation_id=row.correlation_id,
            )
        return row

    def _set_status(self, row, target: InvoiceStatus) -> None:
        row.status = transition(InvoiceStatus(row.status), target).value
        row.updated_at = now_utc()
        self.session.commit()

    def _close(self, row, verb: str) -> None:
        self.gov.record(
            actor=AgentName.SYSTEM,
            invoice_id=row.invoice_id,
            correlation_id=row.correlation_id,
            event_type=EventType.AUDIT_RECORD_CREATED,
            severity=Severity.LOW,
            output_summary=f"human review {verb}; status={row.status}",
        )
