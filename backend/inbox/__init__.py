"""Gmail intake: watch a mailbox for PDF attachments named like an invoice and feed them into the
workflow.

Read-only Gmail scope. PDF bytes live only in memory for the duration of one sync; what is
stored is the parsed upload after `GovernanceEngine.ingest()` has masked it.
"""

from dataclasses import dataclass
from datetime import datetime

INVOICE_WORD = "invoice"  # a PDF whose file name contains this (any case) is an invoice


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
    """`invoice.pdf`, `Invoice_1042.PDF`, `ACME invoice Oct.pdf` … — any PDF named with "invoice"."""
    name = (filename or "").strip().lower()
    return name.endswith(".pdf") and INVOICE_WORD in name
