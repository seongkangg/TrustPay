"""Approval Agent — recommends approve / reject / escalate with a confidence score.

Allowed tool: approval_request_create (the governance engine creates the request during
finalize, so this agent normally needs no tool call). May never execute a payment.

The recommendation is derived deterministically from the policy result; the model supplies
the reasons and next step. Confidence is evidence-based (the lower of the Reading and
Verification scores), never the model's self-report. The model may only make the outcome
more cautious (approve → escalate), never more permissive.
"""

from backend.agents.base_agent import BaseAgent
from backend.llm.output_parser import RecommendationOutput
from backend.llm.prompts import recommendation_prompt
from backend.models import (
    AgentDecision,
    AgentName,
    EventType,
    ReasonCode,
    Recommendation,
    RiskLevel,
    Severity,
)
from backend.orchestration.workflow_context import WorkflowContext

_SEVERITY = {
    RiskLevel.LOW: Severity.LOW,
    RiskLevel.MEDIUM: Severity.MEDIUM,
    RiskLevel.HIGH: Severity.HIGH,
}


def deterministic_recommendation(ctx: WorkflowContext) -> Recommendation:
    policy = ctx.policy
    assert policy is not None
    if ReasonCode.DUPLICATE_INVOICE in policy.reason_codes:
        return Recommendation.REJECT
    if policy.auto_payment_allowed:
        return Recommendation.APPROVE
    return Recommendation.ESCALATE


class ApprovalAgent(BaseAgent):
    name = AgentName.APPROVAL

    def _run(self, ctx: WorkflowContext) -> AgentDecision:
        if ctx.policy is None:
            raise RuntimeError("policy evaluation missing; cannot recommend")
        policy = ctx.policy
        required = deterministic_recommendation(ctx)

        model = self.ask(
            recommendation_prompt(
                {
                    "risk_level": policy.risk_level.value,
                    "reason_codes": [c.value for c in policy.reason_codes],
                    "rules_triggered": policy.rules_triggered,
                    "amount": ctx.amount,
                    "currency": ctx.currency,
                    "vendor_status": (ctx.vendor or {}).get("verification_status"),
                    "duplicate_of": ctx.duplicate_of,
                    "sensitive_detected": ctx.sensitive_detected,
                }
            ),
            RecommendationOutput,
        )

        # Confidence in the recommendation = how much of the invoice is backed by evidence: the
        # lower of the Reading and Verification scores. The model's self-reported confidence is
        # not used (a local model reports 1.0 for everything).
        steps = [c for c in (ctx.reading_confidence, ctx.verification_confidence) if c is not None]
        confidence = min(steps) if steps else 0.0

        if model is None:
            recommendation = Recommendation.ESCALATE
            reasons = ["Model output was invalid; defaulting to escalate."]
            next_step = "route to a finance reviewer"
        else:
            recommendation, reasons, next_step = (
                required,
                list(model.reasons),
                model.next_step,
            )
            if model.recommendation != required:
                if required == Recommendation.APPROVE:
                    recommendation = Recommendation.ESCALATE  # caution is always allowed
                reasons.append(
                    f"Model suggested {model.recommendation.value}; policy requires {required.value}. "
                    f"Final recommendation: {recommendation.value}."
                )
            elif (
                recommendation == Recommendation.APPROVE
                and model.confidence < self.gov.policy.confidence_threshold
            ):
                # The model's self-report is not shown as confidence, but its doubt may still make
                # the outcome more cautious — an unsure "approve" never auto-pays.
                recommendation = Recommendation.ESCALATE
                reasons.append(
                    f"Model was unsure ({model.confidence:.0%}) about approving; "
                    "sent to a reviewer instead."
                )

        ctx.recommendation = recommendation
        ctx.recommendation_confidence = confidence

        evidence = list(ctx.evidence_ids) + [
            r for r in policy.rules_triggered if r not in ctx.evidence_ids
        ]
        self.record(
            ctx,
            EventType.RECOMMENDATION_GENERATED,
            _SEVERITY[policy.risk_level],
            reason_codes=policy.reason_codes,
            output_summary=f"recommendation={recommendation.value} confidence={confidence:.2f}",
            evidence_refs=evidence,
        )

        explanation = self.gov.build_explanation(
            recommendation.value.capitalize(), policy, evidence, next_step=next_step
        )
        explanation.reasons = reasons + explanation.reasons
        return self.decide(
            ctx,
            decision=f"recommend_{recommendation.value}",
            confidence=confidence,
            evidence_ids=evidence,
            explanation=explanation,
            reason_codes=policy.reason_codes,
            risk_level=policy.risk_level,
            recommendation=recommendation,
        )
