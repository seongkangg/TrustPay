"""Every row of docs/policy-matrix.md maps to the right risk, action, and reason code (A7)."""

import pytest

from backend.governance.policy_engine import PolicyEngine, PolicyInput
from backend.models import AgentName, InvoiceStatus, ReasonCode, RiskLevel


@pytest.fixture
def engine(ref):
    return PolicyEngine(ref.thresholds, ref.approval_limits)


def clean(**overrides) -> PolicyInput:
    """A fully verified, in-limit invoice. Override one thing per test."""
    base = dict(
        amount=4250.0,
        invoice_vendor_id="V-101",
        vendor_found=True,
        vendor_status="verified",
        po_found=True,
        po_vendor_id="V-101",
        po_amount=4250.0,
        min_confidence=0.95,
    )
    base.update(overrides)
    return PolicyInput(**base)


def policy_input_from_fixture(fx, ref) -> PolicyInput:
    up = fx["upload"]
    vendor = ref.vendors.get(up.get("vendor_id"))
    po = ref.purchase_orders.get(up.get("purchase_order_id"))
    return PolicyInput(
        amount=up["amount"],
        invoice_vendor_id=up.get("vendor_id"),
        vendor_found=vendor is not None,
        vendor_status=vendor["verification_status"] if vendor else None,
        po_found=po is not None,
        po_vendor_id=po["vendor_id"] if po else None,
        po_amount=po["approved_amount"] if po else None,
        duplicate_of=fx["expected"].get("duplicate_of"),
        sensitive_detected=any(k in up for k in ("bank_account", "routing_number", "tax_id")),
        min_confidence=0.95,
    )


# --- the four demo fixtures ------------------------------------------------


def test_fixtures_match_expected_policy_outcome(engine, ref, demo_invoices):
    status_map = {
        "COMPLETED": InvoiceStatus.APPROVED
    }  # policy stops at APPROVED; payment → COMPLETED
    for fx in demo_invoices:
        exp = fx["expected"]
        result = engine.evaluate(policy_input_from_fixture(fx, ref))
        assert result.risk_level == RiskLevel(exp["risk_level"]), exp["invoice_id"]
        assert {c.value for c in result.reason_codes} == set(exp["reason_codes"]), exp["invoice_id"]
        expected_status = status_map.get(exp["final_status"], InvoiceStatus(exp["final_status"]))
        assert result.target_status == expected_status, exp["invoice_id"]
        assert result.auto_payment_allowed == (not exp["human_approval_required"]), exp[
            "invoice_id"
        ]


# --- individual rules ------------------------------------------------------


def test_policy_001_002_low_risk_permits(engine):
    r = engine.evaluate(clean())
    assert r.risk_level == RiskLevel.LOW
    assert r.reason_codes == [ReasonCode.POLICY_PASSED]
    assert r.rules_triggered == ["POLICY-001", "POLICY-002"]
    assert r.auto_payment_allowed and r.target_status == InvoiceStatus.APPROVED


def test_policy_003_amount_above_agent_limit(engine):
    r = engine.evaluate(clean(amount=25000.0, po_amount=25000.0))
    assert r.risk_level == RiskLevel.HIGH
    assert r.reason_codes == [ReasonCode.AMOUNT_ABOVE_LIMIT]
    assert r.target_status == InvoiceStatus.PENDING_APPROVAL  # only reason → request approval
    assert "POLICY-003" in r.rules_triggered
    assert engine.limit_for(AgentName.APPROVAL) == 10000.0


def test_policy_004_unknown_vendor_is_a_review_not_a_block(engine):
    r = engine.evaluate(
        clean(vendor_found=False, vendor_status=None, po_found=None, po_vendor_id=None)
    )
    assert r.risk_level == RiskLevel.MEDIUM
    assert r.reason_codes == [ReasonCode.UNKNOWN_VENDOR]
    assert r.target_status == InvoiceStatus.PENDING_APPROVAL and not r.auto_payment_allowed


def test_unknown_vendor_with_bank_details_still_blocks(engine):
    r = engine.evaluate(clean(vendor_found=False, vendor_status=None, sensitive_detected=True))
    assert r.risk_level == RiskLevel.HIGH and r.target_status == InvoiceStatus.BLOCKED


def test_policy_005_unverified_vendor(engine):
    r = engine.evaluate(clean(vendor_status="pending"))
    assert r.risk_level == RiskLevel.MEDIUM
    assert r.reason_codes == [ReasonCode.VENDOR_UNVERIFIED]
    assert r.target_status == InvoiceStatus.PENDING_APPROVAL


def test_policy_006_duplicate(engine):
    r = engine.evaluate(clean(duplicate_of="INV-1001"))
    assert r.risk_level == RiskLevel.HIGH
    assert r.reason_codes == [ReasonCode.DUPLICATE_INVOICE]
    assert r.target_status == InvoiceStatus.BLOCKED


def test_policy_007_invalid_po(engine):
    missing = engine.evaluate(clean(po_found=False, po_vendor_id=None, po_amount=None))
    other_vendor = engine.evaluate(clean(po_vendor_id="V-102"))
    for r in (missing, other_vendor):
        assert r.risk_level == RiskLevel.HIGH
        assert ReasonCode.INVALID_PURCHASE_ORDER in r.reason_codes


def test_policy_008_po_amount_mismatch(engine):
    small = engine.evaluate(clean(amount=4300.0))  # ~1% over
    assert small.risk_level == RiskLevel.MEDIUM
    assert small.reason_codes == [ReasonCode.PO_AMOUNT_MISMATCH]
    big = engine.evaluate(clean(amount=5000.0))  # >10% over
    assert big.risk_level == RiskLevel.HIGH


def test_policy_009_sensitive_data(engine):
    r = engine.evaluate(clean(sensitive_detected=True))
    assert r.risk_level == RiskLevel.MEDIUM
    assert r.reason_codes == [ReasonCode.SENSITIVE_DATA_DETECTED]
    worse = engine.evaluate(clean(sensitive_detected=True, vendor_found=False, vendor_status=None))
    assert worse.risk_level == RiskLevel.HIGH


def test_policy_010_unauthorized_tool_call(engine):
    r = engine.evaluate(clean(unauthorized_tool_call=True))
    assert r.risk_level == RiskLevel.HIGH and ReasonCode.UNAUTHORIZED_TOOL_CALL in r.reason_codes


def test_policy_011_012_missing_and_malformed(engine):
    assert engine.evaluate(clean(missing_fields=["due_date"])).reason_codes == [
        ReasonCode.MISSING_REQUIRED_FIELD
    ]
    assert engine.evaluate(clean(malformed_fields=["amount"])).reason_codes == [
        ReasonCode.MALFORMED_FIELD
    ]


def test_policy_013_low_confidence(engine):
    r = engine.evaluate(clean(min_confidence=0.6))
    assert r.risk_level == RiskLevel.MEDIUM and r.reason_codes == [ReasonCode.LOW_CONFIDENCE]


def test_policy_015_016_failures(engine):
    assert engine.evaluate(clean(agent_failure=True)).reason_codes == [ReasonCode.AGENT_FAILURE]
    assert engine.evaluate(clean(mock_unavailable=True)).reason_codes == [
        ReasonCode.MOCK_SYSTEM_UNAVAILABLE
    ]


def test_default_safety_when_evidence_is_missing(engine):
    """No lookups happened → never a pass."""
    r = engine.evaluate(PolicyInput(amount=100.0))
    assert r.risk_level == RiskLevel.MEDIUM
    assert r.reason_codes == [ReasonCode.INSUFFICIENT_EVIDENCE]
    assert not r.auto_payment_allowed


def test_highest_risk_wins_and_low_reasons_are_dropped(engine):
    r = engine.evaluate(clean(vendor_status="pending", duplicate_of="INV-1001"))
    assert r.risk_level == RiskLevel.HIGH
    assert ReasonCode.POLICY_PASSED not in r.reason_codes
    assert set(r.reason_codes) == {ReasonCode.VENDOR_UNVERIFIED, ReasonCode.DUPLICATE_INVOICE}


def test_thresholds_come_from_fixture_not_code(ref):
    custom = PolicyEngine(
        {**ref.thresholds, "auto_approve_max_amount": 1000.0}, ref.approval_limits
    )
    assert custom.evaluate(clean()).rules_triggered == [
        "POLICY-001"
    ]  # 4250 > 1000 → POLICY-002 silent
