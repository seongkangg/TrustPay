"""Regressions from the governance audit: no auto-pay on unsure or rejected AI decisions,
no pay on expired approvals, and no raw sensitive values in stored free text."""

import copy
import json
from datetime import timedelta

import pytest

from backend.database.tables import AgentDecisionRow, ApprovalRow
from backend.governance import GovernanceEngine
from backend.llm.granite_client import MockLLM
from backend.mock_systems.payment_service import PaymentService
from backend.models import HumanDecisionInput, InvoiceUpload
from backend.services.approval_service import ApprovalService
from backend.services.errors import InvalidStateError
from backend.services.invoice_service import InvoiceService
from backend.services.masking_service import mask_text
from backend.utils.timestamps import now_utc

RAW = ("987654326789", "12-3454321")


class UnsureLLM(MockLLM):
    """Mock LLM whose approval recommendation has low confidence and optional reasons."""

    def __init__(self, reasons=None):
        self.reasons = reasons or []

    def complete(self, prompt, *, temperature=0.0):
        out = json.loads(super().complete(prompt))
        if "recommendation" in out:
            out["confidence"] = 0.10
            out["reasons"] = self.reasons
        return json.dumps(out)


def _process(session, upload, llm):
    gov = GovernanceEngine(session, payment_service=PaymentService())
    svc = InvoiceService(session, gov, llm)
    inv = svc.create(InvoiceUpload(**upload))
    svc.process(inv.invoice_id)
    return gov, svc, svc.get_row(inv.invoice_id)


def test_low_confidence_approve_is_not_auto_paid(session, fixture_by_id):
    _, _, row = _process(session, fixture_by_id("INV-1001")["upload"], UnsureLLM())
    assert row.status == "PENDING_APPROVAL"


def test_rejected_approval_decision_is_not_auto_paid_or_stored_raw(session, fixture_by_id):
    llm = UnsureLLM([f"tax id {RAW[1]}"])
    _, _, row = _process(session, fixture_by_id("INV-1001")["upload"], llm)
    assert row.status == "PENDING_APPROVAL"
    stored = json.dumps([d.explanation for d in session.query(AgentDecisionRow).all()])
    assert RAW[1] not in stored


def test_expired_approval_cannot_be_approved(session, fixture_by_id):
    gov, svc, row = _process(session, fixture_by_id("INV-1002")["upload"], MockLLM())
    for a in session.query(ApprovalRow).all():
        a.expires_at = now_utc() - timedelta(hours=1)
    session.commit()
    with pytest.raises(InvalidStateError):
        ApprovalService(session, gov, svc).approve(row.invoice_id, HumanDecisionInput(reviewer="r"))
    assert svc.get_row(row.invoice_id).status == "PENDING_APPROVAL"


def test_reviewer_note_is_masked(session, fixture_by_id):
    gov, svc, row = _process(session, fixture_by_id("INV-1002")["upload"], MockLLM())
    note = f"EIN {RAW[1]} acct {RAW[0]}"
    _, approval = ApprovalService(session, gov, svc).approve(
        row.invoice_id, HumanDecisionInput(reviewer="r", note=note)
    )
    stored = session.query(ApprovalRow).one().reviewer_note
    assert not any(r in stored or r in approval["reviewer_note"] for r in RAW)


def test_free_text_upload_fields_are_masked(session, fixture_by_id):
    upload = copy.deepcopy(fixture_by_id("INV-1001")["upload"])
    upload["vendor_name"] = f"Acme EIN {RAW[1]}"
    upload["vendor_invoice_number"] = f"ACME-X-{RAW[0]}"
    _, _, row = _process(session, upload, MockLLM())
    assert not any(r in (row.vendor_name or "") + row.vendor_invoice_number for r in RAW)


def test_card_cvv_and_base64_are_redacted_but_hashes_are_not():
    key = "AbCdEfGhIjKlMnOpQrStUvWxYz0123456789abcd=="
    masked, _ = mask_text(f"card 4111111111111111 cvv 123 key {key}")
    assert "4111" not in masked and "123" not in masked and key not in masked
    sha = "3f9a1c0e8b7d6a5f4e3d2c1b0a9f8e7d6c5b4a3f2e1d0c9b8a7f6e5d4c3b2a1f"
    assert mask_text(f"hash {sha}")[0] == f"hash {sha}"
