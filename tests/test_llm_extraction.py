"""Free-form invoices: model fallback for missing fields, every value checked against the
document, vendor matched by name through the governed lookup, dates normalized."""

import json

import pytest
from fpdf import FPDF

from backend.governance import GovernanceEngine
from backend.inbox import InboxMessage
from backend.inbox.inbox_service import InboxService, sanitize_upload
from backend.inbox.llm_extraction import appears_in_document, extract_missing_fields
from backend.inbox.pdf_parser import extract_text, normalize_date, upload_from_text
from backend.llm.granite_client import LLMError, MockLLM
from backend.mock_systems.vendor_service import VendorService, normalize_vendor_name
from backend.models import ReasonCode
from backend.services.invoice_service import InvoiceService


def two_column_invoice(vendor="ACME INC.", due="Due: November 22, 2026") -> bytes:
    """The layout from the user's example: letterhead left, invoice meta right, totals block."""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=11)

    def row(left, right=""):
        y = pdf.get_y()
        pdf.set_xy(10, y)
        pdf.cell(110, 6, left)
        pdf.set_xy(130, y)
        pdf.cell(70, 6, right, align="R")
        pdf.ln(6)

    row(vendor, "INVOICE")
    row("123 Main Street", "INV-1042")
    row("San Jose, CA 95112", "Date: October 23, 2026")
    row("billing@acme.com", due)
    row("Bill To:", "Ship To:")
    row("Example Corporation", "Example Corp")
    row("Description        Qty   Unit Price", "Total")
    row("Software license    2      $150.00", "$300.00")
    row("Support service     1      $100.00", "$100.00")
    row("", "Subtotal: $400.00")
    row("", "Tax: $32.00")
    row("", "TOTAL: $432.00")
    row("Payment terms: Net 30")
    row("Pay by bank transfer or: acme.com/pay")
    return bytes(pdf.output())


class FieldsLLM(MockLLM):
    """Answers the invoice_fields prompt with `answer`; everything else as the mock does."""

    mode = "fields"

    def __init__(self, answer: dict | str):
        self.answer = answer
        self.field_prompts: list[str] = []

    def complete(self, prompt: str, *, temperature: float = 0.0) -> str:
        if "<schema>invoice_fields</schema>" in prompt:
            self.field_prompts.append(prompt)
            return self.answer if isinstance(self.answer, str) else json.dumps(self.answer)
        return super().complete(prompt)


HONEST = {
    "vendor_invoice_number": "INV-1042",
    "vendor_name": "ACME INC.",
    "vendor_id": None,
    "amount": "$432.00",
    "currency": "$",
    "due_date": "November 22, 2026",
    "purchase_order_id": None,
}


# --- dates ------------------------------------------------------------------------


@pytest.mark.parametrize(
    "raw,iso",
    [
        ("2026-11-22", "2026-11-22"),
        ("November 22, 2026", "2026-11-22"),
        ("Nov 22, 2026", "2026-11-22"),
        ("Nov 22nd 2026", "2026-11-22"),
        ("22 November 2026", "2026-11-22"),
        ("11/22/2026", "2026-11-22"),
        ("Sept 3, 2026", "2026-09-03"),
        ("next Tuesday", None),
        ("", None),
    ],
)
def test_normalize_date(raw, iso):
    assert normalize_date(raw) == iso


def test_label_parser_normalizes_dates_and_reads_currency_symbol():
    up = upload_from_text("Due Date: November 22, 2026\nTotal: $1,248.00", "x.pdf")
    assert up["due_date"] == "2026-11-22" and up["amount"] == 1248.0 and up["currency"] == "USD"
    bad = upload_from_text("Due Date: whenever\nTotal: €10\nAlso $5", "x.pdf")
    assert bad["due_date"] is None  # unreadable → empty → escalated, never a crash
    assert bad["currency"] is None  # two kinds of symbol → not guessed


# --- the in-document check ----------------------------------------------------------------


def test_appears_in_document():
    text = extract_text(two_column_invoice())
    assert appears_in_document("vendor_invoice_number", "INV-1042", text)
    assert not appears_in_document("vendor_invoice_number", "INV-9999", text)
    assert appears_in_document("amount", "432", text) and appears_in_document(
        "amount", "$432.00", text
    )
    assert not appears_in_document("amount", "999.00", text)
    assert appears_in_document(
        "due_date", "2026-11-22", text
    )  # reformatted by the model, same date
    assert not appears_in_document("due_date", "2026-12-01", text)
    assert appears_in_document("currency", "USD", text)  # via the $ symbol
    assert not appears_in_document("currency", "EUR", text)
    assert appears_in_document("vendor_name", "acme   inc.", text)  # case / spacing tolerant


# --- extraction ------------------------------------------------------------------------------


def test_model_fills_only_missing_fields_with_normalized_values():
    text = extract_text(two_column_invoice())
    upload = upload_from_text(text, "invoice.pdf")
    assert upload["amount"] == 432.0  # labels already got this one
    llm = FieldsLLM(HONEST)
    out = extract_missing_fields(llm, text, upload)
    assert out.filled == {
        "vendor_invoice_number": "INV-1042",
        "vendor_name": "ACME INC.",
        "due_date": "2026-11-22",
    }
    assert out.rejected == {} and out.error is None
    sent = json.loads(llm.field_prompts[0].split("<context>")[1].split("</context>")[0])
    assert "amount" not in sent["fields_needed"] and "vendor_name" in sent["fields_needed"]


def test_invented_values_are_discarded():
    text = extract_text(two_column_invoice())
    upload = upload_from_text(text, "invoice.pdf")
    upload["amount"] = None  # pretend the labels missed it too
    lies = {
        **HONEST,
        "vendor_invoice_number": "INV-9999",
        "amount": "4320.00",
        "purchase_order_id": "PO-5001",
    }
    out = extract_missing_fields(FieldsLLM(lies), text, upload)
    assert out.rejected == {
        "vendor_invoice_number": "INV-9999",
        "amount": "4320.00",
        "purchase_order_id": "PO-5001",
    }
    assert "vendor_invoice_number" not in out.filled and "amount" not in out.filled


def test_model_sees_masked_text_only():
    pdf = two_column_invoice().replace(b"", b"")
    text = extract_text(pdf) + "\nRemit to account 987654326789, routing 021000021"
    llm = FieldsLLM(HONEST)
    extract_missing_fields(llm, text, upload_from_text(text, "invoice.pdf"))
    assert "987654326789" not in llm.field_prompts[0] and "****6789" in llm.field_prompts[0]


@pytest.mark.parametrize("answer", ["not json", '{"amount": [1]}'])
def test_bad_model_output_fills_nothing(answer):
    text = extract_text(two_column_invoice())
    out = extract_missing_fields(FieldsLLM(answer), text, upload_from_text(text, "invoice.pdf"))
    assert out.filled == {} and out.error


def test_model_down_fills_nothing():
    class Down(MockLLM):
        def complete(self, prompt, *, temperature=0.0):
            raise LLMError("ollama not running")

    text = extract_text(two_column_invoice())
    out = extract_missing_fields(Down(), text, upload_from_text(text, "invoice.pdf"))
    assert out.filled == {} and "ollama" in out.error


def test_mock_llm_fills_nothing_so_demo_stays_deterministic():
    text = extract_text(two_column_invoice())
    out = extract_missing_fields(MockLLM(), text, upload_from_text(text, "invoice.pdf"))
    assert out.filled == {} and out.rejected == {}


# --- vendor names -----------------------------------------------------------------------------


def test_vendor_name_normalization_is_exact_not_fuzzy(ref):
    assert normalize_vendor_name("Acme Office Supplies, Inc.") == "acme office supplies"
    vendors = VendorService(ref)
    assert vendors.find_by_name("ACME OFFICE SUPPLIES INC.")["vendor_id"] == "V-101"
    assert vendors.find_by_name("Northwind Logistics LLC")["vendor_id"] == "V-102"
    assert vendors.find_by_name("ACME INC.") is None  # a different company — not guessed
    assert vendors.find_by_name("") is None


# --- end to end through the inbox ----------------------------------------------------------------


class OneEmail:
    def __init__(self, pdf: bytes):
        self.pdf = pdf

    def list_candidates(self, days):
        return ["m-acme"]

    def fetch(self, message_id):
        return InboxMessage(
            message_id, "t", "billing@acme.com", "Invoice INV-1042", None, "invoice.pdf", self.pdf
        )


def reasons(gov, session, invoice_id):
    decisions = InvoiceService(session, gov).decisions(invoice_id)
    return next(d for d in decisions if d.agent.value == "policy_risk_agent").reason_codes


def test_two_column_invoice_end_to_end_unknown_vendor(session, ref):
    gov = GovernanceEngine(session, ref)
    res = InboxService(session, gov, OneEmail(two_column_invoice()), llm=FieldsLLM(HONEST)).sync()
    inv = InvoiceService(session, gov).get(res.created[0])
    assert inv.vendor_invoice_number == "INV-1042" and inv.vendor_name == "ACME INC."
    assert inv.amount == 432.0 and inv.currency.value == "USD" and str(inv.due_date) == "2026-11-22"
    assert inv.vendor_id is None
    codes = reasons(gov, session, inv.invoice_id)
    assert ReasonCode.UNKNOWN_VENDOR in codes and ReasonCode.AGENT_FAILURE not in codes
    assert (
        inv.status.value in ("PENDING_APPROVAL", "BLOCKED")
        and gov.payments.get_payment(inv.invoice_id) is None
    )
    lookup = next(
        c for c in gov.interceptor.calls_for(inv.invoice_id) if c.tool.value == "vendor_lookup"
    )
    assert (
        lookup.parameters == {"vendor_name": "ACME INC."} and lookup.evidence_id
    )  # governed, evidenced


def test_known_vendor_resolved_by_name(session, ref):
    gov = GovernanceEngine(session, ref)
    answer = {**HONEST, "vendor_name": "ACME OFFICE SUPPLIES INC."}
    pdf = two_column_invoice(vendor="ACME OFFICE SUPPLIES INC.")
    res = InboxService(session, gov, OneEmail(pdf), llm=FieldsLLM(answer)).sync()
    inv = InvoiceService(session, gov).get(res.created[0])
    assert inv.vendor_id == "V-101"  # resolved and persisted
    codes = reasons(gov, session, inv.invoice_id)
    assert ReasonCode.UNKNOWN_VENDOR not in codes
    assert ReasonCode.MISSING_REQUIRED_FIELD in codes  # still no PO on the invoice → escalated
    assert gov.payments.get_payment(inv.invoice_id) is None


def test_with_mock_llm_the_same_invoice_still_escalates(session, ref):
    gov = GovernanceEngine(session, ref)
    res = InboxService(session, gov, OneEmail(two_column_invoice())).sync()
    inv = InvoiceService(session, gov).get(res.created[0])
    assert inv.vendor_invoice_number.startswith("EMAIL-") and inv.amount == 432.0
    assert inv.status.value in ("PENDING_APPROVAL", "BLOCKED", "FAILED")
    assert gov.payments.get_payment(inv.invoice_id) is None


def test_invalid_field_is_dropped_not_the_whole_email():
    clean, dropped = sanitize_upload(
        {
            "vendor_invoice_number": "X-1",
            "purchase_order_id": "PO 5001",
            "amount": -5,
            "vendor_id": "V-101",
        }
    )
    assert dropped == {"purchase_order_id": "PO 5001", "amount": -5}
    assert (
        clean["purchase_order_id"] is None
        and clean["amount"] is None
        and clean["vendor_id"] == "V-101"
    )
