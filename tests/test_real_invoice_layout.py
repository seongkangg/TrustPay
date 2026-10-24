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

VENDOR = "Northwind Racket Supply North America"


def supplier_invoice(vendor: str = VENDOR) -> bytes:
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=10)
    for line in (
        "Page 1 of 1",
        vendor,
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

    def complete(self, prompt, *, temperature=0.0):
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


# --- duplicates from a vendor that isn't on the vendor list -----------------------------------


class Inbox:
    def __init__(self, pdfs: dict[str, bytes]):
        self.pdfs = pdfs

    def list_candidates(self, days):
        return list(self.pdfs)

    def fetch(self, message_id):
        return InboxMessage(
            message_id, "t", "a@b.test", "Invoice", None, "invoice.pdf", self.pdfs[message_id]
        )


def _policy_codes(svc, invoice_id):
    return next(
        d for d in svc.decisions(invoice_id) if d.agent.value == "policy_risk_agent"
    ).reason_codes


def test_same_invoice_emailed_twice_by_a_new_vendor_is_a_duplicate(session, ref):
    """No vendor ID (not on the list) used to skip the duplicate check entirely."""
    gov = GovernanceEngine(session, ref)
    pdf = supplier_invoice()
    res = InboxService(session, gov, Inbox({"m-1": pdf, "m-2": pdf}), llm=GraniteLike()).sync()
    first, second = res.created
    svc = InvoiceService(session, gov)

    assert ReasonCode.DUPLICATE_INVOICE not in _policy_codes(svc, first)
    codes = _policy_codes(svc, second)
    assert ReasonCode.DUPLICATE_INVOICE in codes and ReasonCode.UNKNOWN_VENDOR in codes
    dup = svc.get(second)
    assert dup.status.value == "BLOCKED" and dup.recommendation.value == "reject"
    events = [e.event_type.value for e in gov.audit.list_for_invoice(second)]
    assert "duplicate_detected" in events
    assert gov.payments.get_payment(second) is None


class NamedLike(GraniteLike):
    """Same invoice number, but the model reads a different vendor name."""

    def __init__(self, vendor_name):
        self.vendor_name = vendor_name

    def complete(self, prompt, *, temperature=0.0):
        out = super().complete(prompt)
        if "<schema>invoice_fields</schema>" in prompt:
            data = json.loads(out)
            data["vendor_name"] = self.vendor_name
            return json.dumps(data)
        return out


def test_name_variants_of_the_same_vendor_still_match(session, ref):
    gov = GovernanceEngine(session, ref)
    pdf = supplier_invoice()
    svc = InvoiceService(session, gov)
    first = InboxService(session, gov, Inbox({"m-1": pdf}), llm=GraniteLike()).sync().created[0]
    # same company, written with different case, punctuation and a legal suffix
    variant = "NORTHWIND RACKET SUPPLY NORTH AMERICA, INC."
    pdf2 = supplier_invoice(vendor=variant)
    second = (
        InboxService(session, gov, Inbox({"m-2": pdf2}), llm=NamedLike(variant)).sync().created[0]
    )
    assert first != second and svc.get(second).vendor_name == variant
    assert ReasonCode.DUPLICATE_INVOICE in _policy_codes(svc, second)


def test_different_new_vendor_with_the_same_number_is_not_a_duplicate(session, ref):
    """Invoice numbers are only unique per vendor — never flag across vendors."""
    gov = GovernanceEngine(session, ref)
    pdf = supplier_invoice()
    svc = InvoiceService(session, gov)
    InboxService(session, gov, Inbox({"m-1": pdf}), llm=GraniteLike()).sync()
    other = "Example Sports Distribution"
    pdf2 = supplier_invoice(vendor=other)
    second = (
        InboxService(session, gov, Inbox({"m-2": pdf2}), llm=NamedLike(other)).sync().created[0]
    )
    assert svc.get(second).vendor_name == other  # the name was really read from the PDF
    assert ReasonCode.DUPLICATE_INVOICE not in _policy_codes(svc, second)


# --- confidence by step (the mobile ConfidenceChart bars) -------------------------------------


def _confidences(svc, invoice_id):
    return {d.agent.value: d.confidence for d in svc.decisions(invoice_id)}


def test_fully_matched_invoice_scores_high_everywhere(session, ref, fixture_by_id):
    from tests.conftest import run_agents

    gov = GovernanceEngine(session, ref)
    ctx = run_agents(gov, fixture_by_id("INV-1001"))
    conf = {d.agent.value: d.confidence for d in ctx.decisions}
    assert conf == {
        "intake_agent": 0.98,  # exact fields
        "verification_agent": 1.0,  # vendor verified, PO matches, not a duplicate
        "policy_risk_agent": 1.0,
        "approval_agent": 1.0,  # the model gave the final answer in all 5 samples
    }


def test_new_vendor_without_po_shows_what_was_and_wasnt_confirmed(session, ref):
    gov = GovernanceEngine(session, ref)
    res = InboxService(session, gov, OneEmail(), llm=GraniteLike()).sync()
    svc = InvoiceService(session, gov)
    conf = _confidences(svc, res.created[0])
    assert conf["intake_agent"] == 0.8  # fields read by the model, all found in the PDF
    assert conf["verification_agent"] == 0.33  # only "not a duplicate" confirmed
    # the recommendation's confidence is the model's agreement, not the evidence: 5 of 5 here
    assert conf["approval_agent"] == 1.0
    assert svc.get(res.created[0]).recommendation_confidence == 1.0
    # a low Verification score is not "Unclear details": vendor / PO have their own flags
    policy = next(d for d in svc.decisions(res.created[0]) if d.agent.value == "policy_risk_agent")
    assert ReasonCode.LOW_CONFIDENCE not in policy.reason_codes


def test_unreadable_invoice_number_means_unclear_details(session, ref):
    class NoNumber(GraniteLike):
        def complete(self, prompt, *, temperature=0.0):
            out = super().complete(prompt)
            if "<schema>invoice_fields</schema>" in prompt:
                data = json.loads(out)
                data["vendor_invoice_number"] = None
                return json.dumps(data)
            return out

    gov = GovernanceEngine(session, ref)
    res = InboxService(session, gov, OneEmail(), llm=NoNumber()).sync()
    svc = InvoiceService(session, gov)
    inv = svc.get(res.created[0])
    assert inv.vendor_invoice_number.startswith("EMAIL-")  # placeholder
    assert _confidences(svc, inv.invoice_id)["intake_agent"] == 0.0
    policy = next(d for d in svc.decisions(inv.invoice_id) if d.agent.value == "policy_risk_agent")
    assert ReasonCode.LOW_CONFIDENCE in policy.reason_codes


def test_assumed_currency_lowers_reading_confidence(session, ref):
    class NoCurrency(GraniteLike):
        def complete(self, prompt, *, temperature=0.0):
            out = super().complete(prompt)
            if "<schema>invoice_fields</schema>" in prompt:
                data = json.loads(out)
                data["currency"] = None
                return json.dumps(data)
            return out

    pdf = supplier_invoice().replace(b"USD", b"   ")  # no currency anywhere in the text

    class NoCurrencyEmail(OneEmail):
        def fetch(self, message_id):
            return InboxMessage(message_id, "t", "a@b.test", "Invoice", None, "invoice.pdf", pdf)

    gov = GovernanceEngine(session, ref)
    res = InboxService(session, gov, NoCurrencyEmail(), llm=NoCurrency()).sync()
    svc = InvoiceService(session, gov)
    inv = svc.get(res.created[0])
    assert inv.currency.value == "USD"  # assumed
    fields = {f.field: f.confidence for f in inv.extraction}
    assert fields["currency"] == 0.5
    assert _confidences(svc, inv.invoice_id)["intake_agent"] == 0.5
