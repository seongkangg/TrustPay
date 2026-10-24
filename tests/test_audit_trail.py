"""Append-only, hash-chained audit trail (spec §11; acceptance A11 and Part C)."""

from datetime import timedelta

import pytest

from backend.models import AgentName, Authorization, EventType, ReasonCode, Severity
from backend.services.audit_service import AuditService, compute_event_hash, verify_chain
from backend.utils.timestamps import now_utc


@pytest.fixture
def audit(session):
    return AuditService(session)


def _append(audit, invoice_id="INV-1001", event_type=EventType.INVOICE_RECEIVED, **kw):
    return audit.append(
        invoice_id=invoice_id,
        correlation_id="corr-1",
        event_type=event_type,
        severity=kw.pop("severity", Severity.LOW),
        actor=kw.pop("actor", AgentName.SYSTEM),
        **kw,
    )


def test_first_event_has_no_previous_hash_and_sequence_one(audit):
    ev = _append(audit)
    assert ev.event_id == "EVT-001"
    assert ev.sequence == 1
    assert ev.previous_event_hash is None
    assert ev.event_hash == compute_event_hash(ev.model_dump())


def test_events_chain_per_invoice(audit):
    e1 = _append(audit)
    e2 = _append(audit, event_type=EventType.INVOICE_EXTRACTED, actor=AgentName.INTAKE)
    other = _append(audit, invoice_id="INV-1002")
    assert e2.sequence == 2 and e2.previous_event_hash == e1.event_hash
    assert other.sequence == 1 and other.previous_event_hash is None
    assert audit.get_trail("INV-1001").chain_valid
    assert audit.get_trail("INV-1002").chain_valid


def test_duplicate_event_id_is_ignored_idempotently(audit):
    e1 = _append(audit, event_id="EVT-900")
    again = _append(audit, event_id="EVT-900", event_type=EventType.PAYMENT_BLOCKED)
    assert again == e1
    trail = audit.get_trail("INV-1001")
    assert len(trail.events) == 1 and trail.chain_valid


def test_out_of_order_event_is_flagged_not_reordered(audit):
    now = now_utc()
    _append(audit, timestamp=now)
    late = _append(audit, event_type=EventType.RISK_ASSIGNED, timestamp=now - timedelta(minutes=5))
    assert late.out_of_order is True
    assert late.sequence == 2
    trail = audit.get_trail("INV-1001")
    assert [e.event_type for e in trail.events] == [
        EventType.INVOICE_RECEIVED,
        EventType.RISK_ASSIGNED,
    ]
    assert trail.chain_valid


def test_tampering_breaks_chain_verification(audit):
    _append(audit)
    _append(audit, event_type=EventType.RISK_ASSIGNED)
    events = audit.list_for_invoice("INV-1001")
    tampered = events[0].model_copy(update={"actor": AgentName.APPROVAL})
    assert verify_chain([tampered, events[1]]) is False
    assert verify_chain(events) is True


def test_summaries_are_masked_before_storage(audit):
    ev = _append(
        audit,
        event_type=EventType.SENSITIVE_DATA_MASKED,
        severity=Severity.MEDIUM,
        actor=AgentName.GOVERNANCE,
        reason_codes=[ReasonCode.SENSITIVE_DATA_DETECTED],
        policy_result=Authorization.ALLOWED,
        input_summary="remit to account 987654326789",
        evidence_refs=["SCAN-001"],
    )
    assert "987654326789" not in ev.input_summary
    assert "****6789" in ev.input_summary
    assert ev.reason_codes == [ReasonCode.SENSITIVE_DATA_DETECTED]
    assert ev.policy_result == Authorization.ALLOWED
