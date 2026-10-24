"""Verification Agent (acceptance B2)."""

import pytest

from backend.governance import GovernanceEngine
from backend.mock_systems.vendor_service import VendorService
from backend.models import AgentName, Authorization, EventType, ReasonCode, ToolName
from tests.conftest import insert_invoice_row, run_agents


@pytest.fixture
def gov(session, ref):
    return GovernanceEngine(session, ref)


def events(gov, invoice_id):
    return [e.event_type for e in gov.audit.list_for_invoice(invoice_id)]


def test_verified_vendor_and_matching_po(gov, fixture_by_id):
    ctx = run_agents(gov, fixture_by_id("INV-1001"), upto=2)
    d = ctx.decisions[-1]
    assert d.agent == AgentName.VERIFICATION and d.decision == "vendor_verified"
    assert d.confidence == 1.0 and d.governance_result == Authorization.ALLOWED
    assert d.reason_codes == []
    assert set(d.evidence_ids) == {"VENDOR-LOOKUP-001", "PO-LOOKUP-001"}
    assert ctx.vendor_found and ctx.po_found and ctx.duplicate_of is None
    assert events(gov, "INV-1001")[1:] == [
        EventType.VENDOR_LOOKUP_REQUESTED,
        EventType.VENDOR_VERIFIED,
        EventType.PURCHASE_ORDER_CHECKED,
    ]


def test_unknown_vendor_and_missing_po(gov, fixture_by_id):
    ctx = run_agents(gov, fixture_by_id("INV-1003"), upto=2)
    d = ctx.decisions[-1]
    assert d.decision == "vendor_unknown"
    assert set(d.reason_codes) == {ReasonCode.UNKNOWN_VENDOR, ReasonCode.INVALID_PURCHASE_ORDER}
    assert ctx.vendor_found is False and ctx.po_found is False
    assert EventType.VENDOR_UNVERIFIED in events(gov, "INV-1003")


def test_duplicate_detected_against_processed_invoice(gov, fixture_by_id, session):
    insert_invoice_row(session, fixture_by_id("INV-1001"))
    ctx = run_agents(gov, fixture_by_id("INV-1004"), upto=2)
    d = ctx.decisions[-1]
    assert d.decision == "duplicate_detected" and ctx.duplicate_of == "INV-1001"
    assert ReasonCode.DUPLICATE_INVOICE in d.reason_codes
    assert any(e.startswith("DUP-CHECK-") for e in d.evidence_ids)
    assert EventType.DUPLICATE_DETECTED in events(gov, "INV-1004")
    assert d.governance_result == Authorization.ALLOWED  # evidence resolves → accepted


def test_no_duplicate_without_prior_invoice(gov, fixture_by_id):
    ctx = run_agents(gov, fixture_by_id("INV-1004"), upto=2)
    assert ctx.duplicate_of is None


def test_po_amount_mismatch_and_wrong_vendor(gov, fixture_by_id):
    fx = fixture_by_id("INV-1001")
    mismatch = {
        **fx,
        "upload": {**fx["upload"], "amount": 4300.0},
        "expected": {"invoice_id": "INV-2002"},
    }
    ctx = run_agents(gov, mismatch, upto=2)
    assert ctx.decisions[-1].decision == "po_mismatch"
    assert ReasonCode.PO_AMOUNT_MISMATCH in ctx.decisions[-1].reason_codes

    wrong_vendor = {
        **fx,
        "upload": {**fx["upload"], "purchase_order_id": "PO-5002"},
        "expected": {"invoice_id": "INV-2003"},
    }
    ctx2 = run_agents(gov, wrong_vendor, upto=2)
    assert ctx2.decisions[-1].decision == "po_invalid"


def test_only_lookup_tools_are_used(gov, fixture_by_id):
    ctx = run_agents(gov, fixture_by_id("INV-1001"), upto=2)
    tools = {
        c.tool
        for c in gov.interceptor.calls_for(ctx.invoice_id)
        if c.agent == AgentName.VERIFICATION
    }
    assert tools == {ToolName.VENDOR_LOOKUP, ToolName.PO_LOOKUP}
    assert all(not c.is_write for c in gov.interceptor.calls_for(ctx.invoice_id))


def test_vendor_system_down_stops_and_escalates(session, ref, fixture_by_id):
    gov = GovernanceEngine(session, ref, vendor_service=VendorService(ref, available=False))
    ctx = run_agents(gov, fixture_by_id("INV-1001"), upto=2)
    d = ctx.decisions[-1]
    assert d.decision == "verification_unavailable" and ctx.mock_unavailable
    assert ReasonCode.MOCK_SYSTEM_UNAVAILABLE in d.reason_codes
    assert ctx.vendor_found is None  # never assumed valid
    assert d.governance_result == Authorization.ESCALATED  # confidence 0.5 → human review
