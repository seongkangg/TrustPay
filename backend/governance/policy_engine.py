"""The governance policy matrix as code (docs/policy-matrix.md, POLICY-001…016).

Deterministic. No LLM. Every rule is evaluated; the highest resulting risk wins.
Thresholds and limits come from data/approval_limits.json via ReferenceData — nothing
here is hard-coded.

POLICY-014 (payment by an unauthorized actor) is enforced structurally by
`permission_checker`; it surfaces here through `unauthorized_tool_call`.
"""

from dataclasses import dataclass, field

from backend.models import AgentName, InvoiceStatus, ReasonCode, RiskLevel

_RISK_ORDER = {RiskLevel.LOW: 0, RiskLevel.MEDIUM: 1, RiskLevel.HIGH: 2}

PO_MISMATCH_HIGH_RATIO = 1.10  # invoice more than 10% over PO → high


@dataclass
class PolicyInput:
    """Everything the matrix needs, gathered by the agents through governed tool calls.

    `None` on a lookup field means the lookup did not happen (or failed) — the engine
    treats missing evidence as a reason to escalate, never as a pass.
    """

    amount: float | None
    currency: str = "USD"
    acting_agent: AgentName = AgentName.APPROVAL
    invoice_vendor_id: str | None = None

    vendor_found: bool | None = None
    vendor_status: str | None = None

    po_found: bool | None = None
    po_vendor_id: str | None = None
    po_amount: float | None = None

    duplicate_of: str | None = None
    sensitive_detected: bool = False
    missing_fields: list[str] = field(default_factory=list)
    malformed_fields: list[str] = field(default_factory=list)
    min_confidence: float | None = None

    unauthorized_tool_call: bool = False
    agent_failure: bool = False
    mock_unavailable: bool = False


@dataclass(frozen=True)
class RuleHit:
    rule_id: str
    reason_code: ReasonCode
    risk: RiskLevel
    action: str
    detail: str


@dataclass
class PolicyResult:
    risk_level: RiskLevel
    reason_codes: list[ReasonCode]
    rules_triggered: list[str]
    hits: list[RuleHit]
    action: str
    target_status: InvoiceStatus
    auto_payment_allowed: bool

    @property
    def requires_human(self) -> bool:
        return not self.auto_payment_allowed


RULE_DESCRIPTIONS: dict[str, str] = {
    "POLICY-001": "Verified vendor and matching PO → permit recommendation",
    "POLICY-002": "Amount at or below auto-approve threshold → allow automatic processing",
    "POLICY-003": "Amount above acting agent's approval limit → block, request approval",
    "POLICY-004": "Unknown vendor → escalate for a human to confirm the supplier",
    "POLICY-005": "Vendor not verified → escalate for review",
    "POLICY-006": "Duplicate invoice → block, recommend reject, escalate",
    "POLICY-007": "Purchase order missing or belongs to another vendor → block, escalate",
    "POLICY-008": "PO amount differs from invoice amount → escalate (high if >10% over)",
    "POLICY-009": "Sensitive data detected → mask and log (high if vendor unknown)",
    "POLICY-010": "Unauthorized tool call → block, record violation",
    "POLICY-011": "Missing required invoice field → escalate",
    "POLICY-012": "Malformed invoice field → escalate",
    "POLICY-013": "Agent confidence below threshold → require human review",
    "POLICY-014": "Payment requested by unauthorized actor → block immediately",
    "POLICY-015": "Agent failure → mark FAILED, escalate",
    "POLICY-016": "Enterprise system unavailable → stop, escalate",
    "DEFAULT-SAFETY": "Evidence missing or authorization unclear → stop and escalate",
}


class PolicyEngine:
    def __init__(self, thresholds: dict, approval_limits: dict):
        self.auto_approve_max = float(thresholds["auto_approve_max_amount"])
        self.confidence_threshold = float(thresholds["confidence_threshold"])
        self.approval_limits = approval_limits

    def describe_rules(self) -> list[dict[str, str]]:
        return [{"rule_id": k, "description": v} for k, v in RULE_DESCRIPTIONS.items()]

    def limit_for(self, agent: AgentName) -> float:
        entry = self.approval_limits.get(AgentName(agent).value)
        return float(entry["max_amount"]) if entry else 0.0

    # ------------------------------------------------------------------

    def evaluate(self, inp: PolicyInput) -> PolicyResult:
        hits: list[RuleHit] = []

        def hit(rule_id: str, code: ReasonCode, risk: RiskLevel, action: str, detail: str) -> None:
            hits.append(RuleHit(rule_id, code, risk, action, detail))

        vendor_verified = inp.vendor_found is True and inp.vendor_status == "verified"
        po_matches_vendor = (
            inp.po_found is True
            and inp.po_vendor_id is not None
            and inp.po_vendor_id == inp.invoice_vendor_id
        )
        po_amount_matches = (
            inp.po_found is True
            and inp.po_amount is not None
            and inp.amount is not None
            and abs(inp.po_amount - inp.amount) < 0.005
        )

        # --- permits -------------------------------------------------------
        if vendor_verified and po_matches_vendor and po_amount_matches:
            hit(
                "POLICY-001",
                ReasonCode.POLICY_PASSED,
                RiskLevel.LOW,
                "permit",
                "vendor verified, PO matches",
            )
        if inp.amount is not None and inp.amount <= self.auto_approve_max:
            hit(
                "POLICY-002",
                ReasonCode.POLICY_PASSED,
                RiskLevel.LOW,
                "permit",
                f"amount {inp.amount} ≤ auto-approve max {self.auto_approve_max}",
            )

        # --- blocks / escalations -----------------------------------------
        limit = self.limit_for(inp.acting_agent)
        if inp.amount is not None and inp.amount > limit:
            hit(
                "POLICY-003",
                ReasonCode.AMOUNT_ABOVE_LIMIT,
                RiskLevel.HIGH,
                "block_and_request_approval",
                f"amount {inp.amount} > {inp.acting_agent.value} limit {limit}",
            )
        if inp.vendor_found is False:
            # A new vendor is a reason to check, not to block: legitimate first-time suppliers are
            # common. Never auto-paid (medium escalates to a human). Combined with bank details
            # (POLICY-009) or any other high rule it still blocks.
            hit(
                "POLICY-004",
                ReasonCode.UNKNOWN_VENDOR,
                RiskLevel.MEDIUM,
                "escalate",
                "vendor not in vendor master — confirm this is a real supplier",
            )
        elif inp.vendor_found is True and not vendor_verified:
            hit(
                "POLICY-005",
                ReasonCode.VENDOR_UNVERIFIED,
                RiskLevel.MEDIUM,
                "escalate",
                f"vendor status is {inp.vendor_status}",
            )
        if inp.duplicate_of:
            hit(
                "POLICY-006",
                ReasonCode.DUPLICATE_INVOICE,
                RiskLevel.HIGH,
                "block_and_escalate",
                f"duplicate of {inp.duplicate_of}",
            )
        if inp.po_found is False or (inp.po_found is True and not po_matches_vendor):
            hit(
                "POLICY-007",
                ReasonCode.INVALID_PURCHASE_ORDER,
                RiskLevel.HIGH,
                "block_and_escalate",
                "PO not found" if inp.po_found is False else "PO belongs to a different vendor",
            )
        elif (
            inp.po_found is True
            and not po_amount_matches
            and inp.amount is not None
            and inp.po_amount is not None
        ):
            over = inp.amount > inp.po_amount * PO_MISMATCH_HIGH_RATIO
            hit(
                "POLICY-008",
                ReasonCode.PO_AMOUNT_MISMATCH,
                RiskLevel.HIGH if over else RiskLevel.MEDIUM,
                "escalate",
                f"invoice {inp.amount} vs PO {inp.po_amount}",
            )
        if inp.sensitive_detected:
            hit(
                "POLICY-009",
                ReasonCode.SENSITIVE_DATA_DETECTED,
                RiskLevel.HIGH if inp.vendor_found is False else RiskLevel.MEDIUM,
                "mask_and_log",
                "sensitive data was detected and masked",
            )
        if inp.unauthorized_tool_call:
            hit(
                "POLICY-010",
                ReasonCode.UNAUTHORIZED_TOOL_CALL,
                RiskLevel.HIGH,
                "block_and_escalate",
                "an agent attempted an unauthorized tool call",
            )
        if inp.missing_fields:
            hit(
                "POLICY-011",
                ReasonCode.MISSING_REQUIRED_FIELD,
                RiskLevel.MEDIUM,
                "escalate",
                "missing: " + ", ".join(inp.missing_fields),
            )
        if inp.malformed_fields:
            hit(
                "POLICY-012",
                ReasonCode.MALFORMED_FIELD,
                RiskLevel.MEDIUM,
                "escalate",
                "malformed: " + ", ".join(inp.malformed_fields),
            )
        if inp.min_confidence is not None and inp.min_confidence < self.confidence_threshold:
            hit(
                "POLICY-013",
                ReasonCode.LOW_CONFIDENCE,
                RiskLevel.MEDIUM,
                "require_human_review",
                f"confidence {inp.min_confidence} < {self.confidence_threshold}",
            )
        if inp.agent_failure:
            hit(
                "POLICY-015",
                ReasonCode.AGENT_FAILURE,
                RiskLevel.MEDIUM,
                "fail_and_escalate",
                "an agent failed",
            )
        if inp.mock_unavailable:
            hit(
                "POLICY-016",
                ReasonCode.MOCK_SYSTEM_UNAVAILABLE,
                RiskLevel.MEDIUM,
                "escalate",
                "an enterprise system was unavailable",
            )

        # --- default safety: no positive evidence and nothing else fired → escalate
        if not any(h.rule_id == "POLICY-001" for h in hits) and all(
            h.risk == RiskLevel.LOW for h in hits
        ):
            hit(
                "DEFAULT-SAFETY",
                ReasonCode.INSUFFICIENT_EVIDENCE,
                RiskLevel.MEDIUM,
                "escalate",
                "vendor/PO verification evidence is incomplete",
            )

        return self._resolve(hits)

    # ------------------------------------------------------------------

    def _resolve(self, hits: list[RuleHit]) -> PolicyResult:
        risk = max((h.risk for h in hits), key=_RISK_ORDER.__getitem__, default=RiskLevel.MEDIUM)

        if risk == RiskLevel.LOW:
            relevant = hits
        else:
            relevant = [h for h in hits if h.risk != RiskLevel.LOW]  # drop POLICY_PASSED noise

        reason_codes: list[ReasonCode] = []
        for h in relevant:
            if h.reason_code not in reason_codes:
                reason_codes.append(h.reason_code)
        rules = [h.rule_id for h in relevant]

        if risk == RiskLevel.LOW:
            action, status, auto = "permit", InvoiceStatus.APPROVED, True
        elif risk == RiskLevel.MEDIUM:
            action, status, auto = "escalate", InvoiceStatus.PENDING_APPROVAL, False
        elif reason_codes == [ReasonCode.AMOUNT_ABOVE_LIMIT]:
            action, status, auto = (
                "block_and_request_approval",
                InvoiceStatus.PENDING_APPROVAL,
                False,
            )
        else:
            action, status, auto = "block_and_escalate", InvoiceStatus.BLOCKED, False

        return PolicyResult(
            risk_level=risk,
            reason_codes=reason_codes,
            rules_triggered=rules,
            hits=relevant,
            action=action,
            target_status=status,
            auto_payment_allowed=auto,
        )
