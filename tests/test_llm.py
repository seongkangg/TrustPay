"""Output parser guardrails and the deterministic MockLLM (acceptance B8)."""

import json

import httpx
import pytest

from backend.config import Settings
from backend.llm import (
    ExtractionOutput,
    LLMError,
    MalformedOutput,
    MockLLM,
    OllamaLLM,
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


def _ollama(handler) -> OllamaLLM:
    client = httpx.Client(base_url="http://ollama.test", transport=httpx.MockTransport(handler))
    return OllamaLLM(Settings(llm_mode="ollama", ollama_model="granite3.3:8b"), client=client)


def test_factory_selects_ollama():
    client = get_llm_client(Settings(llm_mode="ollama", ollama_model="granite3.3:8b"))
    assert isinstance(client, OllamaLLM) and client.mode == "ollama"
    with pytest.raises(LLMError):
        get_llm_client(Settings(llm_mode="ollama", ollama_model=""))


def test_ollama_sends_json_request_and_returns_response_text():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["path"] = request.url.path
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json={"response": '{"summary": "ok", "confidence": 0.8}'})

    out = _ollama(handler).complete("prompt text")
    assert parse_as(SummaryOutput, out).summary == "ok"
    assert seen["path"] == "/api/generate"
    assert seen["body"]["model"] == "granite3.3:8b"
    assert seen["body"]["format"] == "json" and seen["body"]["stream"] is False
    assert seen["body"]["options"]["temperature"] == 0


@pytest.mark.parametrize(
    "handler",
    [
        lambda r: httpx.Response(500, text="model crashed"),
        lambda r: httpx.Response(200, json={"error": "no response key"}),
        lambda r: httpx.Response(200, text="not json"),
    ],
)
def test_ollama_failures_raise_llm_error(handler):
    with pytest.raises(LLMError):
        _ollama(handler).complete("prompt text")


def test_ollama_unreachable_raises_llm_error():
    def handler(request):
        raise httpx.ConnectError("connection refused")

    with pytest.raises(LLMError):
        _ollama(handler).complete("prompt text")


def test_extraction_accepts_numeric_values_from_real_models():
    """Granite returns `"value": 4250.0` for numeric fields; the schema stores it as text."""
    out = parse_as(
        ExtractionOutput,
        '{"fields": [{"field": "amount", "value": 4250.0, "confidence": 1},'
        ' {"field": "vendor_id", "value": "V-101", "confidence": 0.9},'
        ' {"field": "due_date", "value": null, "confidence": 0, "missing": true}], "notes": ""}',
    )
    by_name = {f.field: f for f in out.fields}
    assert by_name["amount"].value == "4250.0" and by_name["vendor_id"].value == "V-101"
    assert by_name["due_date"].value is None
    with pytest.raises(MalformedOutput):
        parse_as(
            ExtractionOutput, '{"fields": [{"field": "amount", "value": [1], "confidence": 1}]}'
        )
