"""Prompt templates, one per agent task.

Every prompt: (1) embeds already-masked context as JSON inside <context> tags,
(2) names the output schema inside <schema> tags, (3) demands a single JSON object.
Sensitive values are masked by the governance layer before they reach this module.
"""

import json
from typing import Any

SYSTEM_RULES = (
    "You are a component of an invoice-governance system. "
    "You never approve payments and never call tools. "
    "Respond with ONE JSON object and nothing else. "
    "Base every statement on the context block; do not invent vendors, amounts, or policies. "
    "Never repeat bank account, routing, or tax identifiers beyond their masked form."
)


def _wrap(schema: str, task: str, context: dict[str, Any], output_spec: str) -> str:
    return (
        f"{SYSTEM_RULES}\n\n"
        f"<schema>{schema}</schema>\n"
        f"<task>{task}</task>\n"
        f"<context>{json.dumps(context, default=str, sort_keys=True)}</context>\n"
        f"<output>{output_spec}</output>"
    )


def extraction_prompt(parsed_fields: dict[str, Any]) -> str:
    return _wrap(
        "extraction",
        "Report each invoice field with a confidence score. Mark fields that are missing or malformed.",
        {"parsed_fields": parsed_fields},
        '{"fields":[{"field":str,"value":str|null,"confidence":0..1,"missing":bool,"malformed":bool}],"notes":str}',
    )


MAX_DOCUMENT_CHARS = 6000


def invoice_fields_prompt(document_text: str, fields_needed: list[str]) -> str:
    """Read fields out of a free-form invoice. `document_text` must already be masked."""
    return _wrap(
        "invoice_fields",
        "Read the invoice in the context and fill in only the fields listed in fields_needed. "
        "Copy each value EXACTLY as it is written in the document (same spelling, digits, and "
        "date format) — do not reformat, compute, or guess. vendor_name is the company that "
        "issued the invoice (the letterhead), not the Bill To / Ship To party. amount is the final "
        "total due, not a subtotal, tax, or line item. due_date is the payment due date, not the "
        "invoice date. Use null for anything not present in the document.",
        {"document_text": document_text[:MAX_DOCUMENT_CHARS], "fields_needed": fields_needed},
        '{"vendor_invoice_number":str|null,"vendor_name":str|null,"vendor_id":str|null,'
        '"amount":str|null,"currency":str|null,"due_date":str|null,"purchase_order_id":str|null}',
    )


def verification_summary_prompt(findings: dict[str, Any]) -> str:
    return _wrap(
        "summary",
        "Summarize the vendor, purchase-order, and duplicate findings in one or two sentences.",
        findings,
        '{"summary":str,"confidence":0..1}',
    )


def risk_reasoning_prompt(policy: dict[str, Any]) -> str:
    return _wrap(
        "summary",
        "Explain, for a finance reviewer, why the deterministic policy engine assigned this risk level. "
        "Do not change the risk level or add rules.",
        policy,
        '{"summary":str,"confidence":0..1}',
    )


def recommendation_prompt(case: dict[str, Any]) -> str:
    return _wrap(
        "recommendation",
        "Recommend approve, reject, or escalate. High or medium risk must be escalate (or reject for "
        "duplicates). Cite reasons drawn only from the context.",
        case,
        '{"recommendation":"approve"|"reject"|"escalate","confidence":0..1,"reasons":[str],"next_step":str}',
    )
