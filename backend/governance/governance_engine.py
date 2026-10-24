"""Facade over the governance layer. Everything the orchestrator and agents need:

    ingest()          mask sensitive data on upload, emit evidence + event
    call_tool()       governed tool access (allowlist → execute → log)
    accept_decision() validate + persist an AgentDecision, set governance_result
    evaluate()        run the policy matrix, emit risk_assigned
    finalize()        pay (governance only, low risk) or block + request human approval
    record_human_decision() / execute_human_payment()  used by the approval service

No LLM calls happen anywhere in this package.
"""

from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.database.seed_data import ReferenceData, get_reference_data
from backend.database.tables import AgentDecisionRow, ApprovalRow
from backend.governance.decision_validator import ValidationResult, validate_decision
from backend.governance.policy_engine import PolicyEngine, PolicyInput, PolicyResult
from backend.governance.sensitive_data_scanner import ScanResult, SensitiveDataScanner
from backend.governance.tool_call_interceptor import ToolCallInterceptor, ToolCallOutcome
from backend.mock_systems.approval_limit_service import ApprovalLimitService
from backend.mock_systems.payment_service import PaymentService
from backend.mock_systems.purchase_order_service import PurchaseOrderService
from backend.mock_systems.vendor_service import VendorService
from backend.models import (
    AgentDecision,
    AgentName,
    Authorization,
    EventType,
    Explanation,
    HumanDecision,
    InvoiceStatus,
    ReasonCode,
    Recommendation,
    RiskLevel,
    Severity,
    ToolCallRequest,
    ToolName,
)
from backend.services.audit_service import AuditService
from backend.utils.timestamps import now_utc

_SEVERITY = {
    RiskLevel.LOW: Severity.LOW,
    RiskLevel.MEDIUM: Severity.MEDIUM,
    RiskLevel.HIGH: Severity.HIGH,
}


@dataclass
class GovernanceOutcome:
    status: InvoiceStatus
    authorization: Authorization
    reason_codes: list[ReasonCode]
    approval_request: dict[str, Any] | None = None
    payment: dict[str, Any] | None = None


class GovernanceEngine:
    def __init__(
        self,
        session: Session,
        ref: ReferenceData | None = None,
        *,
        vendor_service: VendorService | None = None,
        po_service: PurchaseOrderService | None = None,
        limit_service: ApprovalLimitService | None = None,
        payment_service: PaymentService | None = None,
    ):
        self.session = session
        self.ref = ref or get_reference_data()
        self.audit = AuditService(session)
        self.scanner = SensitiveDataScanner(self.audit)
        self.policy = PolicyEngine(self.ref.thresholds, self.ref.approval_limits)

        vendors = vendor_service or VendorService(self.ref)
        pos = po_service or PurchaseOrderService(self.ref)
        limits = limit_service or ApprovalLimitService(self.ref)
        self.payments = payment_service or PaymentService()

        self.interceptor = ToolCallInterceptor(
            session,
            self.audit,
            {
                ToolName.VENDOR_LOOKUP: lambda p: vendors.get_vendor(p["vendor_id"]),
                ToolName.PO_LOOKUP: lambda p: pos.get_purchase_order(p["purchase_order_id"]),
                ToolName.APPROVAL_LIMIT_LOOKUP: lambda p: limits.get_limit(p["agent_id"]),
                ToolName.RISK_RULES: lambda p: self.policy.describe_rules(),
                ToolName.PAYMENT_AUTHORIZE: lambda p: self.payments.authorize(
                    p["invoice_id"], p["amount"], p["currency"], p["actor"]
                ),
                ToolName.APPROVAL_REQUEST_CREATE: self._create_approval_request,
                # DOCUMENT_PARSER is registered by the intake agent (Sprint 3).
            },
        )

    # ------------------------------------------------------------------ ingest

    def ingest(self, upload: dict, *, invoice_id: str, correlation_id: str) -> ScanResult:
        return self.scanner.scan_upload(
            upload, invoice_id=invoice_id, correlation_id=correlation_id
        )

    # --------------------------------------------------------------- tool calls

    def call_tool(
        self,
        request: ToolCallRequest,
        *,
        payment_permitted: bool = False,
        risk_level: RiskLevel | None = None,
    ) -> ToolCallOutcome:
        return self.interceptor.execute(
            request, payment_permitted=payment_permitted, risk_level=risk_level
        )

    def record(self, *, actor: AgentName, **kw):
        """Agents report workflow progress (vendor_verified, purchase_order_checked, …) through
        here rather than touching the audit store directly."""
        return self.audit.append(actor=actor, **kw)

    def known_evidence(self, invoice_id: str) -> set[str]:
        refs = self.interceptor.evidence_ids_for(invoice_id)
        for ev in self.audit.list_for_invoice(invoice_id):
            refs.update(ev.evidence_refs)
        return refs

    # ---------------------------------------------------------------- decisions

    def accept_decision(self, decision: AgentDecision) -> tuple[AgentDecision, ValidationResult]:
        result = validate_decision(
            decision, self.known_evidence(decision.invoice_id), self.policy.confidence_threshold
        )
        if not result.valid:
            governance_result = Authorization.BLOCKED
        elif result.low_confidence:
            governance_result = Authorization.ESCALATED
        else:
            governance_result = Authorization.ALLOWED

        accepted = decision.model_copy(update={"governance_result": governance_result})
        row = AgentDecisionRow(**accepted.model_dump(mode="json"))
        row.timestamp = accepted.timestamp
        self.session.add(row)
        self.session.commit()

        if not result.valid:
            self.audit.append(
                invoice_id=decision.invoice_id,
                correlation_id=decision.correlation_id,
                event_type=EventType.AGENT_FAILED,
                severity=Severity.MEDIUM,
                actor=AgentName.GOVERNANCE,
                reason_codes=result.reason_codes,
                policy_result=Authorization.BLOCKED,
                input_summary=f"{decision.agent.value} decision {decision.decision_id} rejected",
                output_summary="; ".join(result.problems),
                related_decision_id=decision.decision_id,
            )
        return accepted, result

    # ------------------------------------------------------------------- policy

    def evaluate(self, inp: PolicyInput, *, invoice_id: str, correlation_id: str) -> PolicyResult:
        result = self.policy.evaluate(inp)
        if result.risk_level == RiskLevel.LOW:
            policy_result = Authorization.ALLOWED
        elif result.risk_level == RiskLevel.MEDIUM:
            policy_result = Authorization.ESCALATED
        else:
            policy_result = Authorization.BLOCKED
        self.audit.append(
            invoice_id=invoice_id,
            correlation_id=correlation_id,
            event_type=EventType.RISK_ASSIGNED,
            severity=_SEVERITY[result.risk_level],
            actor=AgentName.GOVERNANCE,
            reason_codes=result.reason_codes,
            policy_result=policy_result,
            output_summary=f"risk={result.risk_level.value}; action={result.action}",
            evidence_refs=result.rules_triggered,
        )
        return result

    # ----------------------------------------------------------------- finalize

    def finalize(
        self,
        *,
        invoice_id: str,
        correlation_id: str,
        amount: float,
        currency: str,
        policy: PolicyResult,
        recommendation: Recommendation,
        confidence: float,
        evidence_ids: list[str],
    ) -> GovernanceOutcome:
        """Deterministic outcome. AI recommended; this decides."""
        if policy.auto_payment_allowed and recommendation == Recommendation.APPROVE:
            outcome = self.call_tool(
                ToolCallRequest(
                    agent=AgentName.GOVERNANCE,
                    tool=ToolName.PAYMENT_AUTHORIZE,
                    purpose="low-risk invoice passed all policy checks",
                    parameters={
                        "invoice_id": invoice_id,
                        "amount": amount,
                        "currency": currency,
                        "actor": AgentName.GOVERNANCE.value,
                    },
                    invoice_id=invoice_id,
                    correlation_id=correlation_id,
                ),
                payment_permitted=True,
            )
            if outcome.ok:
                self.audit.append(
                    invoice_id=invoice_id,
                    correlation_id=correlation_id,
                    event_type=EventType.PAYMENT_AUTHORIZED,
                    severity=Severity.LOW,
                    actor=AgentName.GOVERNANCE,
                    reason_codes=policy.reason_codes,
                    policy_result=Authorization.ALLOWED,
                    output_summary=f"simulated payment {outcome.result['payment_id']} authorized",
                    evidence_refs=[*policy.rules_triggered, outcome.call.evidence_id or ""],
                    related_tool_call_id=outcome.call.tool_call_id,
                )
                return GovernanceOutcome(
                    InvoiceStatus.APPROVED,
                    Authorization.ALLOWED,
                    policy.reason_codes,
                    payment=outcome.result,
                )
            reason_codes = [ReasonCode.MOCK_SYSTEM_UNAVAILABLE]
            target, risk = InvoiceStatus.PENDING_APPROVAL, RiskLevel.MEDIUM
        elif policy.auto_payment_allowed:
            # Policy would permit, but the agent itself asked for review → honour the caution.
            reason_codes = policy.reason_codes
            target, risk = InvoiceStatus.PENDING_APPROVAL, RiskLevel.MEDIUM
        else:
            reason_codes = policy.reason_codes
            target, risk = policy.target_status, policy.risk_level

        self.audit.append(
            invoice_id=invoice_id,
            correlation_id=correlation_id,
            event_type=EventType.PAYMENT_BLOCKED,
            severity=_SEVERITY[risk],
            actor=AgentName.GOVERNANCE,
            reason_codes=reason_codes,
            policy_result=Authorization.BLOCKED,
            output_summary=f"payment withheld pending human review; recommendation={recommendation.value}",
            evidence_refs=[*policy.rules_triggered, *evidence_ids],
        )
        req = self.call_tool(
            ToolCallRequest(
                agent=AgentName.GOVERNANCE,
                tool=ToolName.APPROVAL_REQUEST_CREATE,
                purpose="human approval required by policy",
                parameters={
                    "invoice_id": invoice_id,
                    "correlation_id": correlation_id,
                    "requested_by": AgentName.GOVERNANCE.value,
                    "recommendation": recommendation.value,
                    "recommendation_confidence": confidence,
                    "risk_level": risk.value,
                    "reason_codes": [c.value for c in reason_codes],
                    "evidence_ids": evidence_ids,
                },
                invoice_id=invoice_id,
                correlation_id=correlation_id,
            ),
            risk_level=risk,
        )
        self.audit.append(
            invoice_id=invoice_id,
            correlation_id=correlation_id,
            event_type=EventType.APPROVAL_REQUESTED,
            severity=_SEVERITY[risk],
            actor=AgentName.GOVERNANCE,
            reason_codes=reason_codes,
            policy_result=Authorization.ESCALATED,
            output_summary=f"approval request {req.result['approval_id']} created",
            evidence_refs=[req.call.evidence_id or ""],
            related_tool_call_id=req.call.tool_call_id,
        )
        return GovernanceOutcome(
            target, Authorization.BLOCKED, reason_codes, approval_request=req.result
        )

    # ------------------------------------------------------------ human review

    def record_human_decision(
        self,
        *,
        invoice_id: str,
        correlation_id: str,
        reviewer: str,
        decision: HumanDecision,
        note: str | None = None,
    ) -> dict[str, Any]:
        row = self._open_approval(invoice_id)
        if row is None:
            raise LookupError(f"no open approval request for {invoice_id}")
        row.reviewer = reviewer
        row.human_decision = decision.value
        row.reviewer_note = note
        row.decided_at = now_utc()
        self.session.commit()
        self.audit.append(
            invoice_id=invoice_id,
            correlation_id=correlation_id,
            event_type=EventType.HUMAN_DECISION_RECORDED,
            severity=Severity.MEDIUM,
            actor=AgentName.HUMAN_REVIEWER,
            policy_result=Authorization.ALLOWED
            if decision == HumanDecision.APPROVED
            else Authorization.BLOCKED,
            input_summary=f"reviewer {reviewer} on {row.approval_id}",
            output_summary=f"human decision: {decision.value}" + (f" — {note}" if note else ""),
            evidence_refs=[row.approval_id],
        )
        return self._approval_dict(row)

    def execute_human_payment(
        self, *, invoice_id: str, correlation_id: str, amount: float, currency: str, reviewer: str
    ) -> ToolCallOutcome:
        outcome = self.call_tool(
            ToolCallRequest(
                agent=AgentName.HUMAN_REVIEWER,
                tool=ToolName.PAYMENT_AUTHORIZE,
                purpose=f"human approval recorded by {reviewer}",
                parameters={
                    "invoice_id": invoice_id,
                    "amount": amount,
                    "currency": currency,
                    "actor": AgentName.HUMAN_REVIEWER.value,
                },
                invoice_id=invoice_id,
                correlation_id=correlation_id,
            ),
            payment_permitted=True,
        )
        if outcome.ok:
            self.audit.append(
                invoice_id=invoice_id,
                correlation_id=correlation_id,
                event_type=EventType.PAYMENT_AUTHORIZED,
                severity=Severity.MEDIUM,
                actor=AgentName.HUMAN_REVIEWER,
                policy_result=Authorization.ALLOWED,
                output_summary=f"simulated payment {outcome.result['payment_id']} authorized by {reviewer}",
                evidence_refs=[outcome.call.evidence_id or ""],
                related_tool_call_id=outcome.call.tool_call_id,
            )
        return outcome

    # -------------------------------------------------------------- explanation

    @staticmethod
    def build_explanation(
        decision: str,
        policy: PolicyResult,
        evidence_ids: list[str],
        *,
        missing: list[str] | None = None,
        next_step: str | None = None,
    ) -> Explanation:
        return Explanation(
            decision=decision,
            reasons=[h.detail for h in policy.hits],
            evidence=list(evidence_ids),
            policy_rules_triggered=list(policy.rules_triggered),
            missing_information=list(missing or []),
            recommended_next_step=next_step,
        )

    # ---------------------------------------------------------------- internals

    def _create_approval_request(self, p: dict[str, Any]) -> dict[str, Any]:
        timeout_h = int(self.ref.thresholds.get("approval_timeout_hours", 48))
        count = self.session.scalar(select(func.count()).select_from(ApprovalRow)) or 0
        row = ApprovalRow(
            approval_id=f"APR-{count + 1:03d}",
            invoice_id=p["invoice_id"],
            correlation_id=p["correlation_id"],
            requested_by=p["requested_by"],
            recommendation=p["recommendation"],
            recommendation_confidence=float(p["recommendation_confidence"]),
            risk_level=p["risk_level"],
            reason_codes=list(p.get("reason_codes", [])),
            evidence_ids=list(p.get("evidence_ids", [])),
            requested_at=now_utc(),
            expires_at=now_utc() + timedelta(hours=timeout_h),
        )
        self.session.add(row)
        self.session.commit()
        return self._approval_dict(row)

    def _open_approval(self, invoice_id: str) -> ApprovalRow | None:
        stmt = (
            select(ApprovalRow)
            .where(ApprovalRow.invoice_id == invoice_id, ApprovalRow.human_decision.is_(None))
            .order_by(ApprovalRow.requested_at.desc())
        )
        return self.session.scalars(stmt).first()

    @staticmethod
    def _approval_dict(row: ApprovalRow) -> dict[str, Any]:
        return {
            "approval_id": row.approval_id,
            "invoice_id": row.invoice_id,
            "correlation_id": row.correlation_id,
            "requested_by": row.requested_by,
            "recommendation": row.recommendation,
            "recommendation_confidence": row.recommendation_confidence,
            "risk_level": row.risk_level,
            "reason_codes": row.reason_codes,
            "evidence_ids": row.evidence_ids,
            "requested_at": row.requested_at,
            "expires_at": row.expires_at,
            "reviewer": row.reviewer,
            "human_decision": row.human_decision,
            "reviewer_note": row.reviewer_note,
            "decided_at": row.decided_at,
        }
