"""PDF → text → InvoiceUpload-shaped dict.

Deterministic: a regex over labelled lines (`Label: value`). Fields that are not found stay
None and the Intake agent flags them as MISSING_REQUIRED_FIELD — that is the correct
governance outcome for a document we could not read, so there is no LLM guessing here.
`scripts/make_invoice_pdfs.py` renders the demo PDFs with exactly these labels.
"""

import io
import re
from typing import Any

from pypdf import PdfReader

# field → accepted labels (first label is the canonical one the generator writes)
LABELS: list[tuple[str, tuple[str, ...]]] = [
    ("vendor_invoice_number", ("Invoice Number", "Invoice No", "Invoice #")),
    ("vendor_id", ("Vendor ID",)),
    ("vendor_name", ("Vendor", "Bill From", "Supplier")),
    ("amount", ("Amount Due", "Total Due", "Total", "Amount")),
    ("currency", ("Currency",)),
    ("due_date", ("Due Date", "Payment Due")),
    ("purchase_order_id", ("Purchase Order", "PO Number", "PO")),
    ("bank_account", ("Bank Account", "Account Number")),
    ("routing_number", ("Routing Number", "Routing", "ABA")),
    ("tax_id", ("Tax ID", "EIN")),
]

_PATTERNS = [
    (
        field,
        re.compile(
            r"^\s*(?:" + "|".join(re.escape(label) for label in labels) + r")\s*[:#]\s*(.+?)\s*$",
            re.I,
        ),
    )
    for field, labels in LABELS
]


class PdfParseError(ValueError):
    """The bytes are not a readable PDF."""


def extract_text(pdf_bytes: bytes) -> str:
    try:
        reader = PdfReader(io.BytesIO(pdf_bytes))
        return "\n".join((page.extract_text() or "") for page in reader.pages)
    except Exception as exc:  # noqa: BLE001 — pypdf raises a zoo of error types
        raise PdfParseError(f"could not read PDF: {exc}") from exc


def _number(raw: str) -> float | None:
    cleaned = re.sub(r"[^\d.\-]", "", raw.replace(",", ""))
    try:
        return float(cleaned) if cleaned else None
    except ValueError:
        return None


def upload_from_text(text: str, source_document: str) -> dict[str, Any]:
    """Build the dict `InvoiceUpload(**...)` accepts. Unfound fields are None."""
    found: dict[str, str] = {}
    for line in text.splitlines():
        for field, pattern in _PATTERNS:
            if field in found:
                continue
            m = pattern.match(line)
            if m:
                found[field] = m.group(1).strip()
                break

    upload: dict[str, Any] = {field: found.get(field) for field, _ in LABELS}
    upload["amount"] = _number(found["amount"]) if "amount" in found else None
    if upload.get("currency"):
        upload["currency"] = upload["currency"].upper()[:3]
    for key in ("vendor_id", "purchase_order_id"):
        if upload.get(key):
            upload[key] = upload[key].upper()
    upload["source_document"] = source_document
    upload["raw_text"] = text
    return upload
