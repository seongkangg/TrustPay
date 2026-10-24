"""A real-world invoice layout must not be flagged worse than it is.

Modeled on a real supplier invoice (Canadian vendor, unlabelled invoice number, day-first dates,
international phone number, no purchase order). The data here is synthetic — the real PDF is not
kept in the repo. Before the fix it came out High risk with UNKNOWN_VENDOR, MISSING_REQUIRED_FIELD,
LOW_CONFIDENCE and SENSITIVE_DATA_DETECTED; only the first two are true.
"""

import json

import pytest
from fpdf import FPDF

from backend.governance import GovernanceEngine
from backend.inbox import InboxMessage
from backend.inbox.inbox_service import InboxService
from backend.inbox.llm_extraction import normalize
from backend.inbox.pdf_parser import normalize_date
from backend.llm.granite_client import MockLLM
from backend.models import ReasonCode
from backend.services.invoice_service import InvoiceService
from backend.services.masking_service import mask_text


def supplier_invoice() -> bytes:
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=10)
    for line in (
        "Page 1 of 1",
        "Northwind Racket Supply North America",
        "#140-1000 Example Place",
        "Richmond BC  V6V 0A0",
        "+16045550100",
        "accounting@example-rackets.test",
        "INVOICE",
        "BILL TO",
        "Example University Badminton Team",
        "INVOICE SPN-2026-0169",
        "DATE 14/10/2026",
        "TERMS 0",
        "DUE DATE 14/10/2026",
        "DATE DESCRIPTION TAX QTY RATE AMOUNT",
        "Team shirt size M  Zero-rated 26 12.00 312.00",
        "SUBTOTAL 588.00",
        "SHIPPING 30.00",
        "TOTAL 618.00",
        "BALANCE DUE USD 618.00",
    ):
        pdf.cell(0, 6, line, new_x="LMARGIN", new_y="NEXT")
    return bytes(pdf.output())


class GraniteLike(MockLLM):
    """Answers the field-extraction prompt the way Granite did on the real invoice."""

    def complete(self, prompt):
        if "<schema>invoice_fields</schema>" in prompt:
            return json.dumps(
                {
                    "vendor_invoice_number": "INVOICE SPN-2026-0169",
                    "vendor_name": "Northwind Racket Supply North America",
                    "vendor_id": None,
                    "amount": "618.00",
                    "currency": "USD",
                    "due_date": "14/10/2026",
                    "purchase_order_id": None,
                }
            )
        return super().complete(prompt)


# --- the three bugs, one by one ----------------------------------------------------------


@pytest.mark.parametrize(
    "raw,iso",
    [
        ("14/10/2026", "2026-10-14"),  # first number can't be a month → day-first
        ("31/12/2026", "2026-12-31"),
        ("05/06/2026", "2026-05-06"),  # ambiguous → stays US month-first
        ("12/25/2026", "2026-12-25"),
        ("31/02/2026", None),  # not a real date
    ],
)
def test_unambiguous_day_first_dates_are_read(raw, iso):
    assert normalize_date(raw) == iso


def test_international_phone_number_is_not_a_bank_account():
    masked, detections = mask_text("Call +16045550100 or pay account 987654326789")
    assert "+16045550100" in masked
    assert "987654326789" not in masked and "****6789" in masked
    assert len(detections) == 1


@pytest.mark.parametrize(
    "raw,clean",
    [
        ("INVOICE SPN-2026-0169", "SPN-2026-0169"),
        ("Invoice No.: 1042", "1042"),
        ("Inv # A-77", "A-77"),
        ("INV-1042", "INV-1042"),
        ("SPN-2026-0169", "SPN-2026-0169"),
    ],
)
def test_invoice_label_word_is_stripped(raw, clean):
    assert normalize("vendor_invoice_number", raw) == clean


# --- end to end ------------------------------------------------------------------------------


class OneEmail:
    def list_candidates(self, days):
        return ["m-real"]

    def fetch(self, message_id):
        return InboxMessage(
            message_id, "t", "a@b.test", "Invoice", None, "invoice.pdf", supplier_invoice()
        )


def test_real_layout_is_a_review_not_a_block(session, ref):
    gov = GovernanceEngine(session, ref)
    res = InboxService(session, gov, OneEmail(), llm=GraniteLike()).sync()
    svc = InvoiceService(session, gov)
    inv = svc.get(res.created[0])

    assert inv.vendor_invoice_number == "SPN-2026-0169"
    assert str(inv.due_date) == "2026-10-14"
    assert inv.amount == 618.0 and inv.currency.value == "USD"
    assert inv.sensitive_data_detected is False  # the phone number is not banking data

    policy = next(d for d in svc.decisions(inv.invoice_id) if d.agent.value == "policy_risk_agent")
    assert set(policy.reason_codes) == {
        ReasonCode.UNKNOWN_VENDOR,
        ReasonCode.MISSING_REQUIRED_FIELD,
    }
    assert inv.risk_level.value == "medium" and inv.status.value == "PENDING_APPROVAL"
    assert gov.payments.get_payment(inv.invoice_id) is None  # still a human's call
