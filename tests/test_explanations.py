"""Detailed reviewer explanations (approval page "Why" + "What to do"): built from recorded
evidence, one plain-English reason per flag, a concrete next step, never raw sensitive data."""

from backend.governance import GovernanceEngine
from backend.inbox.inbox_service import InboxService
from backend.models import AgentName
from backend.services.invoice_service import InvoiceService
from tests.conftest import insert_invoice_row, run_agents
from tests.test_real_invoice_layout import GraniteLike, OneEmail


def _why(ctx):
    return next(d for d in ctx.decisions if d.agent == AgentName.APPROVAL).explanation


def test_clean_invoice_says_what_checked_out(session, ref, fixture_by_id):
    why = _why(run_agents(GovernanceEngine(session, ref), fixture_by_id("INV-1001")))
    assert len(why.reasons) == 1 and why.reasons[0].startswith("Everything checks out")
    assert "PO-5001" in why.reasons[0] and "USD 4,250.00" in why.reasons[0]
    assert why.recommended_next_step.startswith("Nothing to do")


def test_suspicious_invoice_explains_every_flag(session, ref, fixture_by_id):
    why = _why(run_agents(GovernanceEngine(session, ref), fixture_by_id("INV-1003")))
    text = " ".join(why.reasons)
    for lead in (
        "Above the AI's limit",
        "New vendor",
        "Purchase order not found",
        "Banking or tax details",
    ):
        assert lead in text, lead
    assert "PO-7781" in text and "****6789" in text and "987654326789" not in text
    assert "USD 10,000.00" in text  # the limit, from approval_limits.json
    assert why.recommended_next_step.startswith("1. ") and "4. " in why.recommended_next_step
    assert not any(r.isupper() for r in why.reasons)  # no bare reason codes


def test_duplicate_names_the_original(session, ref, fixture_by_id):
    insert_invoice_row(session, fixture_by_id("INV-1001"))
    why = _why(run_agents(GovernanceEngine(session, ref), fixture_by_id("INV-1004")))
    assert why.reasons[0].startswith("Possible duplicate") and "INV-1001" in why.reasons[0]
    assert "the same invoice number (ACME-2026-0917)" in why.reasons[0]
    assert "INV-1001" in why.recommended_next_step


def test_new_vendor_without_po_explains_why_a_po_matters(session, ref):
    gov = GovernanceEngine(session, ref)
    created = InboxService(session, gov, OneEmail(), llm=GraniteLike()).sync().created[0]
    svc = InvoiceService(session, gov)
    why = next(d for d in svc.decisions(created) if d.agent == AgentName.APPROVAL).explanation
    text = " ".join(why.reasons)
    assert "'Northwind Racket Supply North America' is not on the approved vendor list" in text
    assert "purchase order (PO) number" in text and "approved this purchase" in text
    assert why.missing_information == ["purchase order (PO) number"]
    assert "Get the missing purchase order (PO) number" in why.recommended_next_step
