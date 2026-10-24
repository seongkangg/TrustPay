"""The four demo fixtures end-to-end through the HTTP API (acceptance Part D), plus the
API contract edges: masked responses, error format, dry-run governance, dashboard summary."""

import json

import pytest
from fastapi.testclient import TestClient

from backend.api.deps import get_payment_service
from backend.database.database import get_session
from backend.main import app
from backend.mock_systems.payment_service import PaymentService

RAW_SECRETS = ("987654326789", "021000021", "12-3454321")


@pytest.fixture
def client(session):
    payments = PaymentService()
    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[get_payment_service] = lambda: payments
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def create_and_process(client, fx):
    created = client.post("/invoices", json=fx["upload"])
    assert created.status_code == 201, created.text
    invoice_id = created.json()["invoice_id"]
    processed = client.post(f"/invoices/{invoice_id}/process")
    assert processed.status_code == 200, processed.text
    return invoice_id, created.json(), processed.json()


def policy_reason_codes(processed):
    return next(d for d in processed["decisions"] if d["agent"] == "policy_risk_agent")[
        "reason_codes"
    ]


# --- Part D: every fixture, in demo order ------------------------------------


def test_all_four_scenarios_in_demo_order(client, demo_invoices):
    for fx in demo_invoices:
        exp = fx["expected"]
        invoice_id, created, processed = create_and_process(client, fx)
        assert invoice_id == exp["invoice_id"]
        assert created["status"] == "RECEIVED"

        inv = processed["invoice"]
        assert inv["status"] == exp["final_status"], exp["invoice_id"]
        assert inv["risk_level"] == exp["risk_level"], exp["invoice_id"]
        assert inv["recommendation"] == exp["recommendation"], exp["invoice_id"]
        assert inv["sensitive_data_detected"] == exp["sensitive_data_detected"], exp["invoice_id"]
        assert set(policy_reason_codes(processed)) == set(exp["reason_codes"]), exp["invoice_id"]
        assert (processed["approval_request"] is not None) == exp["human_approval_required"], exp[
            "invoice_id"
        ]
        for field, masked in exp.get("masked_fields", {}).items():
            assert inv[field] == masked, (exp["invoice_id"], field)

        audit = client.get(f"/invoices/{invoice_id}/audit").json()
        assert [e["event_type"] for e in audit["events"]] == exp["audit_event_sequence"], exp[
            "invoice_id"
        ]
        assert audit["chain_valid"]

    summary = client.get("/dashboard/summary").json()
    assert summary["total_invoices"] == 4
    assert summary["by_risk"] == {"low": 1, "medium": 0, "high": 3}
    assert summary["by_status"] == {"COMPLETED": 1, "PENDING_APPROVAL": 1, "BLOCKED": 2}
    assert summary["blocked_actions"] == 3 and summary["pending_approvals"] == 3
    assert summary["sensitive_data_detections"] == 1
    assert {v["invoice_id"] for v in summary["recent_violations"]} == {
        "INV-1002",
        "INV-1003",
        "INV-1004",
    }


def test_spec_worked_example_is_blocked_masked_and_explained(client, fixture_by_id):
    """$25,000 from a new vendor with banking info → blocked, masked, escalated, fully recorded."""
    invoice_id, _, processed = create_and_process(client, fixture_by_id("INV-1003"))
    inv = processed["invoice"]
    assert inv["status"] == "BLOCKED" and inv["bank_account"] == "****6789"
    approval = processed["decisions"][-1]
    assert approval["agent"] == "approval_agent" and approval["recommendation"] == "escalate"
    assert approval["explanation"]["reasons"] and approval["explanation"]["evidence"]
    assert any(r.startswith("POLICY-") for r in approval["explanation"]["policy_rules_triggered"])
    tools = [c["tool"] for c in processed["tool_calls"]]
    assert "vendor_lookup" in tools and "payment_authorize" not in tools
    for path in (
        f"/invoices/{invoice_id}",
        f"/invoices/{invoice_id}/timeline",
        f"/invoices/{invoice_id}/audit",
    ):
        body = client.get(path).text
        assert not any(secret in body for secret in RAW_SECRETS), path
    assert not any(secret in json.dumps(processed) for secret in RAW_SECRETS)


# --- human decisions over HTTP -------------------------------------------------


def test_human_approve_round_trip(client, fixture_by_id):
    invoice_id, _, processed = create_and_process(client, fixture_by_id("INV-1002"))
    assert processed["invoice"]["status"] == "PENDING_APPROVAL"
    r = client.post(
        f"/invoices/{invoice_id}/approve",
        json={"reviewer": "fin@example.com", "note": "PO confirmed"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["invoice"]["status"] == "COMPLETED"
    assert r.json()["approval"]["human_decision"] == "approved"
    assert r.json()["invoice"]["recommendation"] == "escalate"  # recommendation ≠ human decision
    again = client.post(f"/invoices/{invoice_id}/approve", json={"reviewer": "fin@example.com"})
    assert again.status_code == 409 and again.json()["error"] == "INVALID_TRANSITION"


def test_human_reject_round_trip(client, fixture_by_id):
    invoice_id, _, _ = create_and_process(client, fixture_by_id("INV-1003"))
    r = client.post(f"/invoices/{invoice_id}/reject", json={"reviewer": "fin@example.com"})
    assert r.status_code == 200 and r.json()["invoice"]["status"] == "REJECTED"
    events = [e["event_type"] for e in client.get(f"/invoices/{invoice_id}/audit").json()["events"]]
    assert events[-2:] == ["human_decision_recorded", "audit_record_created"]


# --- contract edges ----------------------------------------------------------


def test_error_format_and_status_codes(client, fixture_by_id):
    missing = client.get("/invoices/INV-9999")
    assert missing.status_code == 404
    body = missing.json()
    assert set(body) == {"error", "message", "invoice_id", "correlation_id", "timestamp"}
    assert body["error"] == "NOT_FOUND" and body["invoice_id"] == "INV-9999"

    invoice_id, _, _ = create_and_process(client, fixture_by_id("INV-1001"))
    twice = client.post(f"/invoices/{invoice_id}/process")
    assert twice.status_code == 409 and twice.json()["error"] == "INVALID_TRANSITION"

    bad = client.post("/invoices", json={"vendor_invoice_number": "X", "amount": -1})
    assert bad.status_code == 422


def test_list_and_filters(client, demo_invoices):
    for fx in demo_invoices[:2]:
        create_and_process(client, fx)
    assert client.get("/invoices").json()["total"] == 2
    high = client.get("/invoices", params={"risk_level": "high"}).json()
    assert [i["invoice_id"] for i in high["items"]] == ["INV-1002"]
    pending = client.get("/invoices", params={"status": "PENDING_APPROVAL"}).json()
    assert pending["total"] == 1


def test_evaluate_tool_call_dry_run_is_audited(client, fixture_by_id):
    invoice_id, created, _ = create_and_process(client, fixture_by_id("INV-1001"))
    r = client.post(
        "/governance/evaluate-tool-call",
        json={
            "agent": "approval_agent",
            "tool": "payment_authorize",
            "purpose": "pay the invoice now",
            "parameters": {"invoice_id": invoice_id, "amount": 4250},
            "invoice_id": invoice_id,
            "correlation_id": created["correlation_id"],
        },
    )
    assert r.status_code == 200
    assert r.json()["authorization"] == "blocked"
    assert r.json()["denial_reason"] == "UNAUTHORIZED_TOOL_CALL"
    assert r.json()["policy_rules_triggered"] == ["POLICY-014"]
    events = [e["event_type"] for e in client.get(f"/invoices/{invoice_id}/audit").json()["events"]]
    assert events[-1] == "tool_call_denied"


def test_mock_inspection_routes(client):
    assert client.get("/mock/vendors/V-101").json()["name"] == "Acme Office Supplies"
    assert client.get("/mock/vendors/V-204").status_code == 404
    assert client.get("/mock/purchase-orders/PO-5002").json()["approved_amount"] == 25000.0
    assert client.get("/mock/approval-limits/approval_agent").json()["max_amount"] == 10000.0
    assert client.get("/mock/thresholds").json()["confidence_threshold"] == 0.75


def test_health(client):
    body = client.get("/health").json()
    assert body["status"] == "ok" and body["llm_mode"] == "mock"


def test_list_rows_carry_the_recommendation_confidence(client, demo_invoices):
    invoice_id, _, processed = create_and_process(client, demo_invoices[0])
    rows = client.get("/invoices").json()["items"]
    row = next(r for r in rows if r["invoice_id"] == invoice_id)
    assert row["recommendation_confidence"] == processed["invoice"]["recommendation_confidence"]
    assert row["recommendation_confidence"] is not None
