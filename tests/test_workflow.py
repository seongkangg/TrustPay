"""State machine, workflow runner, and human-approval service (acceptance A16, B5, B9)."""

import pytest

from backend.governance import GovernanceEngine
from backend.mock_systems.vendor_service import VendorService
from backend.models import EventType, HumanDecisionInput, InvoiceUpload, ReasonCode, Recommendation
from backend.models import InvoiceStatus as S
from backend.orchestration.state_machine import (
    InvalidTransition,
    can_transition,
    is_terminal,
    transition,
)
from backend.services.approval_service import ApprovalService
from backend.services.errors import ForbiddenError, InvalidStateError
from backend.services.invoice_service import InvoiceService


class BrokenLLM:
    mode = "broken"

    def complete(self, prompt: str) -> str:
        return "not json"


@pytest.fixture
def gov(session, ref):
    return GovernanceEngine(session, ref)


@pytest.fixture
def invoices(session, gov):
    return InvoiceService(session, gov)


@pytest.fixture
def approvals(session, gov, invoices):
    return ApprovalService(session, gov, invoices)


def events(gov, invoice_id):
    return [e.event_type.value for e in gov.audit.list_for_invoice(invoice_id)]


# --- state machine ---------------------------------------------------------


def test_happy_path_transitions():
    chain = [
        S.RECEIVED,
        S.EXTRACTED,
        S.VERIFYING,
        S.VERIFIED,
        S.RISK_REVIEW,
        S.APPROVED,
        S.COMPLETED,
    ]
    for a, b in zip(chain, chain[1:], strict=False):
        assert transition(a, b) == b


@pytest.mark.parametrize(
    "current,target",
    [
        (S.RECEIVED, S.COMPLETED),
        (S.BLOCKED, S.COMPLETED),
        (S.REJECTED, S.APPROVED),
        (S.COMPLETED, S.RECEIVED),
    ],
)
def test_invalid_transitions_raise(current, target):
    assert not can_transition(current, target)
    with pytest.raises(InvalidTransition):
        transition(current, target)


def test_human_paths_and_terminals():
    assert transition(S.PENDING_APPROVAL, S.APPROVED) == S.APPROVED
    assert transition(S.BLOCKED, S.REJECTED) == S.REJECTED
    assert all(is_terminal(s) for s in (S.COMPLETED, S.REJECTED, S.FAILED))
    assert not is_terminal(S.PENDING_APPROVAL)


# --- workflow ---------------------------------------------------------------


def test_low_risk_invoice_runs_to_completed(invoices, gov, fixture_by_id):
    fx = fixture_by_id("INV-1001")
    created = invoices.create(InvoiceUpload(**fx["upload"]))
    assert created.invoice_id == "INV-1001" and created.status == S.RECEIVED
    result = invoices.process("INV-1001")
    assert result.invoice.status == S.COMPLETED.value
    assert result.invoice.risk_level == "low" and result.invoice.recommendation == "approve"
    assert result.outcome.payment and result.approval_request is None
    assert (
        len(result.decisions) == 4 and len(result.tool_calls) == 6
    )  # parse, vendor, po, limit, rules, payment
    assert events(gov, "INV-1001") == fx["expected"]["audit_event_sequence"]
    assert gov.audit.get_trail("INV-1001").chain_valid


def test_processing_twice_is_rejected(invoices, fixture_by_id):
    invoices.create(InvoiceUpload(**fixture_by_id("INV-1001")["upload"]))
    invoices.process("INV-1001")
    with pytest.raises(InvalidStateError):
        invoices.process("INV-1001")


def test_intake_failure_ends_failed_and_escalated(session, gov, fixture_by_id):
    svc = InvoiceService(session, gov, llm=BrokenLLM())
    svc.create(InvoiceUpload(**fixture_by_id("INV-1001")["upload"]))
    result = svc.process("INV-1001")
    assert result.invoice.status == S.FAILED.value
    assert result.approval_request is not None  # escalated to a human
    assert ReasonCode.AGENT_FAILURE in result.outcome.reason_codes
    assert gov.payments.get_payment("INV-1001") is None
    seq = events(gov, "INV-1001")
    assert "agent_failed" in seq and seq[-1] == "audit_record_created"
    assert gov.audit.get_trail("INV-1001").chain_valid


def test_vendor_system_down_still_reaches_safe_state(session, ref, fixture_by_id):
    gov = GovernanceEngine(session, ref, vendor_service=VendorService(ref, available=False))
    svc = InvoiceService(session, gov)
    svc.create(InvoiceUpload(**fixture_by_id("INV-1001")["upload"]))
    result = svc.process("INV-1001")
    assert result.invoice.status == S.PENDING_APPROVAL.value
    assert ReasonCode.MOCK_SYSTEM_UNAVAILABLE in result.outcome.reason_codes
    assert gov.payments.get_payment("INV-1001") is None


def test_timeline_merges_decisions_calls_and_events(invoices, fixture_by_id):
    invoices.create(InvoiceUpload(**fixture_by_id("INV-1002")["upload"]))
    invoices.process("INV-1001")
    timeline = invoices.timeline("INV-1001")
    kinds = {e["kind"] for e in timeline["entries"]}
    assert kinds == {"decision", "tool_call", "event"}
    stamps = [e["timestamp"] for e in timeline["entries"]]
    assert stamps == sorted(stamps)


# --- human approval ---------------------------------------------------------


def test_human_approve_pays_and_completes(invoices, approvals, gov, fixture_by_id):
    invoices.create(InvoiceUpload(**fixture_by_id("INV-1002")["upload"]))
    invoices.process("INV-1001")
    invoice, approval = approvals.approve(
        "INV-1001", HumanDecisionInput(reviewer="fin@example.com", note="ok")
    )
    assert invoice.status == S.COMPLETED
    assert invoice.recommendation == Recommendation.ESCALATE  # AI recommendation kept separately
    assert approval["human_decision"] == "approved" and approval["reviewer"] == "fin@example.com"
    assert gov.payments.get_payment("INV-1001")["actor"] == "human_reviewer"
    assert events(gov, "INV-1001")[-3:] == [
        "human_decision_recorded",
        "payment_authorized",
        "audit_record_created",
    ]


def test_human_reject(invoices, approvals, gov, fixture_by_id):
    invoices.create(InvoiceUpload(**fixture_by_id("INV-1003")["upload"]))
    invoices.process("INV-1001")
    invoice, approval = approvals.reject("INV-1001", HumanDecisionInput(reviewer="fin@example.com"))
    assert invoice.status == S.REJECTED and approval["human_decision"] == "rejected"
    assert gov.payments.get_payment("INV-1001") is None
    with pytest.raises(InvalidStateError):
        approvals.approve("INV-1001", HumanDecisionInput(reviewer="fin@example.com"))


def test_cannot_decide_an_unprocessed_or_completed_invoice(invoices, approvals, fixture_by_id):
    invoices.create(InvoiceUpload(**fixture_by_id("INV-1001")["upload"]))
    with pytest.raises(InvalidStateError):
        approvals.approve("INV-1001", HumanDecisionInput(reviewer="fin@example.com"))
    invoices.process("INV-1001")
    with pytest.raises(InvalidStateError):
        approvals.reject("INV-1001", HumanDecisionInput(reviewer="fin@example.com"))


def test_human_limit_is_enforced(invoices, approvals, fixture_by_id):
    up = {**fixture_by_id("INV-1002")["upload"], "amount": 150000.0}
    invoices.create(InvoiceUpload(**up))
    result = invoices.process("INV-1001")
    assert result.invoice.status == S.BLOCKED.value  # PO mismatch + above limit
    with pytest.raises(ForbiddenError):
        approvals.approve("INV-1001", HumanDecisionInput(reviewer="fin@example.com"))
    assert invoices.get("INV-1001").status == S.BLOCKED


def test_every_action_creates_an_audit_event(invoices, gov, fixture_by_id):
    invoices.create(InvoiceUpload(**fixture_by_id("INV-1003")["upload"]))
    result = invoices.process("INV-1001")
    trail = gov.audit.get_trail("INV-1001")
    assert trail.chain_valid
    assert EventType.INVOICE_RECEIVED == trail.events[0].event_type
    assert len(trail.events) >= len(result.decisions) + 2
