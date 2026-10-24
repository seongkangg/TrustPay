"""PDF → text → upload round-trips the demo fixtures exactly, and masking still applies."""

import pytest

from backend.governance import GovernanceEngine
from backend.inbox.pdf_parser import PdfParseError, extract_text, upload_from_text
from backend.models import InvoiceUpload
from backend.services.invoice_service import InvoiceService
from scripts.make_invoice_pdfs import render_invoice_pdf

COMPARED = (
    "vendor_invoice_number",
    "vendor_id",
    "vendor_name",
    "amount",
    "currency",
    "due_date",
    "purchase_order_id",
    "bank_account",
    "routing_number",
    "tax_id",
)


def test_every_fixture_round_trips_through_pdf(demo_invoices):
    for fx in demo_invoices:
        pdf = render_invoice_pdf(fx["upload"])
        upload = upload_from_text(extract_text(pdf), "invoice.pdf")
        for key in COMPARED:
            assert upload.get(key) == fx["upload"].get(key), (fx["scenario"], key)
        assert upload["source_document"] == "invoice.pdf"
        assert upload["raw_text"]
        InvoiceUpload(**upload)  # must validate as an upload


def test_label_variants_and_number_cleanup():
    text = "Total: $1,234.50\nPO: po-5001\nInvoice #: X-1\nEIN: 12-3456789\nCurrency: usd"
    up = upload_from_text(text, "x.pdf")
    assert up["amount"] == 1234.5 and up["purchase_order_id"] == "PO-5001"
    assert up["vendor_invoice_number"] == "X-1" and up["tax_id"] == "12-3456789"
    assert up["currency"] == "USD" and up["vendor_id"] is None


def test_corrupt_pdf_raises():
    with pytest.raises(PdfParseError):
        extract_text(b"this is not a pdf")


def test_emailed_suspicious_invoice_is_masked_on_create(session, ref, fixture_by_id):
    fx = fixture_by_id("INV-1003")
    text = extract_text(render_invoice_pdf(fx["upload"]))
    assert "987654326789" in text  # the PDF really carries the raw number
    upload = upload_from_text(text, "invoice.pdf")
    gov = GovernanceEngine(session, ref)
    created = InvoiceService(session, gov).create(InvoiceUpload(**upload))
    assert created.bank_account == "****6789" and created.sensitive_data_detected
    row = InvoiceService(session, gov).get_row(created.invoice_id)
    assert "987654326789" not in (row.raw_text or "")
