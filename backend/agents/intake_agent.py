"""Intake Agent — extracts invoice fields and reports confidence.

Allowed tool: document_parser. May not approve, reject, pay, or look anything up.
The parser handles structured uploads; the model assigns per-field confidence and the
deterministic validators flag missing / malformed required fields.
"""

from typing import Any

from backend.agents.base_agent import BaseAgent
from backend.llm.output_parser import ExtractionOutput
from backend.llm.prompts import extraction_prompt
from backend.models import (
    AgentDecision,
    AgentName,
    EventType,
    Explanation,
    ReasonCode,
    Severity,
    ToolName,
)
from backend.orchestration.workflow_context import WorkflowContext
from backend.utils.validation import REQUIRED_INVOICE_FIELDS, malformed_fields, missing_fields

PARSED_FIELDS = (
    "vendor_invoice_number",
    "vendor_name",
    "vendor_id",
    "amount",
    "currency",
    "due_date",
    "purchase_order_id",
    "bank_account",
    "routing_number",
    "tax_id",
)
# Fields whose confidence counts toward the overall score (vendor_name is a fallback for vendor_id).
_CONFIDENCE_FIELDS = (set(REQUIRED_INVOICE_FIELDS) - {"vendor"}) | {"vendor_id"}


def parse_document(params: dict[str, Any]) -> dict[str, Any]:
    """The `document_parser` tool. Uploads are structured JSON in the prototype; a PDF/image
    path would plug in here without touching the agent."""
    upload = params.get("upload") or {}
    return {
        "fields": {name: upload.get(name) for name in PARSED_FIELDS},
        "source_document": upload.get("source_document"),
    }


class IntakeAgent(BaseAgent):
    name = AgentName.INTAKE

    def __init__(self, gov, llm=None):
        super().__init__(gov, llm)
        gov.interceptor.register(ToolName.DOCUMENT_PARSER, parse_document)

    def _run(self, ctx: WorkflowContext) -> AgentDecision:
        parsed_call = self.request_tool(
            ctx,
            ToolName.DOCUMENT_PARSER,
            "extract invoice fields from the uploaded document",
            upload=ctx.upload,
        )
        if not parsed_call.ok:
            raise RuntimeError("document parser unavailable")
        parsed: dict[str, Any] = parsed_call.result["fields"]
        parse_evidence = parsed_call.call.evidence_id

        extraction = self.ask(extraction_prompt(parsed), ExtractionOutput)
        if extraction is None:
            raise RuntimeError("extraction output did not match schema")

        missing = missing_fields(parsed)
        malformed = malformed_fields(parsed)
        missing_set = set(missing) | (
            {"vendor_id", "vendor_name"} if "vendor_id/vendor_name" in missing else set()
        )

        fields = []
        for f in extraction.fields:
            f.missing = f.missing or f.field in missing_set
            f.malformed = f.malformed or f.field in malformed
            fields.append(f)

        ctx.extracted = parsed
        ctx.extraction = fields
        ctx.missing_fields = missing
        ctx.malformed_fields = malformed

        required_conf = [f.confidence for f in fields if f.field in _CONFIDENCE_FIELDS]
        confidence = min(required_conf) if required_conf else 0.0

        codes: list[ReasonCode] = []
        if missing:
            codes.append(ReasonCode.MISSING_REQUIRED_FIELD)
        if malformed:
            codes.append(ReasonCode.MALFORMED_FIELD)

        present = [f.field for f in fields if not f.missing]
        self.record(
            ctx,
            EventType.INVOICE_EXTRACTED,
            Severity.LOW if not codes else Severity.MEDIUM,
            reason_codes=codes,
            output_summary=f"{len(present)} fields extracted; missing={missing or 'none'}; malformed={malformed or 'none'}",
            evidence_refs=[parse_evidence or ""],
        )
        reasons = [
            f"Extracted {len(present)} of {len(fields)} fields from {parsed_call.result.get('source_document') or 'upload'}."
        ]
        if missing:
            reasons.append("Missing required fields: " + ", ".join(missing) + ".")
        if malformed:
            reasons.append("Malformed fields: " + ", ".join(malformed) + ".")
        if ctx.sensitive_detected:
            reasons.append("Sensitive banking/tax data was present and has been masked.")

        return self.decide(
            ctx,
            decision="fields_extracted",
            confidence=confidence,
            evidence_ids=[e for e in (parse_evidence, ctx.scan_evidence_id) if e],
            explanation=Explanation(
                decision="fields_extracted",
                reasons=reasons,
                evidence=[e for e in (parse_evidence, ctx.scan_evidence_id) if e],
                missing_information=missing,
                recommended_next_step="verify vendor and purchase order",
            ),
            reason_codes=codes,
        )
