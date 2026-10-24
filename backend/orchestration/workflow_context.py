"""Mutable per-invoice context handed from agent to agent.

Holds the masked upload, what each agent found, every evidence ID gathered so far,
and the policy result once assigned. Agents read from it and add to it; nothing here
talks to a tool or a database.
"""

from dataclasses import dataclass, field
from typing import Any

from backend.governance.policy_engine import PolicyInput, PolicyResult
from backend.governance.sensitive_data_scanner import ScanResult
from backend.models import AgentDecision, AgentName, ExtractedField, Recommendation


@dataclass
class WorkflowContext:
    invoice_id: str
    correlation_id: str
    upload: dict[str, Any]  # already masked by GovernanceEngine.ingest
    sensitive_detected: bool = False
    scan_evidence_id: str | None = None
    acting_agent: AgentName = AgentName.APPROVAL

    # How each field was obtained, set by the email intake: "model" (read by the LLM and found in
    # the document), "default" (filled in, e.g. currency), "placeholder" (unreadable, e.g. the
    # EMAIL-… invoice number). Fields not listed were exact (labelled line or structured upload).
    field_sources: dict[str, str] = field(default_factory=dict)

    # intake
    extracted: dict[str, Any] = field(default_factory=dict)
    extraction: list[ExtractedField] = field(default_factory=list)
    missing_fields: list[str] = field(default_factory=list)
    malformed_fields: list[str] = field(default_factory=list)

    # verification
    vendor: dict[str, Any] | None = None
    vendor_found: bool | None = None
    purchase_order: dict[str, Any] | None = None
    po_found: bool | None = None
    duplicate_of: str | None = None
    duplicate_match: str | None = None  # "invoice_number" or "amount": what the duplicate shared

    # governance flags (set by BaseAgent.request_tool / run)
    mock_unavailable: bool = False
    unauthorized_tool_call: bool = False
    agent_failure: bool = False

    # accumulated
    decisions: list[AgentDecision] = field(default_factory=list)
    evidence_ids: list[str] = field(default_factory=list)
    policy: PolicyResult | None = None
    recommendation: Recommendation | None = None
    recommendation_confidence: float | None = None

    # Evidence-based confidence per step (not the model's opinion of itself)
    reading_confidence: float | None = None  # how reliably the invoice's fields were read
    verification_confidence: float | None = (
        None  # share of vendor / PO / duplicate checks confirmed
    )

    # ------------------------------------------------------------------

    @classmethod
    def from_scan(
        cls, scan: ScanResult, *, invoice_id: str, correlation_id: str
    ) -> "WorkflowContext":
        ctx = cls(invoice_id=invoice_id, correlation_id=correlation_id, upload=scan.masked)
        ctx.sensitive_detected = scan.found
        ctx.scan_evidence_id = scan.evidence_id
        if scan.evidence_id:
            ctx.add_evidence(scan.evidence_id)
        return ctx

    def add_evidence(self, *ids: str | None) -> None:
        for ref in ids:
            if ref and ref not in self.evidence_ids:
                self.evidence_ids.append(ref)

    def _field(self, name: str) -> Any:
        return self.extracted.get(name, self.upload.get(name))

    @property
    def amount(self) -> float | None:
        value = self._field("amount")
        try:
            return float(value) if value is not None else None
        except (TypeError, ValueError):
            return None

    @property
    def currency(self) -> str:
        return str(self._field("currency") or "USD")

    @property
    def vendor_id(self) -> str | None:
        return self._field("vendor_id")

    @property
    def vendor_name(self) -> str | None:
        return self._field("vendor_name")

    @property
    def vendor_ref(self) -> str:
        """How to name the vendor in messages: its ID, else the name on the invoice."""
        return self.vendor_id or (
            f"'{self.vendor_name}'" if self.vendor_name else "(none on invoice)"
        )

    @property
    def vendor_invoice_number(self) -> str | None:
        return self._field("vendor_invoice_number")

    @property
    def purchase_order_id(self) -> str | None:
        return self._field("purchase_order_id")

    @property
    def min_confidence(self) -> float | None:
        """The confidence POLICY-013 (LOW_CONFIDENCE, "Unclear details") checks: how reliably the
        invoice was *read*. An unconfirmed vendor or PO is reported by its own rule, not here."""
        return self.reading_confidence

    def to_policy_input(self) -> PolicyInput:
        return PolicyInput(
            amount=self.amount,
            currency=self.currency,
            acting_agent=self.acting_agent,
            invoice_vendor_id=self.vendor_id,
            vendor_found=self.vendor_found,
            vendor_status=(self.vendor or {}).get("verification_status"),
            po_found=self.po_found,
            po_vendor_id=(self.purchase_order or {}).get("vendor_id"),
            po_amount=(self.purchase_order or {}).get("approved_amount"),
            duplicate_of=self.duplicate_of,
            sensitive_detected=self.sensitive_detected,
            missing_fields=list(self.missing_fields),
            malformed_fields=list(self.malformed_fields),
            min_confidence=self.min_confidence,
            unauthorized_tool_call=self.unauthorized_tool_call,
            agent_failure=self.agent_failure,
            mock_unavailable=self.mock_unavailable,
        )
