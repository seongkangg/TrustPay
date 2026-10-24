"""Generic input validators used by the intake step and the API layer.

They return findings rather than raising, so the caller can turn them into
MISSING_REQUIRED_FIELD / MALFORMED_FIELD reason codes.
"""

import re
from datetime import date
from typing import Any

from backend.models.enums import Currency

REQUIRED_INVOICE_FIELDS = (
    "vendor_invoice_number",
    "vendor",  # satisfied by vendor_id OR vendor_name
    "amount",
    "currency",
    "due_date",
    "purchase_order_id",
)

ID_PATTERNS = {
    "invoice_id": re.compile(r"^INV-\d{4,}$"),
    "vendor_id": re.compile(r"^V-\d{3,}$"),
    "purchase_order_id": re.compile(r"^PO-\d{4,}$"),
}


def missing_fields(data: dict[str, Any]) -> list[str]:
    missing = []
    for field in REQUIRED_INVOICE_FIELDS:
        if field == "vendor":
            if not data.get("vendor_id") and not data.get("vendor_name"):
                missing.append("vendor_id/vendor_name")
        elif data.get(field) in (None, ""):
            missing.append(field)
    return missing


def malformed_fields(data: dict[str, Any]) -> list[str]:
    bad = []
    for field, pattern in ID_PATTERNS.items():
        value = data.get(field)
        if value and not pattern.match(str(value)):
            bad.append(field)

    amount = data.get("amount")
    if amount is not None:
        try:
            if float(amount) <= 0:
                bad.append("amount")
        except (TypeError, ValueError):
            bad.append("amount")

    currency = data.get("currency")
    if currency is not None and currency not in {c.value for c in Currency}:
        bad.append("currency")

    due = data.get("due_date")
    if due is not None and not isinstance(due, date):
        try:
            date.fromisoformat(str(due))
        except ValueError:
            bad.append("due_date")

    return bad
