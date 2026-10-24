"""Reliability (spec §17/§18): the system reaches a safe terminal state when things break.

Covered elsewhere: malformed model output at intake and approval (test_intake_agent,
test_approval_agents), vendor service down (test_workflow), duplicate and out-of-order
audit events (test_audit_trail), missing vendor record (test_verification_agent).
"""

import pytest

from backend.governance import GovernanceEngine
from backend.mock_systems.approval_limit_service import ApprovalLimitService
from backend.mock_systems.payment_service import PaymentService
from backend.mock_systems.purchase_order_service import PurchaseOrderService
from backend.models import HumanDecisionInput, InvoiceUpload, ReasonCode
from backend.models import InvoiceStatus as S
from backend.services.approval_service import ApprovalService
from backend.services.errors import UpstreamUnavailableError
from backend.services.invoice_service import InvoiceService


class HangingLLM:
    """Simulates a model call that times out."""

    mode = "hanging"

    def complete(self, prompt: str) -> str:
        raise TimeoutError("model did not respond within the deadline")


class CrashingLLM:
    """Raises something unexpected — not an LLMError — from inside a model call."""

    mode = "crashing"

    def complete(self, prompt: str) -> str:
        raise RuntimeError("provider exploded")


def events(gov, invoice_id):
    return [e.event_type.value for e in gov.audit.list_for_invoice(invoice_id)]


def process(session, ref, fixture, *, llm=None, **engine_kwargs):
    gov = GovernanceEngine(session, ref, **engine_kwargs)
    svc = InvoiceService(session, gov, llm=llm)
    svc.create(InvoiceUpload(**fixture["upload"]))
    return gov, svc, svc.process("INV-1001")


# --- agent timeout -----------------------------------------------------------


def test_model_timeout_ends_in_failed_and_escalated(session, ref, fixture_by_id):
    gov, _, result = process(session, ref, fixture_by_id("INV-1001"), llm=HangingLLM())
    assert result.invoice.status == S.FAILED.value
    assert result.approval_request is not None
    assert ReasonCode.AGENT_FAILURE in result.outcome.reason_codes
    assert gov.payments.get_payment("INV-1001") is None
    assert "agent_failed" in events(gov, "INV-1001")
    assert gov.audit.get_trail("INV-1001").chain_valid


def test_unexpected_model_exception_is_contained(session, ref, fixture_by_id):
    gov, _, result = process(session, ref, fixture_by_id("INV-1001"), llm=CrashingLLM())
    assert result.invoice.status == S.FAILED.value
    assert gov.audit.get_trail("INV-1001").chain_valid


# --- enterprise systems down ----------------------------------------------------


def test_purchase_order_service_down_escalates_not_fails(session, ref, fixture_by_id):
    gov, _, result = process(
        session,
        ref,
        fixture_by_id("INV-1001"),
        po_service=PurchaseOrderService(ref, available=False),
    )
    assert result.invoice.status == S.PENDING_APPROVAL.value
    assert ReasonCode.MOCK_SYSTEM_UNAVAILABLE in result.outcome.reason_codes
    assert gov.payments.get_payment("INV-1001") is None


def test_approval_limit_service_down_escalates(session, ref, fixture_by_id):
    gov, _, result = process(
        session,
        ref,
        fixture_by_id("INV-1001"),
        limit_service=ApprovalLimitService(ref, available=False),
    )
    assert result.invoice.status == S.PENDING_APPROVAL.value
    assert ReasonCode.MOCK_SYSTEM_UNAVAILABLE in result.outcome.reason_codes


def test_payment_service_down_on_low_risk_holds_for_human(session, ref, fixture_by_id):
    gov, _, result = process(
        session, ref, fixture_by_id("INV-1001"), payment_service=PaymentService(available=False)
    )
    assert result.invoice.status == S.PENDING_APPROVAL.value
    assert result.outcome.reason_codes == [ReasonCode.MOCK_SYSTEM_UNAVAILABLE]
    assert result.approval_request is not None
    seq = events(gov, "INV-1001")
    assert "payment_authorized" not in seq and "payment_blocked" in seq


def test_payment_service_down_during_human_approval_is_retryable(session, ref, fixture_by_id):
    payments = PaymentService(available=False)
    gov = GovernanceEngine(session, ref, payment_service=payments)
    invoices = InvoiceService(session, gov)
    approvals = ApprovalService(session, gov, invoices)
    invoices.create(InvoiceUpload(**fixture_by_id("INV-1002")["upload"]))
    invoices.process("INV-1001")

    with pytest.raises(UpstreamUnavailableError):
        approvals.approve("INV-1001", HumanDecisionInput(reviewer="fin@example.com"))
    assert invoices.get("INV-1001").status == S.PENDING_APPROVAL
    assert "human_decision_recorded" not in events(gov, "INV-1001")  # nothing half-recorded

    payments._available = True  # service recovers
    invoice, approval = approvals.approve(
        "INV-1001", HumanDecisionInput(reviewer="fin@example.com")
    )
    assert invoice.status == S.COMPLETED and approval["human_decision"] == "approved"


# --- every failure path keeps the audit chain intact ----------------------------


@pytest.mark.parametrize("llm", [HangingLLM(), CrashingLLM(), None])
def test_chain_valid_under_every_failure(session, ref, fixture_by_id, llm):
    gov, _, _ = process(
        session,
        ref,
        fixture_by_id("INV-1003"),
        llm=llm,
        po_service=PurchaseOrderService(ref, available=False),
    )
    trail = gov.audit.get_trail("INV-1001")
    assert trail.chain_valid and trail.events[-1].event_type.value == "audit_record_created"
