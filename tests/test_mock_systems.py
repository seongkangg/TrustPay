"""Mock enterprise systems return seeded records and fail safely (Sprint 1 done-criteria)."""

import pytest

from backend.mock_systems import MockSystemUnavailable, NotFound, UnauthorizedActor
from backend.mock_systems.approval_limit_service import ApprovalLimitService
from backend.mock_systems.payment_service import PaymentService
from backend.mock_systems.purchase_order_service import PurchaseOrderService
from backend.mock_systems.vendor_service import VendorService
from backend.models.enums import AgentName


def test_reference_data_loaded(ref):
    assert set(ref.vendors) == {"V-101", "V-102", "V-103"}
    assert set(ref.purchase_orders) == {"PO-5001", "PO-5002", "PO-5003"}
    assert ref.thresholds["auto_approve_max_amount"] == 10000.0
    assert ref.approval_limits["approval_agent"]["max_amount"] == 10000.0


def test_vendor_lookup_returns_seeded_vendor_and_masked_bank():
    vendor = VendorService().get_vendor("V-101")
    assert vendor["name"] == "Acme Office Supplies"
    assert vendor["verification_status"] == "verified"
    assert vendor["bank_account_masked"].startswith("****")


def test_unknown_vendor_raises_not_found():
    with pytest.raises(NotFound):
        VendorService().get_vendor("V-204")


def test_purchase_order_lookup():
    po = PurchaseOrderService().get_purchase_order("PO-5002")
    assert po["vendor_id"] == "V-102" and po["approved_amount"] == 25000.0
    with pytest.raises(NotFound):
        PurchaseOrderService().get_purchase_order("PO-7781")


def test_approval_limits_and_thresholds():
    svc = ApprovalLimitService()
    assert svc.get_limit("approval_agent")["may_execute_payment"] is False
    assert svc.get_limit("human_reviewer")["max_amount"] == 100000.0
    assert svc.get_thresholds()["confidence_threshold"] == 0.75


def test_unavailable_mock_raises():
    with pytest.raises(MockSystemUnavailable):
        VendorService(available=False).get_vendor("V-101")
    with pytest.raises(MockSystemUnavailable):
        PurchaseOrderService(available=False).get_purchase_order("PO-5001")


def test_payment_refuses_agents_and_double_payment():
    pay = PaymentService()
    with pytest.raises(UnauthorizedActor):
        pay.authorize("INV-1002", 25000.0, "USD", AgentName.APPROVAL)
    result = pay.authorize("INV-1001", 4250.0, "USD", AgentName.GOVERNANCE)
    assert result["status"] == "authorized" and result["simulated"] is True
    with pytest.raises(UnauthorizedActor):
        pay.authorize("INV-1001", 4250.0, "USD", AgentName.HUMAN_REVIEWER)


def test_agents_do_not_import_mock_systems_directly():
    """Part C: 0 imports of mock_systems from agents/."""
    from pathlib import Path

    agents_dir = Path(__file__).resolve().parent.parent / "backend" / "agents"
    import_lines = ("from backend.mock_systems", "import backend.mock_systems")
    offenders = [
        p.name
        for p in agents_dir.glob("*.py")
        if any(
            line.strip().startswith(import_lines)
            for line in p.read_text(encoding="utf-8").splitlines()
        )
    ]
    assert offenders == []
