"""Plain-English explanation of an invoice's policy result, for the reviewer.

Deterministic: every sentence is built from what the agents recorded in the WorkflowContext
(the vendor lookup, the PO lookup, the duplicate check, how each field was read, the masked
scan) and the policy constants. No model text, so nothing here can be invented. Each reason
says what was found, why it matters, and what to check; `next_step` lists the checks in order.

Values are already masked by the time they reach the context, so nothing raw can appear here.
"""

from backend.governance.policy_engine import PolicyEngine
from backend.models import AgentName, ReasonCode, RiskLevel
from backend.orchestration.workflow_context import WorkflowContext

FIELD_LABELS = {
    "vendor_invoice_number": "invoice number",
    "vendor_name": "vendor name",
    "vendor_id": "vendor ID",
    "amount": "amount",
    "currency": "currency",
    "due_date": "due date",
    "purchase_order_id": "purchase order (PO) number",
}

# Why a reviewer should care that a field is missing.
FIELD_WHY = {
    "vendor_invoice_number": "it is how the vendor identifies this bill, and how a second copy "
    "of the same bill gets caught",
    "vendor_name": "without it there is no way to tell who is asking to be paid",
    "vendor_id": "without it there is no way to tell who is asking to be paid",
    "amount": "there is nothing to approve without a total",
    "currency": "the same number means a different amount in another currency",
    "due_date": "without it the payment can't be scheduled and late fees can't be avoided",
    "purchase_order_id": "a PO shows someone in the company approved this purchase, at this "
    "price, before the bill arrived — without one there is no record that it was ordered",
}

SOURCE_NOTE = {
    "model": "read by the AI model (found in the PDF, but not next to a clear label)",
    "default": "not on the invoice, so it was assumed",
    "placeholder": "unreadable, so a placeholder was used",
}

SENSITIVE_LABELS = {
    "bank_account": "bank account",
    "routing_number": "routing number",
    "tax_id": "tax ID",
}


def money(amount: float | None, currency: str) -> str:
    return "an unknown amount" if amount is None else f"{currency} {amount:,.2f}"


def label(field: str) -> str:
    return FIELD_LABELS.get(field, field.replace("_", " "))


def _vendor(ctx: WorkflowContext) -> str:
    name = (ctx.vendor or {}).get("name") or ctx.vendor_name
    return f"'{name}'" if name else "the vendor"


def _join(items: list[str]) -> str:
    if len(items) <= 1:
        return "".join(items)
    return ", ".join(items[:-1]) + " and " + items[-1]


class _Builder:
    def __init__(self, ctx: WorkflowContext, policy: PolicyEngine):
        self.ctx = ctx
        self.policy = policy
        self.reasons: list[str] = []
        self.steps: list[str] = []

    def add(self, reason: str, step: str | None = None) -> None:
        self.reasons.append(reason)
        if step and step not in self.steps:
            self.steps.append(step)

    # --- one method per reason code -------------------------------------------------------

    def duplicate(self) -> None:
        ctx = self.ctx
        if ctx.duplicate_match == "invoice_number":
            shared = f"the same invoice number ({ctx.vendor_invoice_number})"
        else:
            shared = f"the same amount ({money(ctx.amount, ctx.currency)}) within 30 days"
        self.add(
            f"Possible duplicate: {_vendor(ctx)} already sent {ctx.duplicate_of} with {shared}. "
            "Paying both would pay the same bill twice, so this one is blocked and the "
            "recommendation is to reject it.",
            f"Open {ctx.duplicate_of} and compare it with this invoice; reject this copy if it "
            "is the same bill",
        )

    def amount_above_limit(self) -> None:
        ctx = self.ctx
        ai_limit = self.policy.limit_for(ctx.acting_agent)
        human_limit = self.policy.limit_for(AgentName.HUMAN_REVIEWER)
        text = (
            f"Above the AI's limit: the invoice is for {money(ctx.amount, ctx.currency)}, more "
            f"than the {money(ai_limit, ctx.currency)} the system may approve on its own. "
        )
        if ctx.amount is not None and ctx.amount > human_limit:
            text += (
                f"It is also above the {money(human_limit, ctx.currency)} a reviewer may "
                "approve, so it stays blocked until someone with a higher limit signs off."
            )
            step = "Send it to someone with approval authority above the reviewer limit"
        else:
            text += f"A reviewer may approve up to {money(human_limit, ctx.currency)}."
            step = "Check the amount against what was ordered before approving"
        self.add(text, step)

    def unknown_vendor(self) -> None:
        ctx = self.ctx
        name = _vendor(ctx)
        self.add(
            f"New vendor: {name} is not on the approved vendor list (searched by "
            + ("ID and name" if ctx.vendor_id else "name")
            + "). That doesn't mean the invoice is fake — first-time suppliers are common — "
            "but nobody has confirmed this company exists, or that it is the one you buy from. "
            "Fake invoices from look-alike company names are a common fraud.",
            f"Confirm {name} is a real supplier your team bought from (ask the person who "
            "ordered, or contact the vendor using details you already have, not the ones on "
            "this invoice)",
        )

    def vendor_unverified(self) -> None:
        ctx = self.ctx
        status = (ctx.vendor or {}).get("verification_status") or "unknown"
        self.add(
            f"Vendor not verified: {_vendor(ctx)} is on the vendor list, but its status is "
            f"'{status}', not 'verified'. Its details (bank account, tax ID) haven't been "
            "confirmed, so payments to it need a person's sign-off.",
            f"Check why {_vendor(ctx)} is '{status}' with the vendor-management team",
        )

    def invalid_po(self) -> None:
        ctx = self.ctx
        po = ctx.purchase_order_id
        if not po:
            return  # no PO on the invoice — explained once, under missing fields
        if ctx.po_found is False:
            self.add(
                f"Purchase order not found: the invoice cites {po}, but there is no PO with "
                "that number. It may be a typo, a PO from another system, or made up — "
                "without a real PO there is no record anyone ordered this.",
                f"Ask the requester or the vendor for the correct PO number ({po} doesn't exist)",
            )
        else:
            owner = (ctx.purchase_order or {}).get("vendor_id") or "another vendor"
            self.add(
                f"Purchase order belongs to someone else: {po} exists, but it was issued to "
                f"{owner}, not {ctx.vendor_ref}. An invoice should only be paid against a PO "
                "issued to the same vendor.",
                f"Confirm which vendor {po} was issued to",
            )

    def po_mismatch(self) -> None:
        ctx = self.ctx
        po_amount = (ctx.purchase_order or {}).get("approved_amount")
        if ctx.amount is None or po_amount is None:
            return
        diff = ctx.amount - po_amount
        pct = abs(diff) / po_amount * 100 if po_amount else 0
        direction = "more" if diff > 0 else "less"
        self.add(
            f"Amount differs from the PO: the invoice is for {money(ctx.amount, ctx.currency)}, "
            f"but {ctx.purchase_order_id} approved {money(po_amount, ctx.currency)} — "
            f"{money(abs(diff), ctx.currency)} ({pct:.1f}%) {direction}. "
            + (
                "Billing more than was approved needs an explanation (extra items, price "
                "change, or an error)."
                if diff > 0
                else "Billing less is usually a partial delivery; check what was received."
            ),
            f"Find out why the invoice and {ctx.purchase_order_id} differ by "
            f"{money(abs(diff), ctx.currency)}",
        )

    def missing(self) -> None:
        ctx = self.ctx
        fields = [f for f in ctx.missing_fields if not (f == "vendor_id" and ctx.vendor_name)]
        if not fields:
            return
        parts = [f"{label(f)} — {FIELD_WHY.get(f, 'it is required')}" for f in fields]
        self.add(
            "Missing information: the invoice has no " + "; no ".join(parts) + ".",
            "Get the missing " + _join([label(f) for f in fields]) + " from the vendor or the "
            "person who ordered",
        )

    def malformed(self) -> None:
        ctx = self.ctx
        values = {f.field: f.value for f in ctx.extraction}
        parts = [
            f"the {label(f)} ('{values[f]}')" if values.get(f) else f"the {label(f)}"
            for f in ctx.malformed_fields
        ]
        self.add(
            f"Unreadable value: {_join(parts)} could not be read as a valid "
            + ("value" if len(parts) == 1 else "values")
            + " (for example a date that doesn't exist, or an amount that isn't a number). "
            "The system won't guess what was meant.",
            "Check " + _join([label(f) for f in ctx.malformed_fields]) + " on the original PDF",
        )

    def low_confidence(self) -> None:
        ctx = self.ctx
        threshold = self.policy.confidence_threshold
        unsure = [
            f
            for f in ctx.extraction
            if not f.missing and f.confidence < threshold and f.field != "vendor_id"
        ]
        detail = _join(
            [
                f"the {label(f.field)}"
                + (f" ('{f.value}')" if f.value else "")
                + f" was {SOURCE_NOTE.get(ctx.field_sources.get(f.field, ''), 'hard to read')}"
                for f in unsure
                if not f.malformed  # malformed fields are explained on their own
            ]
        )
        score = f"{(ctx.reading_confidence or 0):.0%}"
        self.add(
            f"Unclear details: reading confidence is {score}, below the {threshold:.0%} "
            "needed to trust the invoice's fields without a second look"
            + (f" — {detail}." if detail else "."),
            "Compare the fields shown here with the original PDF",
        )

    def sensitive(self) -> None:
        ctx = self.ctx
        found = [
            f"{text} {ctx.upload[key]}"
            for key, text in SENSITIVE_LABELS.items()
            if isinstance(ctx.upload.get(key), str) and ctx.upload[key].startswith("*")
        ]
        what = f" ({_join(found)})" if found else ""
        text = (
            f"Banking or tax details on the invoice: they were found{what} and masked, so only "
            "the last 4 digits are kept. Never pay to account details taken from an invoice — "
            "changing the bank account is the most common invoice scam."
        )
        if ctx.vendor_found is False:
            text += " Coming from a vendor that isn't on the list, this is treated as high risk."
        self.add(
            text,
            "Confirm the bank details by phoning the vendor on a number you already have",
        )

    def unauthorized(self) -> None:
        self.add(
            "Blocked action: an agent tried to use a tool it isn't allowed to. The call was "
            "stopped and recorded, and the invoice can't proceed automatically.",
            "Look at the blocked call in the audit trail",
        )

    def agent_failure(self) -> None:
        self.add(
            "Processing error: one of the agents failed or returned something unusable, so "
            "its checks are incomplete. Nothing is assumed to be fine.",
            "Re-check the invoice by hand, or re-process it",
        )

    def mock_unavailable(self) -> None:
        self.add(
            "A system was unreachable: the vendor, purchase-order or limit lookup didn't "
            "answer, so that check never ran. A check that didn't run is never counted as a pass.",
            "Re-process the invoice once the lookup service is back",
        )

    def insufficient_evidence(self) -> None:
        missing = []
        if self.ctx.vendor_found is None:
            missing.append("vendor")
        if self.ctx.po_found is None:
            missing.append("purchase order")
        what = _join(missing) or "vendor and purchase order"
        self.add(
            f"Not enough evidence: the {what} check didn't complete, so there isn't enough "
            "on record to approve automatically.",
            f"Confirm the {what} by hand",
        )

    def passed(self) -> None:
        ctx = self.ctx
        po_amount = (ctx.purchase_order or {}).get("approved_amount")
        self.add(
            f"Everything checks out: {_vendor(ctx)} is a verified vendor, "
            f"{ctx.purchase_order_id} approved exactly {money(po_amount, ctx.currency)}, "
            f"the amount is within the {money(self.policy.auto_approve_max, ctx.currency)} "
            "auto-approve limit, and no earlier copy of this invoice was found.",
        )


_ORDER = [
    (ReasonCode.DUPLICATE_INVOICE, _Builder.duplicate),
    (ReasonCode.AMOUNT_ABOVE_LIMIT, _Builder.amount_above_limit),
    (ReasonCode.UNKNOWN_VENDOR, _Builder.unknown_vendor),
    (ReasonCode.VENDOR_UNVERIFIED, _Builder.vendor_unverified),
    (ReasonCode.INVALID_PURCHASE_ORDER, _Builder.invalid_po),
    (ReasonCode.PO_AMOUNT_MISMATCH, _Builder.po_mismatch),
    (ReasonCode.MISSING_REQUIRED_FIELD, _Builder.missing),
    (ReasonCode.MALFORMED_FIELD, _Builder.malformed),
    (ReasonCode.LOW_CONFIDENCE, _Builder.low_confidence),
    (ReasonCode.SENSITIVE_DATA_DETECTED, _Builder.sensitive),
    (ReasonCode.UNAUTHORIZED_TOOL_CALL, _Builder.unauthorized),
    (ReasonCode.AGENT_FAILURE, _Builder.agent_failure),
    (ReasonCode.MOCK_SYSTEM_UNAVAILABLE, _Builder.mock_unavailable),
    (ReasonCode.INSUFFICIENT_EVIDENCE, _Builder.insufficient_evidence),
]


def explain(ctx: WorkflowContext, policy: PolicyEngine) -> tuple[list[str], str, list[str]]:
    """Returns (reasons, next step, missing information) for the policy result on ctx."""
    result = ctx.policy
    assert result is not None
    b = _Builder(ctx, policy)
    codes = set(result.reason_codes)
    for code, method in _ORDER:
        if code in codes:
            method(b)
    if result.risk_level == RiskLevel.LOW and ReasonCode.POLICY_PASSED in codes:
        b.passed()
        next_step = "Nothing to do: the payment is authorized automatically under policy."
    elif b.steps:
        steps = [*b.steps, "Then approve or reject"]
        next_step = " ".join(f"{i}. {s}." for i, s in enumerate(steps, 1))
    else:
        next_step = "Review the invoice and approve or reject it."
    missing = [label(f) for f in ctx.missing_fields if not (f == "vendor_id" and ctx.vendor_name)]
    return b.reasons, next_step, missing
