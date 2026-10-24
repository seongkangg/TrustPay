"""Gmail intake: watch a mailbox for `invoice.pdf` attachments and feed them into the workflow.

Read-only Gmail scope. PDF bytes live only in memory for the duration of one sync; what is
stored is the parsed upload after `GovernanceEngine.ingest()` has masked it.
"""

from dataclasses import dataclass
from datetime import datetime

INVOICE_FILENAME = "invoice.pdf"  # matched case-insensitively


class InboxError(RuntimeError):
    """Gmail could not be reached, authorized, or read."""


@dataclass
class InboxMessage:
    message_id: str
    thread_id: str | None
    sender: str | None
    subject: str | None
    received_at: datetime | None
    attachment_name: str
    pdf_bytes: bytes


def is_invoice_attachment(filename: str | None) -> bool:
    return bool(filename) and filename.strip().lower() == INVOICE_FILENAME
