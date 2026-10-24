"""Approval Agent — recommends approve / reject / escalate with a confidence score.

Allowed tool: approval_request_create (the governance engine creates the request during
finalize, so this agent normally needs no tool call). May never execute a payment.

The recommendation is derived deterministically from the policy result. The explanation shown
to the reviewer is written from the recorded evidence (explanations.py), not by the model; the
model only adds a note when it disagreed or was unsure. The model may only make the outcome
more cautious (approve → escalate), never more permissive.

Confidence = how sure the model is of the final recommendation, measured rather than asked: the
same question is put to it RECOMMENDATION_SAMPLES times with some randomness, and the score is
the share of answers that match the final approve / reject / escalate (4 of 5 → 80%). Invalid
answers count as disagreeing. The model's self-reported number is not the score (a local model
says 1.0 for everything); it can only make an "approve" more cautious.
"""

from collections import Counter

from backend.agents.base_agent import BaseAgent
from backend.agents.explanations import explain
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

# How the recommendation confidence is measured (see the module docstring). Not policy thresholds:
# five answers give 20% steps, and 0.7 lets an unsure model vary without turning to noise.
RECOMMENDATION_SAMPLES = 5
SAMPLE_TEMPERATURE = 0.7


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

        prompt = recommendation_prompt(
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
        )
        answers = [
            self.ask(prompt, RecommendationOutput, temperature=SAMPLE_TEMPERATURE)
            for _ in range(RECOMMENDATION_SAMPLES)
        ]
        valid = [a for a in answers if a is not None]

        if not valid:
            recommendation = Recommendation.ESCALATE
            notes = ["Model output was invalid; defaulting to escalate."]
        else:
            # The model's answer is its most common one across the samples.
            vote = Counter(a.recommendation for a in valid).most_common(1)[0][0]
            recommendation, notes = required, []
            if vote != required:
                if required == Recommendation.APPROVE:
                    recommendation = Recommendation.ESCALATE  # caution is always allowed
                notes.append(
                    f"Model suggested {vote.value}; policy requires {required.value}. "
                    f"Final recommendation: {recommendation.value}."
                )
            else:
                said = sum(a.confidence for a in valid if a.recommendation == vote) / sum(
                    1 for a in valid if a.recommendation == vote
                )
                if (
                    recommendation == Recommendation.APPROVE
                    and said < self.gov.policy.confidence_threshold
                ):
                    # Its self-report is not the score, but its doubt may still make the outcome
                    # more cautious — an unsure "approve" never auto-pays.
                    recommendation = Recommendation.ESCALATE
                    notes.append(
                        f"Model was unsure ({said:.0%}) about approving; "
                        "sent to a reviewer instead."
                    )

        # Share of all samples (invalid ones included) that back the final recommendation.
        agreeing = sum(1 for a in valid if a.recommendation == recommendation)
        confidence = round(agreeing / RECOMMENDATION_SAMPLES, 2)
        if valid and agreeing < len(answers):
            notes.append(
                f"Model gave this answer {agreeing} of {RECOMMENDATION_SAMPLES} times "
                f"({confidence:.0%} confidence)."
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

        reasons, next_step, missing = explain(ctx, self.gov.policy)
        explanation = self.gov.build_explanation(
            recommendation.value.capitalize(),
            policy,
            evidence,
            missing=missing,
            next_step=next_step,
        )
        explanation.reasons = reasons + notes
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
