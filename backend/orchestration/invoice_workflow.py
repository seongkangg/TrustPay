"""Runs one stored invoice through the four agents and the governance decision.

    RECEIVED → EXTRACTED → VERIFYING → VERIFIED → RISK_REVIEW → (governance.finalize)
             → APPROVED → COMPLETED | PENDING_APPROVAL | BLOCKED | FAILED

Failure behaviour (spec §17): an agent that fails produces an `agent_failed` decision and
the workflow keeps going so the invoice still reaches a safe terminal state. If the
Intake agent fails there is nothing to verify, so the invoice is escalated to a human
and marked FAILED. Policy evaluation and the final decision are always made by the
governance engine, never skipped.
"""

from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.orm import Session

from backend.agents import ApprovalAgent, IntakeAgent, PolicyRiskAgent, VerificationAgent
from backend.database.tables import InvoiceRow
from backend.governance import GovernanceEngine, GovernanceOutcome
from backend.llm.granite_client import LLMClient
from backend.models import (
    AgentDecision,
    AgentName,
    EventType,
    InvoiceStatus,
    Recommendation,
    Severity,
    ToolCall,
)
from backend.orchestration.state_machine import transition
from backend.orchestration.workflow_context import WorkflowContext
from backend.utils.timestamps import now_utc

UPLOAD_FIELDS = (
    "vendor_invoice_number",
    "vendor_name",
    "vendor_id",
    "amount",
    "currency",
    "due_date",
    "purchase_order_id",
    "bank_account",
    "routing_number",
    "tax_id",
    "source_document",
    "raw_text",
)


@dataclass
class WorkflowResult:
    invoice: InvoiceRow
    decisions: list[AgentDecision]
    tool_calls: list[ToolCall]
    outcome: GovernanceOutcome
    approval_request: dict[str, Any] | None = None
    context: WorkflowContext = field(repr=False, default=None)


class InvoiceWorkflow:
    def __init__(self, session: Session, gov: GovernanceEngine, llm: LLMClient | None = None):
        self.session = session
        self.gov = gov
        self.llm = llm

    # ------------------------------------------------------------------

    def run(self, row: InvoiceRow) -> WorkflowResult:
        ctx = self._context_from_row(row)

        # Intake
        IntakeAgent(self.gov, self.llm).run(ctx)
        intake_failed = ctx.decisions[-1].decision == "agent_failed"
        self._set_status(
            row, InvoiceStatus.EXTRACTED if not intake_failed else InvoiceStatus.FAILED
        )
        row.extraction = [f.model_dump() for f in ctx.extraction]
        row.vendor_name = row.vendor_name or ctx.extracted.get("vendor_name")

        if not intake_failed:
            # Verification
            self._set_status(row, InvoiceStatus.VERIFYING)
            VerificationAgent(self.gov, self.llm).run(ctx)
            self._set_status(row, InvoiceStatus.VERIFIED)

            # Policy / risk
            self._set_status(row, InvoiceStatus.RISK_REVIEW)
            PolicyRiskAgent(self.gov, self.llm).run(ctx)
            ApprovalAgent(self.gov, self.llm).run(ctx)

        # Governance decides, no matter what the agents managed to do.
        policy = ctx.policy or self.gov.evaluate(
            ctx.to_policy_input(), invoice_id=ctx.invoice_id, correlation_id=ctx.correlation_id
        )
        # A failed or rejected agent decision never stands as an approve recommendation.
        recommendation = (
            Recommendation.ESCALATE
            if ctx.agent_failure
            else ctx.recommendation or Recommendation.ESCALATE
        )
        confidence = (
            ctx.recommendation_confidence if ctx.recommendation_confidence is not None else 0.0
        )
        outcome = self.gov.finalize(
            invoice_id=ctx.invoice_id,
            correlation_id=ctx.correlation_id,
            amount=ctx.amount or 0.0,
            currency=ctx.currency,
            policy=policy,
            recommendation=recommendation,
            confidence=confidence,
            evidence_ids=list(ctx.evidence_ids),
        )

        row.risk_level = policy.risk_level.value
        row.recommendation = recommendation.value
        row.recommendation_confidence = confidence
        if not intake_failed:
            self._set_status(row, outcome.status)
            if outcome.status == InvoiceStatus.APPROVED and outcome.payment:
                self._set_status(row, InvoiceStatus.COMPLETED)
        # intake_failed: stays FAILED, with an approval request open for a human to look at.

        self.gov.record(
            actor=AgentName.SYSTEM,
            invoice_id=ctx.invoice_id,
            correlation_id=ctx.correlation_id,
            event_type=EventType.AUDIT_RECORD_CREATED,
            severity=self._severity_for(row.status),
            output_summary=f"workflow finished: status={row.status} risk={row.risk_level} recommendation={row.recommendation}",
            evidence_refs=list(ctx.evidence_ids),
        )
        self.session.commit()

        return WorkflowResult(
            invoice=row,
            decisions=list(ctx.decisions),
            tool_calls=self.gov.interceptor.calls_for(ctx.invoice_id),
            outcome=outcome,
            approval_request=outcome.approval_request,
            context=ctx,
        )

    # ------------------------------------------------------------------

    def _context_from_row(self, row: InvoiceRow) -> WorkflowContext:
        upload = {name: getattr(row, name) for name in UPLOAD_FIELDS}
        if upload.get("due_date") is not None:
            upload["due_date"] = upload["due_date"].isoformat()
        ctx = WorkflowContext(
            invoice_id=row.invoice_id, correlation_id=row.correlation_id, upload=upload
        )
        ctx.sensitive_detected = bool(row.sensitive_data_detected)
        for ev in self.gov.audit.list_for_invoice(row.invoice_id):
            if ev.event_type == EventType.SENSITIVE_DATA_MASKED:
                ctx.scan_evidence_id = next(
                    (r for r in ev.evidence_refs if r.startswith("SCAN-")), None
                )
                ctx.add_evidence(ctx.scan_evidence_id)
        return ctx

    def _set_status(self, row: InvoiceRow, target: InvoiceStatus) -> None:
        row.status = transition(InvoiceStatus(row.status), target).value
        row.updated_at = now_utc()
        self.session.commit()

    @staticmethod
    def _severity_for(status: str) -> Severity:
        return {
            InvoiceStatus.COMPLETED.value: Severity.LOW,
            InvoiceStatus.PENDING_APPROVAL.value: Severity.MEDIUM,
        }.get(status, Severity.HIGH)
