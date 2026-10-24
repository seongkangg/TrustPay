"""Model fallback for free-form invoices: ask the LLM for the fields the label parser missed,
then keep only values that can be found in the document itself.

The model sees the masked text. Every value it returns is checked against that text — an
invoice number, vendor name, or PO that is not written there is discarded, an amount must
match a number in the document, a date must match a date written in the document. A
discarded or unreadable value leaves the field empty, so the Intake agent flags it and
governance escalates. The model can fill gaps; it cannot invent facts.

Bank / routing / tax identifiers are never requested from the model; only the label parser
reads those, and they are masked before storage either way.
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Any

from backend.inbox.pdf_parser import CURRENCY_SYMBOLS, _number, normalize_date
from backend.llm.granite_client import LLMClient, LLMError
from backend.llm.output_parser import InvoiceFieldsOutput, MalformedOutput, parse_as
from backend.llm.prompts import invoice_fields_prompt
from backend.models import Currency
from backend.services.masking_service import mask_text

log = logging.getLogger(__name__)

MODEL_FIELDS = (
    "vendor_invoice_number",
    "vendor_name",
    "vendor_id",
    "amount",
    "currency",
    "due_date",
    "purchase_order_id",
)

_NUMBERS = re.compile(r"\d[\d,]*(?:\.\d+)?")
_MONTH = r"[A-Z][a-z]{2,8}\.?"
_DATE_CANDIDATES = re.compile(
    rf"\d{{4}}-\d{{2}}-\d{{2}}"
    rf"|\d{{1,2}}/\d{{1,2}}/\d{{4}}"
    rf"|{_MONTH} \d{{1,2}}(?:st|nd|rd|th)?,? \d{{4}}"
    rf"|\d{{1,2}}(?:st|nd|rd|th)? {_MONTH} \d{{4}}"
)
_KNOWN_CURRENCIES = {c.value for c in Currency}


@dataclass
class ModelExtraction:
    filled: dict[str, Any] = field(default_factory=dict)  # field → normalized value
    rejected: dict[str, str] = field(default_factory=dict)  # field → what the model said
    error: str | None = None  # model unavailable / malformed output


def _squash(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip().lower()


def appears_in_document(name: str, value: str, text: str) -> bool:
    """True when `value` for field `name` is actually written in `text`."""
    if name == "amount":
        n = _number(value)
        return n is not None and any(
            (m := _number(tok)) is not None and abs(m - n) < 0.005 for tok in _NUMBERS.findall(text)
        )
    if name == "due_date":
        if _squash(value) in _squash(text):
            return True
        target = normalize_date(value)
        return target is not None and any(
            normalize_date(c) == target for c in _DATE_CANDIDATES.findall(text)
        )
    if name == "currency":
        code = value.strip().upper()
        return code in text.upper() or any(
            sym in text for sym, c in CURRENCY_SYMBOLS.items() if c == code or sym == value.strip()
        )
    return _squash(value) in _squash(text)


def normalize(name: str, value: str) -> Any:
    """Convert a verbatim document value to what InvoiceUpload expects; None if not possible."""
    if name == "amount":
        n = _number(value)
        return n if n is not None and n > 0 else None
    if name == "due_date":
        return normalize_date(value)
    if name == "currency":
        v = value.strip()
        code = CURRENCY_SYMBOLS.get(v, v.upper())
        return code if code in _KNOWN_CURRENCIES else None
    if name in ("vendor_id", "purchase_order_id"):
        return value.strip().upper()
    return value.strip()


def extract_missing_fields(llm: LLMClient, text: str, upload: dict[str, Any]) -> ModelExtraction:
    missing = [f for f in MODEL_FIELDS if upload.get(f) in (None, "")]
    result = ModelExtraction()
    if not missing:
        return result

    masked, _ = mask_text(text)
    try:
        out = parse_as(InvoiceFieldsOutput, llm.complete(invoice_fields_prompt(masked, missing)))
    except (LLMError, MalformedOutput, TimeoutError) as exc:
        result.error = f"{type(exc).__name__}: {exc}"
        log.warning("inbox: model field extraction unavailable: %s", exc)
        return result

    for name in missing:
        raw = getattr(out, name)
        if raw is None or not str(raw).strip():
            continue
        raw = str(raw).strip()
        if not appears_in_document(name, raw, masked):
            result.rejected[name] = raw
            continue
        value = normalize(name, raw)
        if value is None:
            result.rejected[name] = raw
            continue
        result.filled[name] = value

    if result.rejected:
        log.info(
            "inbox: discarded model values not found in the document: %s", sorted(result.rejected)
        )
    return result
