"""Hackathon targets (acceptance Part C): < 10 s per invoice end-to-end, < 1 s per audit event.

Measured in mock-LLM mode over HTTP, which is what the demo runs.
"""

import time

import pytest
from fastapi.testclient import TestClient

from backend.api.deps import get_payment_service
from backend.database.database import get_session
from backend.main import app
from backend.mock_systems.payment_service import PaymentService
from backend.models import AgentName, EventType, Severity
from backend.services.audit_service import AuditService

INVOICE_BUDGET_S = 10.0
AUDIT_EVENT_BUDGET_S = 1.0


@pytest.fixture
def client(session):
    payments = PaymentService()
    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[get_payment_service] = lambda: payments
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def test_each_demo_invoice_processes_within_budget(client, demo_invoices):
    timings = {}
    for fx in demo_invoices:
        start = time.perf_counter()
        created = client.post("/invoices", json=fx["upload"])
        processed = client.post(f"/invoices/{created.json()['invoice_id']}/process")
        elapsed = time.perf_counter() - start
        assert processed.status_code == 200
        timings[fx["expected"]["invoice_id"]] = elapsed
        assert elapsed < INVOICE_BUDGET_S, f"{fx['expected']['invoice_id']} took {elapsed:.2f}s"
    print({k: f"{v * 1000:.0f} ms" for k, v in timings.items()})


def test_audit_event_creation_within_budget(session):
    audit = AuditService(session)
    worst = 0.0
    for i in range(50):
        start = time.perf_counter()
        audit.append(
            invoice_id="INV-9000",
            correlation_id="perf",
            event_type=EventType.AUDIT_RECORD_CREATED,
            severity=Severity.LOW,
            actor=AgentName.SYSTEM,
            output_summary=f"perf event {i}",
        )
        worst = max(worst, time.perf_counter() - start)
    assert worst < AUDIT_EVENT_BUDGET_S, f"slowest append {worst:.3f}s"
    assert audit.get_trail("INV-9000").chain_valid
