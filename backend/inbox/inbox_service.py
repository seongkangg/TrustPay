"""One sync pass: new Gmail messages with invoice.pdf → parse → create → process.

Every message looked at gets an `inbox_messages` row (processed / skipped / failed) so it is
never fetched twice. A failure on one message never stops the batch and never raises out of
`sync()`; only a failure to reach Gmail at all does (InboxError).
"""

import logging
import threading
from dataclasses import dataclass, field
from typing import Any

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database.tables import InboxMessageRow
from backend.governance import GovernanceEngine
from backend.inbox import InboxError, InboxMessage
from backend.inbox.gmail_client import GmailClient
from backend.inbox.llm_extraction import extract_missing_fields
from backend.inbox.pdf_parser import PdfParseError, extract_text, upload_from_text
from backend.llm.granite_client import LLMClient, MockLLM
from backend.models import InvoiceUpload
from backend.services.invoice_service import InvoiceService
from backend.utils.timestamps import now_utc

log = logging.getLogger(__name__)

_SYNC_LOCK = threading.Lock()


def sanitize_upload(upload: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """Null out any field InvoiceUpload rejects (bad ID format, negative amount, …).

    An emailed invoice with one unreadable field must still become an invoice — escalated
    for the missing field — rather than be dropped. `vendor_invoice_number` is always set by
    the caller, so it is never the field being dropped.
    """
    clean = dict(upload)
    dropped: dict[str, Any] = {}
    for _ in range(len(clean) + 1):
        try:
            InvoiceUpload(**clean)
            return clean, dropped
        except ValidationError as exc:
            bad = {err["loc"][0] for err in exc.errors() if err["loc"]}
            bad.discard("vendor_invoice_number")
            if not bad:
                raise
            for name in bad:
                dropped[name] = clean.get(name)
                clean[name] = None
    raise ValueError("upload could not be sanitized")


@dataclass
class SyncResult:
    checked: int = 0
    created: list[str] = field(default_factory=list)
    skipped: int = 0
    failed: list[tuple[str, str]] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "checked": self.checked,
            "created": list(self.created),
            "skipped": self.skipped,
            "failed": [list(f) for f in self.failed],
        }


class InboxService:
    def __init__(
        self,
        session: Session,
        gov: GovernanceEngine,
        client: GmailClient,
        llm: LLMClient | None = None,
        lookback_days: int = 30,
    ):
        self.session = session
        self.gov = gov
        self.client = client
        self.llm = llm or MockLLM()
        self.invoices = InvoiceService(session, gov, llm)
        self.lookback_days = lookback_days

    def sync(self) -> SyncResult:
        # One sync at a time per process: the background poll and a "Check inbox now" click
        # must not both pick up the same email while the first is still being processed
        # (that duplicated the invoice and collided on IDs). The second caller waits, then
        # sees the email already recorded and skips it.
        with _SYNC_LOCK:
            self.session.expire_all()  # read what the previous sync committed, not a stale cache
            return self._sync()

    def _sync(self) -> SyncResult:
        result = SyncResult()
        ids = self.client.list_candidates(self.lookback_days)  # InboxError propagates
        if not ids:
            return result
        known = set(
            self.session.scalars(
                select(InboxMessageRow.message_id).where(InboxMessageRow.message_id.in_(ids))
            )
        )
        for message_id in ids:
            if message_id in known:
                result.skipped += 1
                continue
            result.checked += 1
            self._handle(message_id, result)
        return result

    # ------------------------------------------------------------------

    def _handle(self, message_id: str, result: SyncResult) -> None:
        try:
            msg = self.client.fetch(message_id)
        except InboxError as exc:
            self._record(message_id, None, "failed", error=str(exc))
            result.failed.append((message_id, str(exc)))
            return
        if msg is None:
            self._record(message_id, None, "skipped")
            result.skipped += 1
            return
        try:
            invoice_id = self._ingest(msg)
        except Exception as exc:  # noqa: BLE001 — one bad email must not stop the batch
            log.warning("inbox: message %s failed: %s", message_id, exc)
            self.session.rollback()
            self._record(message_id, msg, "failed", error=f"{type(exc).__name__}: {exc}"[:300])
            result.failed.append((message_id, str(exc)))
            return
        self._record(message_id, msg, "processed", invoice_id=invoice_id)
        result.created.append(invoice_id)

    def _ingest(self, msg: InboxMessage) -> str:
        try:
            text = extract_text(msg.pdf_bytes)
        except PdfParseError as exc:
            raise ValueError(str(exc)) from exc
        source = f"{msg.attachment_name} (email from {msg.sender or 'unknown sender'})"
        upload = upload_from_text(text, source)

        # Fields the labels didn't give us: ask the model, keep only what is in the document.
        model = extract_missing_fields(self.llm, text, upload)
        upload.update(model.filled)

        if not upload.get("vendor_invoice_number"):
            # Required column; the Intake agent still flags the missing field.
            upload["vendor_invoice_number"] = f"EMAIL-{msg.message_id[:8]}"
        if not upload.get("currency"):
            upload["currency"] = "USD"
        upload, dropped = sanitize_upload(upload)
        if dropped:
            log.info(
                "inbox: %s fields failed validation and were left empty: %s",
                msg.message_id,
                sorted(dropped),
            )
        created = self.invoices.create(InvoiceUpload(**upload))
        self.invoices.process(created.invoice_id)
        return created.invoice_id

    def _record(
        self,
        message_id: str,
        msg: InboxMessage | None,
        status: str,
        *,
        invoice_id: str | None = None,
        error: str | None = None,
    ) -> None:
        self.session.add(
            InboxMessageRow(
                message_id=message_id,
                thread_id=msg.thread_id if msg else None,
                sender=msg.sender if msg else None,
                subject=msg.subject if msg else None,
                received_at=msg.received_at if msg else None,
                attachment_name=msg.attachment_name if msg else None,
                invoice_id=invoice_id,
                status=status,
                error=error,
                synced_at=now_utc(),
            )
        )
        self.session.commit()


def recent_messages(session: Session, limit: int = 10) -> list[dict[str, Any]]:
    """Newest inbox rows for the dashboard's inbox card."""
    stmt = select(InboxMessageRow).order_by(InboxMessageRow.synced_at.desc()).limit(limit)
    return [
        {
            "message_id": r.message_id,
            "sender": r.sender,
            "subject": r.subject,
            "received_at": r.received_at,
            "attachment_name": r.attachment_name,
            "invoice_id": r.invoice_id,
            "status": r.status,
            "error": r.error,
            "synced_at": r.synced_at,
        }
        for r in session.scalars(stmt)
    ]
