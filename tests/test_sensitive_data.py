"""Masking rules (Sprint 1). Detection + SCAN evidence tests are added with the scanner in Sprint 2."""

import json
import logging

from backend.models.enums import SensitiveFieldType
from backend.services.masking_service import (
    contains_unmasked,
    mask_field,
    mask_last4,
    mask_text,
    mask_upload,
)
from backend.utils.logging_config import JsonFormatter, MaskingFilter


def test_mask_last4_keeps_only_last_four_digits():
    assert mask_last4("987654326789") == "****6789"
    assert mask_last4("12-3454321") == "****4321"
    assert mask_last4("123") == "****"


def test_mask_field_masks_structured_sensitive_fields():
    masked, det = mask_field("bank_account", "987654326789")
    assert masked == "****6789"
    assert det.field_type == SensitiveFieldType.BANK_ACCOUNT


def test_mask_field_is_idempotent_and_ignores_other_fields():
    assert mask_field("bank_account", "****6789") == ("****6789", None)
    assert mask_field("vendor_name", "Acme") == ("Acme", None)


def test_mask_text_masks_account_routing_and_tax_id():
    text = "Please remit to account 987654326789, routing 021000021. Tax ID 12-3454321."
    masked, detections = mask_text(text)
    assert "987654326789" not in masked
    assert "021000021" not in masked
    assert "12-3454321" not in masked
    assert "****6789" in masked and "****0021" in masked and "****4321" in masked
    assert {d.field_type for d in detections} == {
        SensitiveFieldType.BANK_ACCOUNT,
        SensitiveFieldType.ROUTING_NUMBER,
        SensitiveFieldType.TAX_ID,
    }


def test_mask_text_redacts_card_numbers_and_api_keys():
    masked, detections = mask_text("card 4111 1111 1111 1111, Bearer abcdefghijklmnop1234567890")
    assert "4111" not in masked
    assert "abcdefghijklmnop" not in masked
    assert masked.count("[REDACTED]") == 2
    assert {d.field_type for d in detections} == {
        SensitiveFieldType.PAYMENT_CREDENTIAL,
        SensitiveFieldType.API_KEY,
    }


def test_mask_text_leaves_amounts_ids_and_masked_values_alone():
    text = "INV-1002 for 25000.0 USD on PO-5002, account ****6789"
    masked, detections = mask_text(text)
    assert masked == text
    assert detections == []


def test_mask_upload_masks_suspicious_fixture(demo_invoices):
    suspicious = next(d for d in demo_invoices if d["expected"]["invoice_id"] == "INV-1003")
    masked, detections = mask_upload(suspicious["upload"])
    assert masked["bank_account"] == suspicious["expected"]["masked_fields"]["bank_account"]
    assert masked["routing_number"] == suspicious["expected"]["masked_fields"]["routing_number"]
    assert masked["tax_id"] == suspicious["expected"]["masked_fields"]["tax_id"]
    assert not contains_unmasked(masked["raw_text"])
    assert len(detections) >= 3
    # the input dict is not modified
    assert suspicious["upload"]["bank_account"] == "987654326789"


def test_served_source_text_is_masked(session, ref, demo_invoices):
    # The review screen shows the source document's text; it must never carry a raw identifier,
    # including from a row whose raw_text was somehow stored unmasked.
    from backend.governance import GovernanceEngine
    from backend.models import InvoiceUpload
    from backend.services.invoice_service import InvoiceService

    invoices = InvoiceService(session, GovernanceEngine(session, ref))
    suspicious = next(d for d in demo_invoices if d["expected"]["invoice_id"] == "INV-1003")
    created = invoices.create(InvoiceUpload(**suspicious["upload"]))

    text = invoices.get(created.invoice_id).source_text
    assert text and "****6789" in text
    assert not contains_unmasked(text)

    row = invoices.get_row(created.invoice_id)
    row.raw_text = "Bank Account: 987654326789 Routing Number: 021000021 Tax ID: 12-3454321"
    session.commit()
    served = invoices.get(created.invoice_id).source_text
    assert not contains_unmasked(served)
    assert "987654326789" not in served and "021000021" not in served


def test_source_document_pdf_is_a_masked_copy(session, demo_invoices):
    # GET /invoices/{id}/document.pdf rebuilds the source document from its masked text; the
    # downloaded file must never carry a raw identifier. No source text means 404.
    from io import BytesIO

    from fastapi.testclient import TestClient
    from pypdf import PdfReader

    from backend.api.deps import get_session
    from backend.main import app

    app.dependency_overrides[get_session] = lambda: session
    try:
        client = TestClient(app)
        suspicious = next(d for d in demo_invoices if d["expected"]["invoice_id"] == "INV-1003")
        inv_id = client.post("/invoices", json=suspicious["upload"]).json()["invoice_id"]

        r = client.get(f"/invoices/{inv_id}/document.pdf")
        assert r.status_code == 200
        assert r.headers["content-type"] == "application/pdf"
        assert "attachment" in r.headers["content-disposition"]
        text = " ".join(p.extract_text() for p in PdfReader(BytesIO(r.content)).pages)
        assert "****6789" in text and "masked copy" in text
        assert not contains_unmasked(text)
        for raw in ("987654326789", "021000021", "12-3454321"):
            assert raw not in text

        clean = next(d for d in demo_invoices if d["expected"]["invoice_id"] == "INV-1001")
        clean_id = client.post("/invoices", json=clean["upload"]).json()["invoice_id"]
        assert client.get(f"/invoices/{clean_id}/document.pdf").status_code == 404
    finally:
        app.dependency_overrides.clear()


def test_mask_upload_clean_fixture_has_no_detections(demo_invoices):
    low = next(d for d in demo_invoices if d["expected"]["invoice_id"] == "INV-1001")
    _, detections = mask_upload(low["upload"])
    assert detections == []


def test_log_lines_are_masked_json():
    record = logging.LogRecord(
        "t", logging.INFO, __file__, 1, "vendor bank account 987654326789", None, None
    )
    record.invoice_id = "INV-1003"
    assert MaskingFilter().filter(record)
    line = json.loads(JsonFormatter().format(record))
    assert "987654326789" not in line["message"]
    assert "****6789" in line["message"]
    assert line["invoice_id"] == "INV-1003"
