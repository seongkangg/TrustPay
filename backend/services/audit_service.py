"""Append-only, hash-chained audit trail (docs/architecture.md, spec §11).

Guarantees:
- Events are never updated or deleted.
- Each event stores the hash of the previous event for the same invoice.
- A duplicate `event_id` is ignored idempotently (the stored event is returned unchanged).
- An event whose timestamp precedes the last recorded one is appended and flagged
  `out_of_order=True`; it is never reordered, so the chain stays intact.
- Summaries are masked before storage as a last line of defense.
"""

import hashlib
import json
from collections.abc import Iterable
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.database.tables import AuditEventRow
from backend.models import (
    AgentName,
    AuditEvent,
    AuditTrail,
    Authorization,
    EventType,
    ReasonCode,
    Severity,
)
from backend.services.masking_service import mask_text
from backend.utils.timestamps import now_utc, to_iso

HASHED_FIELDS = (
    "event_id",
    "invoice_id",
    "correlation_id",
    "sequence",
    "event_type",
    "severity",
    "actor",
    "reason_codes",
    "policy_result",
    "input_summary",
    "output_summary",
    "evidence_refs",
    "related_decision_id",
    "related_tool_call_id",
    "previous_event_hash",
    "timestamp",
)


def compute_event_hash(fields: dict) -> str:
    canonical = {k: fields.get(k) for k in HASHED_FIELDS}
    if isinstance(canonical["timestamp"], datetime):
        canonical["timestamp"] = to_iso(canonical["timestamp"])
    payload = json.dumps(canonical, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _as_utc(dt: datetime) -> datetime:
    """SQLite hands back naive datetimes; everything we stored is UTC."""
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


def _to_model(row: AuditEventRow) -> AuditEvent:
    return AuditEvent(
        event_id=row.event_id,
        invoice_id=row.invoice_id,
        correlation_id=row.correlation_id,
        sequence=row.sequence,
        event_type=row.event_type,
        severity=row.severity,
        actor=row.actor,
        reason_codes=row.reason_codes or [],
        policy_result=row.policy_result,
        input_summary=row.input_summary,
        output_summary=row.output_summary,
        evidence_refs=row.evidence_refs or [],
        related_decision_id=row.related_decision_id,
        related_tool_call_id=row.related_tool_call_id,
        previous_event_hash=row.previous_event_hash,
        event_hash=row.event_hash,
        out_of_order=row.out_of_order,
        timestamp=_as_utc(row.timestamp),
    )


class AuditService:
    def __init__(self, session: Session):
        self.session = session

    # -- write -------------------------------------------------------------

    def append(
        self,
        *,
        invoice_id: str,
        correlation_id: str,
        event_type: EventType,
        severity: Severity,
        actor: AgentName,
        reason_codes: Iterable[ReasonCode] = (),
        policy_result: Authorization | None = None,
        input_summary: str | None = None,
        output_summary: str | None = None,
        evidence_refs: Iterable[str] = (),
        related_decision_id: str | None = None,
        related_tool_call_id: str | None = None,
        timestamp: datetime | None = None,
        event_id: str | None = None,
    ) -> AuditEvent:
        if event_id:
            existing = self.session.get(AuditEventRow, event_id)
            if existing:
                return _to_model(existing)  # duplicate: idempotent, chain unchanged
        else:
            event_id = self._next_event_id()

        last = self._last_for_invoice(invoice_id)
        ts = timestamp or now_utc()
        out_of_order = bool(last and ts < _as_utc(last.timestamp))

        fields = {
            "event_id": event_id,
            "invoice_id": invoice_id,
            "correlation_id": correlation_id,
            "sequence": (last.sequence + 1) if last else 1,
            "event_type": EventType(event_type).value,
            "severity": Severity(severity).value,
            "actor": AgentName(actor).value,
            "reason_codes": [ReasonCode(r).value for r in reason_codes],
            "policy_result": Authorization(policy_result).value if policy_result else None,
            "input_summary": mask_text(input_summary)[0],
            "output_summary": mask_text(output_summary)[0],
            "evidence_refs": list(evidence_refs),
            "related_decision_id": related_decision_id,
            "related_tool_call_id": related_tool_call_id,
            "previous_event_hash": last.event_hash if last else None,
            "timestamp": ts,
        }
        row = AuditEventRow(
            **fields, event_hash=compute_event_hash(fields), out_of_order=out_of_order
        )
        self.session.add(row)
        self.session.commit()
        return _to_model(row)

    # -- read --------------------------------------------------------------

    def list_for_invoice(self, invoice_id: str) -> list[AuditEvent]:
        stmt = (
            select(AuditEventRow)
            .where(AuditEventRow.invoice_id == invoice_id)
            .order_by(AuditEventRow.sequence)
        )
        return [_to_model(r) for r in self.session.scalars(stmt)]

    def get_trail(self, invoice_id: str) -> AuditTrail:
        events = self.list_for_invoice(invoice_id)
        return AuditTrail(invoice_id=invoice_id, events=events, chain_valid=verify_chain(events))

    def count(self) -> int:
        return self.session.scalar(select(func.count()).select_from(AuditEventRow)) or 0

    # -- internals ---------------------------------------------------------

    def _next_event_id(self) -> str:
        return f"EVT-{self.count() + 1:03d}"

    def _last_for_invoice(self, invoice_id: str) -> AuditEventRow | None:
        stmt = (
            select(AuditEventRow)
            .where(AuditEventRow.invoice_id == invoice_id)
            .order_by(AuditEventRow.sequence.desc())
            .limit(1)
        )
        return self.session.scalars(stmt).first()


def verify_chain(events: list[AuditEvent]) -> bool:
    """True when every hash recomputes and every previous_event_hash links correctly."""
    prev_hash: str | None = None
    for expected_seq, ev in enumerate(events, start=1):
        if ev.sequence != expected_seq or ev.previous_event_hash != prev_hash:
            return False
        if compute_event_hash(ev.model_dump()) != ev.event_hash:
            return False
        prev_hash = ev.event_hash
    return True
