"""Masking rules for sensitive data (docs/policy-matrix.md → Sensitive-data handling).

Two entry points:
- `mask_field(name, value)` for structured invoice fields (bank_account, routing_number, tax_id)
- `mask_text(text)` for free text (raw invoice text, explanations, log messages)

Both return masked output plus a list of `Detection`s so the caller can emit
`sensitive_data_masked` events and `SCAN-NNN` evidence IDs. The raw value is never returned.
"""

import re
from dataclasses import dataclass

from backend.models.enums import SensitiveFieldType

MASK_PREFIX = "****"
REDACTED = "[REDACTED]"

# Structured fields that are always masked to their last four digits.
LAST4_FIELDS: dict[str, SensitiveFieldType] = {
    "bank_account": SensitiveFieldType.BANK_ACCOUNT,
    "routing_number": SensitiveFieldType.ROUTING_NUMBER,
    "tax_id": SensitiveFieldType.TAX_ID,
}


@dataclass(frozen=True)
class Detection:
    field_type: SensitiveFieldType
    masked_value: str
    source: str  # field name, or "text"


def mask_last4(value: str) -> str:
    """`987654326789` → `****6789`, `12-3454321` → `****4321`."""
    digits = re.sub(r"\D", "", str(value))
    return MASK_PREFIX + digits[-4:] if len(digits) >= 4 else MASK_PREFIX


def is_masked(value: str | None) -> bool:
    return value is None or (value.startswith(MASK_PREFIX) and len(value) == 8)


def mask_field(name: str, value: str | None) -> tuple[str | None, Detection | None]:
    """Mask a structured field. Already-masked values pass through without a detection."""
    if value is None or name not in LAST4_FIELDS:
        return value, None
    if is_masked(value):
        return value, None
    masked = mask_last4(value)
    return masked, Detection(LAST4_FIELDS[name], masked, name)


# Free-text patterns, applied in order. Earlier patterns win on overlap.
_TEXT_RULES: list[tuple[SensitiveFieldType, re.Pattern[str], str]] = [
    # "Bearer abc..." / "sk-..." / "api_key=..." → fully redacted
    (
        SensitiveFieldType.API_KEY,
        re.compile(r"(?i)\b(?:bearer\s+|sk-|api[_-]?key[=:\s]+|token[=:\s]+)[A-Za-z0-9._-]{16,}"),
        "redact",
    ),
    # Long base64 secret: 32+ chars mixing upper, lower and digits (lowercase hex hashes don't match)
    (
        SensitiveFieldType.API_KEY,
        re.compile(
            r"(?<![A-Za-z0-9+/])(?=[A-Za-z0-9+/]{0,200}[A-Z])(?=[A-Za-z0-9+/]{0,200}[a-z])"
            r"(?=[A-Za-z0-9+/]{0,200}\d)[A-Za-z0-9+/]{32,}={0,2}"
        ),
        "redact",
    ),
    # Card number: 4 groups of 4 digits, or 15–16 contiguous digits → fully redacted
    (
        SensitiveFieldType.PAYMENT_CREDENTIAL,
        re.compile(r"\b(?:\d{4}[ -]){3}\d{4}\b|\b\d{15,16}\b"),
        "redact",
    ),
    # Card security code after "CVV" / "CVC" / "security code" → fully redacted
    (
        SensitiveFieldType.PAYMENT_CREDENTIAL,
        re.compile(r"(?i)\b(?:cvv2?|cvc2?|security code)\D{0,5}(\d{3,4})\b"),
        "redact",
    ),
    # Routing number: 9 digits preceded by the word "routing" (or ABA)
    (
        SensitiveFieldType.ROUTING_NUMBER,
        re.compile(r"(?i)(?:(?<=routing)|(?<=aba))\D{0,12}(\d{9})\b"),
        "last4",
    ),
    # Tax ID: EIN NN-NNNNNNN or SSN NNN-NN-NNNN
    (
        SensitiveFieldType.TAX_ID,
        re.compile(r"\b\d{2}-\d{7}\b|\b\d{3}-\d{2}-\d{4}\b"),
        "last4",
    ),
    # Bank account: 8–17 digit run (amounts and IDs in this system are shorter). A run written
    # right after "+" is an international phone number (+16048751070), not an account.
    (
        SensitiveFieldType.BANK_ACCOUNT,
        re.compile(r"(?<!\+)\b\d{8,17}\b"),
        "last4",
    ),
]


def mask_text(text: str | None) -> tuple[str | None, list[Detection]]:
    """Mask sensitive values inside free text. Idempotent on already-masked text."""
    if not text:
        return text, []
    detections: list[Detection] = []
    out = text

    for field_type, pattern, mode in _TEXT_RULES:

        def _sub(m: re.Match[str], _ft=field_type, _mode=mode) -> str:
            raw = next((g for g in m.groups() if g), None) or m.group(0)
            masked = REDACTED if _mode == "redact" else mask_last4(raw)
            detections.append(Detection(_ft, masked, "text"))
            # Preserve any prefix captured outside the digit group (e.g. "routing ")
            return m.group(0).replace(raw, masked)

        out = pattern.sub(_sub, out)

    return out, detections


def sensitive_values(text: str | None) -> list[str]:
    """The raw sensitive substrings `mask_text` would mask in `text`, longest first.

    Only for redacting a document in place (backend/services/source_pdf.py): the values are
    located and blacked out, never returned by the API, logged or stored.
    """
    if not text:
        return []
    found: set[str] = set()
    for _field_type, pattern, _mode in _TEXT_RULES:
        for m in pattern.finditer(text):
            found.add(next((g for g in m.groups() if g), None) or m.group(0))
    return sorted(found, key=len, reverse=True)


def mask_upload(data: dict) -> tuple[dict, list[Detection]]:
    """Mask every sensitive field and the free-text fields of an InvoiceUpload-shaped dict.

    Returns a new dict; the input is not modified and should be discarded by the caller.
    """
    masked = dict(data)
    detections: list[Detection] = []
    for name in LAST4_FIELDS:
        if name in masked:
            masked[name], det = mask_field(name, masked[name])
            if det:
                detections.append(det)
    for name in ("vendor_name", "vendor_invoice_number", "source_document", "raw_text"):
        if masked.get(name):
            masked[name], text_dets = mask_text(masked[name])
            detections.extend(text_dets)
    return masked, detections


def contains_unmasked(text: str | None) -> bool:
    """True if `mask_text` would change the text — used by the decision validator."""
    if not text:
        return False
    masked, _ = mask_text(text)
    return masked != text
