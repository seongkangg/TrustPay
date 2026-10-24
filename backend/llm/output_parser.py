"""Structured-output guardrail for model responses (spec §20).

Every model response must be a JSON object matching one of the schemas below.
Anything else raises MalformedOutput — it is never silently accepted or "repaired".
"""

import json
import re
from typing import TypeVar

from pydantic import BaseModel, Field, ValidationError

from backend.models import ExtractedField, Recommendation


class MalformedOutput(ValueError):
    """Model output could not be parsed or did not match the schema."""


# --- output schemas, one per prompt --------------------------------------


class ExtractionOutput(BaseModel):
    fields: list[ExtractedField]
    notes: str = ""


class SummaryOutput(BaseModel):
    summary: str = Field(..., min_length=1)
    confidence: float = Field(..., ge=0.0, le=1.0)


class RecommendationOutput(BaseModel):
    recommendation: Recommendation
    confidence: float = Field(..., ge=0.0, le=1.0)
    reasons: list[str] = Field(default_factory=list)
    next_step: str = ""


SCHEMAS: dict[str, type[BaseModel]] = {
    "extraction": ExtractionOutput,
    "summary": SummaryOutput,
    "recommendation": RecommendationOutput,
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
