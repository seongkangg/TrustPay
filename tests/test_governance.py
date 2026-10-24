"""Governance layer end-to-end: interceptor, scanner, validator, engine (acceptance B6, Part C)."""

from pathlib import Path

import pytest

from backend.governance import GovernanceEngine, PolicyInput
from backend.governance.decision_validator import parse_decision
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
    ToolCallRequest,
    ToolName,
)
from backend.utils.timestamps import now_utc

INV, CORR = "INV-1001", "corr-1001"


@pytest.fixture
def gov(session, ref):
    return GovernanceEngine(session, ref)


def tool_req(agent, tool, **params):
    return ToolCallRequest(
        agent=agent,
        tool=tool,
        purpose="needed for verification",
        parameters=params,
        invoice_id=INV,
        correlation_id=CORR,
    )


def decision(
    evidence,
    agent=AgentName.VERIFICATION,
    confidence=0.9,
    reasons=None,
    decision_id="DEC-001",
    **kw,
):
    return AgentDecision(
        decision_id=decision_id,
        invoice_id=INV,
        correlation_id=CORR,
        agent=agent,
        decision="vendor_verified",
        confidence=confidence,
        evidence_ids=list(evidence),
        explanation=Explanation(
            decision="verified", reasons=reasons or ["vendor found"], evidence=list(evidence)
        ),
        timestamp=now_utc(),
        **kw,
    )


def event_types(gov, invoice_id=INV):
    return [e.event_type for e in gov.audit.list_for_invoice(invoice_id)]


# --- tool-call interceptor -------------------------------------------------


def test_allowed_call_is_executed_logged_and_gets_evidence(gov):
    out = gov.call_tool(tool_req(AgentName.VERIFICATION, ToolName.VENDOR_LOOKUP, vendor_id="V-101"))
    assert out.ok and out.result["name"] == "Acme Office Supplies"
    assert out.call.authorization == Authorization.ALLOWED
    assert out.call.evidence_id == "VENDOR-LOOKUP-001"
    assert out.call.tool_call_id == "TOOL-001"
    assert "****" in out.call.result_summary and "1234" in out.call.result_summary


def test_not_found_is_an_allowed_call_with_empty_result(gov):
    out = gov.call_tool(tool_req(AgentName.VERIFICATION, ToolName.VENDOR_LOOKUP, vendor_id="V-204"))
    assert out.allowed and out.not_found and out.error is None
    assert out.call.evidence_id == "VENDOR-LOOKUP-001"


def test_unauthorized_call_is_blocked_logged_and_audited(gov):
    out = gov.call_tool(tool_req(AgentName.INTAKE, ToolName.VENDOR_LOOKUP, vendor_id="V-101"))
    assert not out.allowed and out.error == ReasonCode.UNAUTHORIZED_TOOL_CALL
    assert out.call.authorization == Authorization.BLOCKED
    assert out.call.evidence_id is None
    assert event_types(gov) == [EventType.TOOL_CALL_DENIED]
    denied = gov.audit.list_for_invoice(INV)[0]
    assert denied.related_tool_call_id == out.call.tool_call_id
    assert denied.policy_result == Authorization.BLOCKED


def test_agent_payment_attempt_is_blocked_immediately(gov):
    out = gov.call_tool(
        tool_req(
            AgentName.APPROVAL,
            ToolName.PAYMENT_AUTHORIZE,
            invoice_id=INV,
            amount=25000,
            currency="USD",
            actor="approval_agent",
        ),
        payment_permitted=True,
    )
    assert not out.allowed
    assert gov.payments.get_payment(INV) is None


def test_every_call_allowed_or_not_is_recorded(gov):
    gov.call_tool(tool_req(AgentName.VERIFICATION, ToolName.VENDOR_LOOKUP, vendor_id="V-101"))
    gov.call_tool(tool_req(AgentName.INTAKE, ToolName.PO_LOOKUP, purchase_order_id="PO-5001"))
    gov.call_tool(tool_req(AgentName.VERIFICATION, ToolName.PO_LOOKUP, purchase_order_id="PO-7781"))
    calls = gov.interceptor.calls_for(INV)
    assert [c.authorization for c in calls] == [
        Authorization.ALLOWED,
        Authorization.BLOCKED,
        Authorization.ALLOWED,
    ]
    assert gov.known_evidence(INV) == {"VENDOR-LOOKUP-001", "PO-LOOKUP-001"}


def test_unavailable_mock_surfaces_reason_code(session, ref):
    gov = GovernanceEngine(session, ref, vendor_service=VendorService(ref, available=False))
    out = gov.call_tool(tool_req(AgentName.VERIFICATION, ToolName.VENDOR_LOOKUP, vendor_id="V-101"))
    assert out.allowed and out.error == ReasonCode.MOCK_SYSTEM_UNAVAILABLE and out.result is None


# --- scanner ---------------------------------------------------------------


def test_ingest_masks_and_produces_scan_evidence(gov, demo_invoices):
    suspicious = next(d for d in demo_invoices if d["expected"]["invoice_id"] == "INV-1003")
    scan = gov.ingest(suspicious["upload"], invoice_id="INV-1003", correlation_id="c3")
    assert scan.found and scan.evidence_id == "SCAN-001"
    assert scan.masked["bank_account"] == "****6789"
    assert "987654326789" not in scan.masked["raw_text"]
    events = gov.audit.list_for_invoice("INV-1003")
    assert [e.event_type for e in events] == [EventType.SENSITIVE_DATA_MASKED]
    assert events[0].evidence_refs == ["SCAN-001"]
    assert "SCAN-001" in gov.known_evidence("INV-1003")


def test_ingest_clean_upload_emits_nothing(gov, demo_invoices):
    low = next(d for d in demo_invoices if d["expected"]["invoice_id"] == "INV-1001")
    scan = gov.ingest(low["upload"], invoice_id=INV, correlation_id=CORR)
    assert not scan.found and scan.evidence_id is None
    assert event_types(gov) == []


# --- decision validator ----------------------------------------------------


def test_decision_with_real_evidence_is_accepted(gov):
    gov.call_tool(tool_req(AgentName.VERIFICATION, ToolName.VENDOR_LOOKUP, vendor_id="V-101"))
    accepted, result = gov.accept_decision(decision(["VENDOR-LOOKUP-001"]))
    assert result.valid and accepted.governance_result == Authorization.ALLOWED


def test_fabricated_evidence_is_rejected(gov):
    accepted, result = gov.accept_decision(decision(["VENDOR-LOOKUP-999"]))
    assert not result.valid and accepted.governance_result == Authorization.BLOCKED
    assert ReasonCode.AGENT_FAILURE in result.reason_codes
    assert event_types(gov) == [EventType.AGENT_FAILED]


def test_decision_without_evidence_is_rejected(gov):
    _, result = gov.accept_decision(decision([]))
    assert not result.valid


def test_unmasked_data_in_explanation_is_rejected(gov):
    gov.call_tool(tool_req(AgentName.VERIFICATION, ToolName.VENDOR_LOOKUP, vendor_id="V-101"))
    _, result = gov.accept_decision(
        decision(["VENDOR-LOOKUP-001"], reasons=["remit to account 987654326789"])
    )
    assert not result.valid and ReasonCode.SENSITIVE_DATA_DETECTED in result.reason_codes


def test_low_reading_confidence_is_flagged_not_rejected(gov):
    gov.call_tool(tool_req(AgentName.VERIFICATION, ToolName.VENDOR_LOOKUP, vendor_id="V-101"))
    accepted, result = gov.accept_decision(
        decision(["VENDOR-LOOKUP-001"], agent=AgentName.INTAKE, confidence=0.5)
    )
    assert result.valid and result.low_confidence
    assert accepted.governance_result == Authorization.ESCALATED


def test_low_verification_confidence_is_not_unclear_details(gov):
    """A low Verification score means checks weren't confirmed — flagged by their own reason
    codes (New vendor, PO not found…), not as LOW_CONFIDENCE."""
    gov.call_tool(tool_req(AgentName.VERIFICATION, ToolName.VENDOR_LOOKUP, vendor_id="V-101"))
    accepted, result = gov.accept_decision(
        decision(["VENDOR-LOOKUP-001"], confidence=0.33, decision_id="DEC-002")
    )
    assert result.valid and not result.low_confidence
    assert accepted.governance_result == Authorization.ALLOWED


def test_role_requirements(gov):
    gov.call_tool(tool_req(AgentName.VERIFICATION, ToolName.VENDOR_LOOKUP, vendor_id="V-101"))
    _, no_risk = gov.accept_decision(decision(["VENDOR-LOOKUP-001"], agent=AgentName.POLICY_RISK))
    assert not no_risk.valid
    _, no_rec = gov.accept_decision(
        decision(["VENDOR-LOOKUP-001"], agent=AgentName.APPROVAL, decision_id="DEC-002")
    )
    assert not no_rec.valid


def test_parse_decision_rejects_malformed_output():
    assert parse_decision("not json") is None
    assert parse_decision({"decision_id": "DEC-001"}) is None
    assert (
        parse_decision({**decision(["POLICY-001"]).model_dump(mode="json"), "confidence": 1.7})
        is None
    )


# --- engine: evaluate + finalize ------------------------------------------


def low_risk_input():
    return PolicyInput(
        amount=4250.0,
        invoice_vendor_id="V-101",
        vendor_found=True,
        vendor_status="verified",
        po_found=True,
        po_vendor_id="V-101",
        po_amount=4250.0,
        min_confidence=0.95,
    )


def test_low_risk_invoice_is_paid_by_governance_only(gov):
    policy = gov.evaluate(low_risk_input(), invoice_id=INV, correlation_id=CORR)
    out = gov.finalize(
        invoice_id=INV,
        correlation_id=CORR,
        amount=4250.0,
        currency="USD",
        policy=policy,
        recommendation=Recommendation.APPROVE,
        confidence=0.95,
        evidence_ids=["POLICY-001"],
    )
    assert out.status == InvoiceStatus.APPROVED and out.payment["simulated"] is True
    assert event_types(gov) == [EventType.RISK_ASSIGNED, EventType.PAYMENT_AUTHORIZED]
    paying_call = gov.interceptor.calls_for(INV)[-1]
    assert (
        paying_call.agent == AgentName.GOVERNANCE and paying_call.tool == ToolName.PAYMENT_AUTHORIZE
    )
    assert gov.audit.get_trail(INV).chain_valid


def test_high_risk_invoice_is_blocked_and_escalated(gov):
    inp = low_risk_input()
    inp.amount = inp.po_amount = 25000.0
    policy = gov.evaluate(inp, invoice_id="INV-1002", correlation_id="c2")
    out = gov.finalize(
        invoice_id="INV-1002",
        correlation_id="c2",
        amount=25000.0,
        currency="USD",
        policy=policy,
        recommendation=Recommendation.ESCALATE,
        confidence=0.9,
        evidence_ids=["POLICY-003"],
    )
    assert out.status == InvoiceStatus.PENDING_APPROVAL and out.payment is None
    assert out.reason_codes == [ReasonCode.AMOUNT_ABOVE_LIMIT]
    assert out.approval_request["approval_id"] == "APR-001"
    assert out.approval_request["risk_level"] == "high"
    assert event_types(gov, "INV-1002") == [
        EventType.RISK_ASSIGNED,
        EventType.PAYMENT_BLOCKED,
        EventType.APPROVAL_REQUESTED,
    ]
    assert gov.payments.get_payment("INV-1002") is None
    assert gov.audit.get_trail("INV-1002").chain_valid


def test_agent_caution_on_low_risk_still_goes_to_human(gov):
    policy = gov.evaluate(low_risk_input(), invoice_id=INV, correlation_id=CORR)
    out = gov.finalize(
        invoice_id=INV,
        correlation_id=CORR,
        amount=4250.0,
        currency="USD",
        policy=policy,
        recommendation=Recommendation.ESCALATE,
        confidence=0.6,
        evidence_ids=["POLICY-001"],
    )
    assert out.status == InvoiceStatus.PENDING_APPROVAL and out.payment is None


def test_human_approval_then_payment(gov):
    inp = low_risk_input()
    inp.amount = inp.po_amount = 25000.0
    policy = gov.evaluate(inp, invoice_id="INV-1002", correlation_id="c2")
    gov.finalize(
        invoice_id="INV-1002",
        correlation_id="c2",
        amount=25000.0,
        currency="USD",
        policy=policy,
        recommendation=Recommendation.ESCALATE,
        confidence=0.9,
        evidence_ids=["POLICY-003"],
    )
    approval = gov.record_human_decision(
        invoice_id="INV-1002",
        correlation_id="c2",
        reviewer="finance.reviewer@example.com",
        decision=HumanDecision.APPROVED,
        note="PO confirmed",
    )
    assert (
        approval["human_decision"] == "approved"
        and approval["reviewer"] == "finance.reviewer@example.com"
    )
    pay = gov.execute_human_payment(
        invoice_id="INV-1002",
        correlation_id="c2",
        amount=25000.0,
        currency="USD",
        reviewer="finance.reviewer@example.com",
    )
    assert pay.ok and pay.call.agent == AgentName.HUMAN_REVIEWER
    assert event_types(gov, "INV-1002")[-2:] == [
        EventType.HUMAN_DECISION_RECORDED,
        EventType.PAYMENT_AUTHORIZED,
    ]
    assert gov.audit.get_trail("INV-1002").chain_valid


def test_explanation_is_built_from_policy_hits(gov):
    policy = gov.policy.evaluate(
        PolicyInput(amount=25000.0, vendor_found=False, sensitive_detected=True)
    )
    exp = gov.build_explanation(
        "Escalate", policy, ["VENDOR-LOOKUP-001", "SCAN-001"], next_step="route to finance reviewer"
    )
    assert exp.decision == "Escalate"
    assert any("vendor" in r for r in exp.reasons)
    assert "POLICY-004" in exp.policy_rules_triggered
    assert exp.evidence == ["VENDOR-LOOKUP-001", "SCAN-001"]


# --- structural guarantees -------------------------------------------------


def test_governance_package_has_no_llm_calls():
    gov_dir = Path(__file__).resolve().parent.parent / "backend" / "governance"
    forbidden = ("backend.llm", "watsonx", "granite", "openai")
    offenders = [
        p.name
        for p in gov_dir.glob("*.py")
        if any(tok in p.read_text(encoding="utf-8").lower() for tok in forbidden)
    ]
    assert offenders == []


def test_risk_levels_map_to_authorization(gov):
    for inp, expected in [
        (low_risk_input(), Authorization.ALLOWED),
        (
            PolicyInput(
                amount=100.0,
                vendor_found=True,
                vendor_status="pending",
                po_found=True,
                po_vendor_id="V-103",
                po_amount=100.0,
                invoice_vendor_id="V-103",
            ),
            Authorization.ESCALATED,
        ),
        (PolicyInput(amount=100.0, vendor_found=False), Authorization.ESCALATED),
        (
            PolicyInput(amount=100.0, vendor_found=False, sensitive_detected=True),
            Authorization.BLOCKED,
        ),
    ]:
        gov.evaluate(inp, invoice_id=INV, correlation_id=CORR)
        assert gov.audit.list_for_invoice(INV)[-1].policy_result == expected
    assert all(e.event_type == EventType.RISK_ASSIGNED for e in gov.audit.list_for_invoice(INV))
    assert RiskLevel.HIGH.value in gov.audit.list_for_invoice(INV)[-1].output_summary
