"""Structured-output guardrail for model responses (spec §20).

Every model response must be a JSON object matching one of the schemas below.
Anything else raises MalformedOutput — it is never silently accepted or "repaired".
"""

import json
import re
from typing import TypeVar

from pydantic import BaseModel, Field, ValidationError, field_validator

from backend.models import ExtractedField, Recommendation


class MalformedOutput(ValueError):
    """Model output could not be parsed or did not match the schema."""


# --- output schemas, one per prompt --------------------------------------


class ExtractionOutput(BaseModel):
    fields: list[ExtractedField]
    notes: str = ""


def _null_confidence_is_zero(v):
    """Real models sometimes send `"confidence": null`; that is zero confidence (which escalates)."""
    return 0.0 if v is None else v


class SummaryOutput(BaseModel):
    summary: str = Field(..., min_length=1)
    confidence: float = Field(..., ge=0.0, le=1.0)

    _conf = field_validator("confidence", mode="before")(
        classmethod(lambda cls, v: _null_confidence_is_zero(v))
    )


class RecommendationOutput(BaseModel):
    recommendation: Recommendation
    confidence: float = Field(..., ge=0.0, le=1.0)
    reasons: list[str] = Field(default_factory=list)
    next_step: str = ""

    _conf = field_validator("confidence", mode="before")(
        classmethod(lambda cls, v: _null_confidence_is_zero(v))
    )


class InvoiceFieldsOutput(BaseModel):
    """Fields read from a free-form invoice document, each copied exactly as written (or null).

    Values are untrusted: backend/inbox/llm_extraction.py keeps only those that appear in the
    document text."""

    vendor_invoice_number: str | None = None
    vendor_name: str | None = None
    vendor_id: str | None = None
    amount: str | None = None
    currency: str | None = None
    due_date: str | None = None
    purchase_order_id: str | None = None

    @field_validator("*", mode="before")
    @classmethod
    def scalar_to_text(cls, v):
        if isinstance(v, bool):
            raise ValueError("expected text")
        if isinstance(v, int | float):
            return str(v)
        return v


SCHEMAS: dict[str, type[BaseModel]] = {
    "extraction": ExtractionOutput,
    "summary": SummaryOutput,
    "recommendation": RecommendationOutput,
    "invoice_fields": InvoiceFieldsOutput,
}

T = TypeVar("T", bound=BaseModel)

_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)


def parse_json_object(text: str) -> dict:
    """Extract the first JSON object from model text (tolerates code fences and prose)."""
    if not isinstance(text, str) or not text.strip():
        raise MalformedOutput("empty model output")
    cleaned = _FENCE.sub("", text.strip())
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise MalformedOutput("no JSON object in model output")
    try:
        data = json.loads(cleaned[start : end + 1])
    except json.JSONDecodeError as exc:
        raise MalformedOutput(f"invalid JSON: {exc.msg}") from exc
    if not isinstance(data, dict):
        raise MalformedOutput("model output is not a JSON object")
    return data


def parse_as(schema: type[T], text: str) -> T:
    data = parse_json_object(text)
    try:
        return schema.model_validate(data)
    except ValidationError as exc:
        raise MalformedOutput(
            f"output does not match {schema.__name__}: {exc.error_count()} error(s)"
        ) from exc
