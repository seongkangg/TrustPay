"""Output parser guardrails and the deterministic MockLLM (acceptance B8)."""

import json

import pytest

from backend.config import Settings
from backend.llm import (
    ExtractionOutput,
    LLMError,
    MalformedOutput,
    MockLLM,
    RecommendationOutput,
    SummaryOutput,
    get_llm_client,
    parse_as,
    parse_json_object,
)
from backend.llm.prompts import (
    extraction_prompt,
    recommendation_prompt,
    verification_summary_prompt,
)


def test_parse_json_object_tolerates_fences_and_prose():
    assert parse_json_object('```json\n{"a": 1}\n```') == {"a": 1}
    assert parse_json_object('Sure! Here it is: {"a": 1} hope that helps') == {"a": 1}


@pytest.mark.parametrize("bad", ["", "   ", "no json here", "[1, 2]", "{not json}", '{"a": 1'])
def test_parse_json_object_rejects_malformed(bad):
    with pytest.raises(MalformedOutput):
        parse_json_object(bad)


def test_parse_as_enforces_schema():
    good = parse_as(SummaryOutput, '{"summary": "ok", "confidence": 0.9}')
    assert good.confidence == 0.9
    with pytest.raises(MalformedOutput):
        parse_as(SummaryOutput, '{"summary": "ok", "confidence": 1.9}')
    with pytest.raises(MalformedOutput):
        parse_as(RecommendationOutput, '{"recommendation": "pay_now", "confidence": 0.9}')


def test_mock_extraction_marks_missing_fields():
    out = parse_as(
        ExtractionOutput,
        MockLLM().complete(
            extraction_prompt({"amount": 4250.0, "due_date": None, "vendor_id": "V-101"})
        ),
    )
    by_name = {f.field: f for f in out.fields}
    assert by_name["amount"].confidence > 0.9 and not by_name["amount"].missing
    assert by_name["due_date"].missing and by_name["due_date"].confidence == 0.0


def test_mock_recommendation_follows_risk():
    low = json.loads(
        MockLLM().complete(recommendation_prompt({"risk_level": "low", "reason_codes": []}))
    )
    high = json.loads(
        MockLLM().complete(
            recommendation_prompt({"risk_level": "high", "reason_codes": ["AMOUNT_ABOVE_LIMIT"]})
        )
    )
    dup = json.loads(
        MockLLM().complete(
            recommendation_prompt({"risk_level": "high", "reason_codes": ["DUPLICATE_INVOICE"]})
        )
    )
    assert (low["recommendation"], high["recommendation"], dup["recommendation"]) == (
        "approve",
        "escalate",
        "reject",
    )
    assert all(0 <= r["confidence"] <= 1 for r in (low, high, dup))


def test_mock_summary_is_deterministic():
    prompt = verification_summary_prompt(
        {"vendor_found": False, "po_found": False, "po_matches": False}
    )
    assert MockLLM().complete(prompt) == MockLLM().complete(prompt)
    assert "not found" in json.loads(MockLLM().complete(prompt))["summary"]


def test_mock_requires_structured_prompt():
    with pytest.raises(LLMError):
        MockLLM().complete("free text prompt")


def test_factory_defaults_to_mock_and_watsonx_needs_credentials():
    assert get_llm_client(Settings(llm_mode="mock")).mode == "mock"
    with pytest.raises(LLMError):
        get_llm_client(Settings(llm_mode="watsonx", watsonx_api_key="", watsonx_project_id=""))
