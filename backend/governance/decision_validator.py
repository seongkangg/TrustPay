"""Validates an AgentDecision before the governance layer accepts it (spec §10, §20).

Rejects:
- decisions with no evidence, or evidence IDs that do not resolve to a recorded tool call,
  scan, or policy rule (an AI explanation is never evidence by itself)
- unmasked sensitive values anywhere in the decision text
- role violations (policy agent without a risk level, approval agent without a recommendation)

Flags (but does not reject) a Reading (intake) confidence below the threshold → LOW_CONFIDENCE.
"""

import re
from dataclasses import dataclass, field
from typing import Any

from pydantic import ValidationError

from backend.models import AgentDecision, AgentName, ReasonCode
from backend.services.masking_service import contains_unmasked

POLICY_RULE_ID = re.compile(r"^(POLICY-\d{3}|DEFAULT-SAFETY)$")


@dataclass
class ValidationResult:
    valid: bool
    low_confidence: bool = False
    reason_codes: list[ReasonCode] = field(default_factory=list)
    problems: list[str] = field(default_factory=list)


def parse_decision(raw: Any) -> AgentDecision | None:
    """Structured-output guardrail: anything that does not match the schema is rejected."""
    if not isinstance(raw, dict):
        return None
    try:
        return AgentDecision.model_validate(raw)
    except ValidationError:
        return None


def validate_decision(
    decision: AgentDecision,
    known_evidence: set[str],
    confidence_threshold: float,
) -> ValidationResult:
    problems: list[str] = []
    codes: list[ReasonCode] = []

    def _resolves(ref: str) -> bool:
        return ref in known_evidence or bool(POLICY_RULE_ID.match(ref))

    # 1. Evidence must exist and resolve.
    if not decision.evidence_ids:
        problems.append("decision cites no evidence")
    for ref in decision.evidence_ids:
        if not _resolves(ref):
            problems.append(
                f"evidence {ref} does not resolve to a recorded tool call, scan, or rule"
            )
    for ref in decision.explanation.evidence:
        if not _resolves(ref):
            problems.append(f"explanation cites unknown evidence {ref}")
    for rule in decision.explanation.policy_rules_triggered:
        if not POLICY_RULE_ID.match(rule):
            problems.append(f"unknown policy rule {rule}")

    # 2. No raw sensitive data in any free text.
    texts = [
        decision.decision,
        decision.explanation.decision,
        decision.explanation.recommended_next_step,
        *decision.explanation.reasons,
        *decision.explanation.missing_information,
    ]
    if any(contains_unmasked(t) for t in texts):
        problems.append("decision text contains unmasked sensitive data")
        codes.append(ReasonCode.SENSITIVE_DATA_DETECTED)

    # 3. Role requirements.
    if decision.agent == AgentName.POLICY_RISK and decision.risk_level is None:
        problems.append("policy/risk decision has no risk_level")
    if decision.agent == AgentName.APPROVAL and decision.recommendation is None:
        problems.append("approval decision has no recommendation")

    valid = not problems
    if not valid:
        codes.insert(0, ReasonCode.AGENT_FAILURE)

    # 4. Confidence is advisory: flag, never reject. Only the Reading (intake) confidence means
    # "unclear details"; a low Verification score is an unconfirmed vendor / PO / duplicate check,
    # each already flagged by its own reason code.
    low = decision.agent == AgentName.INTAKE and decision.confidence < confidence_threshold
    if low:
        codes.append(ReasonCode.LOW_CONFIDENCE)

    return ValidationResult(valid=valid, low_confidence=low, reason_codes=codes, problems=problems)
