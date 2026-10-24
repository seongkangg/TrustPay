"""Shared fixtures: a fresh in-memory SQLite session per test, reference data, demo fixtures,
and helpers that drive the four agents over a fixture."""

import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.database.database import Base
from backend.database.seed_data import get_reference_data, load_demo_invoices
from backend.database.tables import InvoiceRow
from backend.utils.timestamps import now_utc


@pytest.fixture
def session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    from backend.database import tables  # noqa: F401 — register tables

    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, future=True)
    s = Session()
    try:
        yield s
    finally:
        s.close()
        engine.dispose()


@pytest.fixture(scope="session")
def ref():
    return get_reference_data()


@pytest.fixture(scope="session")
def demo_invoices():
    return load_demo_invoices()


@pytest.fixture
def fixture_by_id(demo_invoices):
    def _get(invoice_id: str) -> dict:
        return next(d for d in demo_invoices if d["expected"]["invoice_id"] == invoice_id)

    return _get


def insert_invoice_row(session, fixture: dict, status: str = "COMPLETED") -> InvoiceRow:
    """Persist a fixture as an already-processed invoice (for duplicate checks)."""
    up = fixture["upload"]
    now = now_utc()
    row = InvoiceRow(
        invoice_id=fixture["expected"]["invoice_id"],
        correlation_id=str(uuid.uuid4()),
        vendor_invoice_number=up["vendor_invoice_number"],
        vendor_id=up.get("vendor_id"),
        vendor_name=up.get("vendor_name"),
        amount=up.get("amount"),
        currency=up.get("currency", "USD"),
        purchase_order_id=up.get("purchase_order_id"),
        status=status,
        created_at=now,
        updated_at=now,
    )
    session.add(row)
    session.commit()
    return row


def run_agents(gov, fixture: dict, llm=None, *, upto: int = 4):
    """ingest → intake → verification → policy/risk → approval. Returns the WorkflowContext."""
    from backend.agents import ApprovalAgent, IntakeAgent, PolicyRiskAgent, VerificationAgent
    from backend.orchestration.workflow_context import WorkflowContext

    invoice_id = fixture["expected"]["invoice_id"]
    correlation_id = f"corr-{invoice_id}"
    scan = gov.ingest(fixture["upload"], invoice_id=invoice_id, correlation_id=correlation_id)
    ctx = WorkflowContext.from_scan(scan, invoice_id=invoice_id, correlation_id=correlation_id)
    for agent_cls in (IntakeAgent, VerificationAgent, PolicyRiskAgent, ApprovalAgent)[:upto]:
        agent_cls(gov, llm).run(ctx)
    return ctx
