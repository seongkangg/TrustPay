"""LLM clients: `MockLLM` (default, deterministic), `WatsonxLLM` (Granite via watsonx.ai),
and `OllamaLLM` (Granite or another open model served locally by Ollama).

All return raw text; agents parse it with output_parser. The model is used only for
extraction confidence, summaries, and recommendation text — never for authorization.
"""

import json
import re
from typing import Protocol

import httpx

from backend.config import Settings, get_settings


class LLMError(RuntimeError):
    """The model could not be called (config, network, provider error)."""


class LLMClient(Protocol):
    mode: str

    # temperature 0 = deterministic (the default for every call). Only the Approval Agent samples
    # with a higher temperature, to measure how consistently the model gives the same answer.
    def complete(self, prompt: str, *, temperature: float = 0.0) -> str: ...


_SCHEMA = re.compile(r"<schema>(\w+)</schema>")
_CONTEXT = re.compile(r"<context>(.*)</context>", re.DOTALL)

PRESENT_FIELD_CONFIDENCE = 0.98
MISSING_FIELD_CONFIDENCE = 0.0


class MockLLM:
    """Deterministic stand-in. Reads the prompt's <schema> and <context> and answers in kind,
    so demo runs never depend on live model behavior."""

    mode = "mock"

    def complete(self, prompt: str, *, temperature: float = 0.0) -> str:  # noqa: ARG002 — deterministic
        schema = _SCHEMA.search(prompt)
        ctx_match = _CONTEXT.search(prompt)
        if not schema or not ctx_match:
            raise LLMError("mock prompt is missing <schema> or <context>")
        context = json.loads(ctx_match.group(1))
        handler = {
            "extraction": self._extraction,
            "summary": self._summary,
            "recommendation": self._recommendation,
            "invoice_fields": self._invoice_fields,
        }.get(schema.group(1))
        if handler is None:
            raise LLMError(f"mock has no handler for schema {schema.group(1)}")
        return json.dumps(handler(context))

    @staticmethod
    def _invoice_fields(context: dict) -> dict:
        # The mock does not read documents: free-form invoices stay unfilled (→ escalated),
        # and the labelled demo PDFs never need this step.
        return {name: None for name in context.get("fields_needed", [])}

    @staticmethod
    def _extraction(context: dict) -> dict:
        parsed = context.get("parsed_fields", {})
        fields = []
        for name, value in parsed.items():
            present = value not in (None, "")
            fields.append(
                {
                    "field": name,
                    "value": None if not present else str(value),
                    "confidence": PRESENT_FIELD_CONFIDENCE if present else MISSING_FIELD_CONFIDENCE,
                    "missing": not present,
                    "malformed": False,
                }
            )
        return {"fields": fields, "notes": "mock extraction from structured upload"}

    @staticmethod
    def _summary(context: dict) -> dict:
        parts = []
        if "vendor_found" in context:
            parts.append(
                "Vendor verified."
                if context.get("vendor_status") == "verified"
                else "Vendor not found in vendor master."
                if context.get("vendor_found") is False
                else f"Vendor status is {context.get('vendor_status')}."
            )
        if "po_found" in context:
            parts.append(
                "Purchase order matches."
                if context.get("po_matches")
                else "Purchase order does not match."
            )
        if context.get("duplicate_of"):
            parts.append(f"Duplicate of {context['duplicate_of']}.")
        if "risk_level" in context:
            parts.append(
                f"Policy engine assigned {context['risk_level']} risk via "
                + ", ".join(context.get("rules_triggered", []))
                + "."
            )
        return {"summary": " ".join(parts) or "No findings.", "confidence": 0.9}

    @staticmethod
    def _recommendation(context: dict) -> dict:
        risk = context.get("risk_level")
        codes = context.get("reason_codes", [])
        if "DUPLICATE_INVOICE" in codes:
            rec, conf, step = "reject", 0.92, "Reject as duplicate; notify vendor."
        elif risk == "low":
            rec, conf, step = "approve", 0.94, "Proceed with automatic processing."
        else:
            rec, conf, step = "escalate", 0.88, "Route to a finance reviewer for human approval."
        reasons = [f"Policy rule {r} triggered." for r in context.get("rules_triggered", [])] or [
            "All policy checks passed."
        ]
        return {"recommendation": rec, "confidence": conf, "reasons": reasons, "next_step": step}


class WatsonxLLM:
    """Granite on watsonx.ai. Only constructed when LLM_MODE=watsonx."""

    mode = "watsonx"

    def __init__(self, settings: Settings):
        if not (settings.watsonx_api_key and settings.watsonx_project_id):
            raise LLMError(
                "WATSONX_API_KEY and WATSONX_PROJECT_ID are required for LLM_MODE=watsonx"
            )
        try:
            from ibm_watsonx_ai import Credentials
            from ibm_watsonx_ai.foundation_models import ModelInference
        except ImportError as exc:  # pragma: no cover - depends on optional package
            raise LLMError("ibm-watsonx-ai is not installed") from exc
        self._model = ModelInference(
            model_id=settings.watsonx_model_id,
            credentials=Credentials(url=settings.watsonx_url, api_key=settings.watsonx_api_key),
            project_id=settings.watsonx_project_id,
            params={"decoding_method": "greedy", "max_new_tokens": 600, "temperature": 0},
        )

    def complete(self, prompt: str, *, temperature: float = 0.0) -> str:
        params = (
            {"decoding_method": "sample", "temperature": temperature, "max_new_tokens": 600}
            if temperature > 0
            else None
        )
        try:
            return self._model.generate_text(prompt=prompt, params=params)
        except Exception as exc:  # noqa: BLE001 — provider errors are all LLMError to callers
            raise LLMError(str(exc)) from exc


OLLAMA_TIMEOUT_SECONDS = 120  # the first call loads the model into memory and can be slow


class OllamaLLM:
    """A model served by a local Ollama instance. Only constructed when LLM_MODE=ollama."""

    mode = "ollama"

    def __init__(self, settings: Settings, client: httpx.Client | None = None):
        if not settings.ollama_model:
            raise LLMError("OLLAMA_MODEL is required for LLM_MODE=ollama")
        self._model = settings.ollama_model
        self._client = client or httpx.Client(
            base_url=settings.ollama_url, timeout=OLLAMA_TIMEOUT_SECONDS
        )

    def complete(self, prompt: str, *, temperature: float = 0.0) -> str:
        try:
            resp = self._client.post(
                "/api/generate",
                json={
                    "model": self._model,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json",
                    "options": {"temperature": temperature},
                },
            )
            resp.raise_for_status()
            return resp.json()["response"]
        except (httpx.HTTPError, ValueError, KeyError) as exc:
            raise LLMError(f"ollama call failed: {exc}") from exc


def get_llm_client(settings: Settings | None = None) -> LLMClient:
    settings = settings or get_settings()
    if settings.llm_mode == "watsonx":
        return WatsonxLLM(settings)
    if settings.llm_mode == "ollama":
        return OllamaLLM(settings)
    return MockLLM()
