"""Source-document PDFs: the redacted original kept at ingestion, and the masked-copy fallback.

The emailed PDF of the suspicious fixture carries a raw bank account, routing number and tax ID;
none of them may survive in the stored file, its text, or its bytes.
"""

import pymupdf
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from backend.api.deps import get_payment_service, get_session
from backend.database.tables import SourceDocumentRow
from backend.governance import GovernanceEngine
from backend.inbox.inbox_service import InboxService
from backend.main import app
from backend.mock_systems.payment_service import PaymentService
from backend.services.invoice_service import InvoiceService
from backend.services.source_pdf import redact_pdf
from scripts.make_invoice_pdfs import render_invoice_pdf
from tests.test_inbox import FakeGmailClient, inbox_msg

RAW = ("987654326789", "021000021", "12-3454321")


def _text(pdf: bytes) -> str:
    doc = pymupdf.open(stream=pdf, filetype="pdf")
    try:
        return "".join(page.get_text() for page in doc)
    finally:
        doc.close()


@pytest.fixture
def gov(session, ref):
    return GovernanceEngine(session, ref)


@pytest.fixture
def client(session):
    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[get_payment_service] = lambda: PaymentService()
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def test_redaction_removes_every_sensitive_value_and_keeps_the_rest(fixture_by_id):
    original = render_invoice_pdf(fixture_by_id("INV-1003")["upload"])
    assert all(raw in _text(original) for raw in RAW)  # the input really is sensitive

    redacted = redact_pdf(original)
    assert redacted is not None
    text = _text(redacted)
    for raw in RAW:
        assert raw not in text
        assert raw.encode() not in redacted
    for kept in ("Example Supplies", "25000.00", "PO-7781", "Bank Account"):
        assert kept in text


def test_redaction_refuses_scans_and_unreadable_files(fixture_by_id):
    src = pymupdf.open(
        stream=render_invoice_pdf(fixture_by_id("INV-1003")["upload"]), filetype="pdf"
    )
    picture = src[0].get_pixmap(dpi=100)
    scan = pymupdf.open()
    page = scan.new_page(width=src[0].rect.width, height=src[0].rect.height)
    page.insert_image(page.rect, pixmap=picture)

    assert redact_pdf(scan.tobytes()) is None  # numbers inside a picture cannot be verified
    assert redact_pdf(b"not a pdf") is None


def test_emailed_invoice_downloads_as_its_redacted_original(session, gov, fixture_by_id, client):
    pdf = render_invoice_pdf(fixture_by_id("INV-1003")["upload"])
    result = InboxService(session, gov, FakeGmailClient({"m-sus": inbox_msg("m-sus", pdf)})).sync()
    inv_id = result.created[0]

    stored = session.get(SourceDocumentRow, inv_id)
    assert stored is not None and not any(raw.encode() in stored.pdf for raw in RAW)
    assert InvoiceService(session, gov).get(inv_id).has_source_pdf is True

    r = client.get(f"/invoices/{inv_id}/document.pdf")
    assert r.status_code == 200 and r.headers["content-type"] == "application/pdf"
    assert f'filename="{inv_id}.pdf"' in r.headers["content-disposition"]
    assert r.content == stored.pdf
    assert "Example Supplies" in _text(r.content)
    assert not any(raw in _text(r.content) for raw in RAW)


def test_invoice_without_a_kept_pdf_falls_back_to_the_masked_copy(client, fixture_by_id):
    inv_id = client.post("/invoices", json=fixture_by_id("INV-1003")["upload"]).json()["invoice_id"]
    assert client.get(f"/invoices/{inv_id}").json()["has_source_pdf"] is False

    r = client.get(f"/invoices/{inv_id}/document.pdf")
    assert r.status_code == 200
    assert f'filename="{inv_id}-masked.pdf"' in r.headers["content-disposition"]
    assert "masked copy" in _text(r.content)


def test_demo_reset_clears_redacted_pdfs(session, gov, fixture_by_id, client):
    pdf = render_invoice_pdf(fixture_by_id("INV-1001")["upload"])
    InboxService(session, gov, FakeGmailClient({"m-low": inbox_msg("m-low", pdf)})).sync()
    assert session.scalar(select(func.count()).select_from(SourceDocumentRow)) == 1

    assert client.post("/demo/reset").status_code == 200
    assert session.scalar(select(func.count()).select_from(SourceDocumentRow)) == 0
