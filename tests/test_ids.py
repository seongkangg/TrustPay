"""IDs are numbered from the highest existing one, so deleting rows never causes a collision.

Regression: with "row count + 1", deleting two invoices' rows made the next audit event reuse
EVT-043, which a surviving row still held — the whole invoice failed on a primary-key error.
"""

from sqlalchemy import delete

from backend.database.ids import next_id
from backend.database.tables import AuditEventRow, InvoiceRow
from backend.models import AgentName, EventType, InvoiceUpload, Severity
from backend.services.audit_service import AuditService
from backend.services.invoice_service import InvoiceService


def _append(audit, invoice_id):
    return audit.append(
        invoice_id=invoice_id,
        correlation_id="c",
        event_type=EventType.INVOICE_RECEIVED,
        severity=Severity.LOW,
        actor=AgentName.SYSTEM,
    )


def test_next_id_starts_and_counts_past_the_highest(session):
    assert next_id(session, AuditEventRow.event_id, "EVT") == "EVT-001"
    audit = AuditService(session)
    for i in range(3):
        _append(audit, f"INV-{9000 + i}")
    assert next_id(session, AuditEventRow.event_id, "EVT") == "EVT-004"


def test_deleting_rows_in_the_middle_never_reissues_an_id(session):
    audit = AuditService(session)
    ids = [_append(audit, f"INV-{9000 + i}").event_id for i in range(5)]  # EVT-001..005
    session.execute(delete(AuditEventRow).where(AuditEventRow.event_id.in_(ids[1:3])))
    session.commit()
    new = _append(audit, "INV-9100").event_id
    assert new == "EVT-006" and new not in ids  # count+1 would have given EVT-004, a duplicate


def test_ids_order_numerically_across_widths(session):
    audit = AuditService(session)
    session.add_all(
        [
            AuditEventRow(**{**_row(), "event_id": "EVT-999"}),
            AuditEventRow(**{**_row(), "event_id": "EVT-1000", "sequence": 2}),
        ]
    )
    session.commit()
    assert _append(audit, "INV-9001").event_id == "EVT-1001"


def _row():
    from backend.utils.timestamps import now_utc

    return dict(
        invoice_id="INV-9000",
        correlation_id="c",
        sequence=1,
        event_type="invoice_received",
        severity="low",
        actor="system",
        reason_codes=[],
        evidence_refs=[],
        event_hash="x",
        out_of_order=False,
        timestamp=now_utc(),
    )


def test_invoice_ids_skip_seeded_history_and_survive_deletes(session, ref, fixture_by_id):
    from backend.governance import GovernanceEngine

    svc = InvoiceService(session, GovernanceEngine(session, ref))
    # seeded history lives below the live range
    session.add(
        InvoiceRow(
            invoice_id="INV-0007",
            correlation_id="h",
            vendor_invoice_number="HIST-0007",
            status="COMPLETED",
            created_at=_row()["timestamp"],
            updated_at=_row()["timestamp"],
        )
    )
    session.commit()
    up = InvoiceUpload(**fixture_by_id("INV-1001")["upload"])
    first = svc.create(up).invoice_id
    second = svc.create(up).invoice_id
    assert (first, second) == ("INV-1001", "INV-1002")
    session.execute(delete(InvoiceRow).where(InvoiceRow.invoice_id == "INV-1001"))
    session.commit()
    assert svc.create(up).invoice_id == "INV-1003"
