"""Verification Agent — validates vendor, purchase order, and duplicates.

Allowed tools: vendor_lookup, po_lookup. May never change vendor or PO records.
Lookups are deterministic (confidence 1.0); the model only writes the summary sentence.
If an enterprise system is unavailable the agent stops and escalates — it never assumes
a vendor or PO is valid.
"""

from datetime import timedelta
from typing import Any

from sqlalchemy import and_, or_, select

from backend.agents.base_agent import BaseAgent
from backend.database.tables import InvoiceRow
from backend.llm.output_parser import SummaryOutput
from backend.llm.prompts import verification_summary_prompt
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
from backend.utils.timestamps import now_utc
from backend.utils.validation import normalize_vendor_name

DUPLICATE_WINDOW_DAYS = 30


class VerificationAgent(BaseAgent):
    name = AgentName.VERIFICATION

    def _run(self, ctx: WorkflowContext) -> AgentDecision:
        evidence: list[str] = []
        codes: list[ReasonCode] = []
        reasons: list[str] = []

        # --- vendor ----------------------------------------------------------
        self.record(
            ctx,
            EventType.VENDOR_LOOKUP_REQUESTED,
            Severity.LOW,
            input_summary=f"vendor_id={ctx.vendor_id} vendor_name={ctx.vendor_name}",
        )
        if ctx.vendor_id or ctx.vendor_name:
            by_name = not ctx.vendor_id
            v = self.request_tool(
                ctx,
                ToolName.VENDOR_LOOKUP,
                "match the vendor name on the invoice to the vendor master"
                if by_name
                else "confirm the vendor exists and is verified",
                **({"vendor_name": ctx.vendor_name} if by_name else {"vendor_id": ctx.vendor_id}),
            )
            if v.call.evidence_id:
                evidence.append(v.call.evidence_id)
            if v.ok:
                ctx.vendor = v.result
                ctx.vendor_found = v.result is not None
                if by_name and v.result:
                    # Resolved by name: from here on (PO match, duplicates) the ID is known.
                    ctx.extracted["vendor_id"] = v.result["vendor_id"]
                    reasons.append(
                        f"Vendor name '{ctx.vendor_name}' matched vendor master record {v.result['vendor_id']}."
                    )
        status = (ctx.vendor or {}).get("verification_status")
        if ctx.vendor_found is True and status == "verified":
            self.record(
                ctx,
                EventType.VENDOR_VERIFIED,
                Severity.LOW,
                evidence_refs=evidence[-1:],
                output_summary=f"vendor {ctx.vendor_ref} verified",
            )
            reasons.append(f"Vendor {ctx.vendor_ref} is in the vendor master and verified.")
        else:
            if ctx.vendor_found is False:
                codes.append(ReasonCode.UNKNOWN_VENDOR)
                reasons.append(
                    f"Vendor {ctx.vendor_ref} was not found in the approved vendor database."
                )
            elif ctx.vendor_found is True:
                codes.append(ReasonCode.VENDOR_UNVERIFIED)
                reasons.append(f"Vendor {ctx.vendor_ref} exists but its status is {status}.")
            self.record(
                ctx,
                EventType.VENDOR_UNVERIFIED,
                Severity.HIGH if ctx.vendor_found is False else Severity.MEDIUM,
                reason_codes=codes[-1:],
                evidence_refs=evidence[-1:],
                output_summary=f"vendor {ctx.vendor_ref}: found={ctx.vendor_found} status={status}",
            )

        # --- purchase order --------------------------------------------------
        po_matches = False
        if ctx.purchase_order_id:
            p = self.request_tool(
                ctx,
                ToolName.PO_LOOKUP,
                "compare the invoice against its purchase order",
                purchase_order_id=ctx.purchase_order_id,
            )
            if p.call.evidence_id:
                evidence.append(p.call.evidence_id)
            if p.ok:
                ctx.purchase_order = p.result
                ctx.po_found = p.result is not None
        if ctx.po_found is False:
            codes.append(ReasonCode.INVALID_PURCHASE_ORDER)
            reasons.append(f"Purchase order {ctx.purchase_order_id} does not exist.")
        elif ctx.po_found is True:
            po = ctx.purchase_order or {}
            if po.get("vendor_id") != ctx.vendor_id:
                codes.append(ReasonCode.INVALID_PURCHASE_ORDER)
                reasons.append(
                    f"Purchase order {ctx.purchase_order_id} belongs to vendor {po.get('vendor_id')}."
                )
            elif (
                ctx.amount is None or abs(float(po.get("approved_amount", 0)) - ctx.amount) >= 0.005
            ):
                codes.append(ReasonCode.PO_AMOUNT_MISMATCH)
                reasons.append(
                    f"Invoice amount {ctx.amount} differs from PO amount {po.get('approved_amount')}."
                )
            else:
                po_matches = True
                reasons.append(f"Purchase order {ctx.purchase_order_id} matches vendor and amount.")
        self.record(
            ctx,
            EventType.PURCHASE_ORDER_CHECKED,
            Severity.LOW if po_matches else Severity.MEDIUM,
            reason_codes=[
                c
                for c in codes
                if c in (ReasonCode.INVALID_PURCHASE_ORDER, ReasonCode.PO_AMOUNT_MISMATCH)
            ],
            evidence_refs=evidence[-1:] if ctx.purchase_order_id else [],
            output_summary=f"po {ctx.purchase_order_id}: found={ctx.po_found} matches={po_matches}",
        )

        # --- duplicates ------------------------------------------------------
        duplicate_of = self._find_duplicate(ctx)
        if duplicate_of:
            ctx.duplicate_of = duplicate_of
            dup_evidence = f"DUP-CHECK-{self.gov.audit.count() + 1:03d}"
            self.record(
                ctx,
                EventType.DUPLICATE_DETECTED,
                Severity.HIGH,
                reason_codes=[ReasonCode.DUPLICATE_INVOICE],
                evidence_refs=[dup_evidence],
                output_summary=f"matches previously processed invoice {duplicate_of}",
            )
            evidence.append(dup_evidence)
            ctx.add_evidence(dup_evidence)
            codes.append(ReasonCode.DUPLICATE_INVOICE)
            reasons.append(
                f"This invoice duplicates {duplicate_of} (same vendor and invoice number or amount)."
            )

        if ctx.mock_unavailable:
            codes.append(ReasonCode.MOCK_SYSTEM_UNAVAILABLE)
            reasons.append(
                "An enterprise system was unavailable; verification could not be completed."
            )

        # --- summary (advisory) ---------------------------------------------
        findings: dict[str, Any] = {
            "vendor_found": ctx.vendor_found,
            "vendor_status": status,
            "po_found": ctx.po_found,
            "po_matches": po_matches,
            "duplicate_of": duplicate_of,
        }
        summary = self.ask(verification_summary_prompt(findings), SummaryOutput)
        if summary:
            reasons.append(summary.summary)

        decision = self._decision_label(codes, po_matches)
        # Confidence = share of the three checks that came back confirmed. A lookup that could
        # not run (system down, no vendor or PO on the invoice) is unconfirmed, not passed.
        confirmed = [
            ctx.vendor_found is True and status == "verified",
            po_matches,
            not duplicate_of,
        ]
        ctx.verification_confidence = round(sum(confirmed) / len(confirmed), 2)
        return self.decide(
            ctx,
            decision=decision,
            confidence=ctx.verification_confidence,
            evidence_ids=evidence,
            explanation=Explanation(
                decision=decision,
                reasons=reasons,
                evidence=evidence,
                recommended_next_step="evaluate policy and risk",
            ),
            reason_codes=codes,
        )

    # ------------------------------------------------------------------

    @staticmethod
    def _decision_label(codes: list[ReasonCode], po_matches: bool) -> str:
        if ReasonCode.MOCK_SYSTEM_UNAVAILABLE in codes:
            return "verification_unavailable"
        if ReasonCode.DUPLICATE_INVOICE in codes:
            return "duplicate_detected"
        if ReasonCode.UNKNOWN_VENDOR in codes:
            return "vendor_unknown"
        if ReasonCode.VENDOR_UNVERIFIED in codes:
            return "vendor_unverified"
        if ReasonCode.INVALID_PURCHASE_ORDER in codes:
            return "po_invalid"
        if ReasonCode.PO_AMOUNT_MISMATCH in codes:
            return "po_mismatch"
        return "vendor_verified" if po_matches else "verified_with_findings"

    def _find_duplicate(self, ctx: WorkflowContext) -> str | None:
        """Same vendor + (same vendor invoice number, or same amount within the window).

        The vendor is matched by ID when the invoice has one; otherwise by the normalized vendor
        name — a vendor not on the vendor list has no ID, and a new vendor sending the same
        invoice twice is exactly the case this check must catch."""
        vendor_name = normalize_vendor_name(ctx.vendor_name)
        if not ctx.vendor_id and not vendor_name:
            return None
        since = now_utc() - timedelta(days=DUPLICATE_WINDOW_DAYS)
        conditions = []
        if ctx.vendor_invoice_number:
            conditions.append(InvoiceRow.vendor_invoice_number == ctx.vendor_invoice_number)
        if ctx.amount is not None:
            conditions.append(and_(InvoiceRow.amount == ctx.amount, InvoiceRow.created_at >= since))
        if not conditions:
            return None
        stmt = (
            select(
                InvoiceRow.invoice_id,
                InvoiceRow.vendor_id,
                InvoiceRow.vendor_name,
                InvoiceRow.vendor_invoice_number,
            )
            .where(InvoiceRow.invoice_id != ctx.invoice_id, or_(*conditions))
            .order_by(InvoiceRow.created_at)
        )
        for invoice_id, other_id, other_name, other_number in self.gov.session.execute(stmt):
            same_vendor = (
                other_id == ctx.vendor_id
                if ctx.vendor_id and other_id
                else bool(vendor_name) and normalize_vendor_name(other_name) == vendor_name
            )
            if same_vendor:
                same_number = bool(ctx.vendor_invoice_number) and (
                    other_number == ctx.vendor_invoice_number
                )
                ctx.duplicate_match = "invoice_number" if same_number else "amount"
                return invoice_id
        return None
