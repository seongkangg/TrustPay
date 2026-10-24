"""Policy / Risk Agent — runs the deterministic policy matrix and assigns risk.

Allowed tools: approval_limit_lookup, risk_rules. May not approve payment or create
approval requests. The risk level comes from the governance engine; the model only
writes the reviewer-facing explanation sentence.
"""

from backend.agents.base_agent import BaseAgent
from backend.llm.output_parser import SummaryOutput
from backend.llm.prompts import risk_reasoning_prompt
from backend.models import AgentDecision, AgentName, ToolName
from backend.orchestration.workflow_context import WorkflowContext


class PolicyRiskAgent(BaseAgent):
    name = AgentName.POLICY_RISK

    def _run(self, ctx: WorkflowContext) -> AgentDecision:
        limit = self.request_tool(
            ctx,
            ToolName.APPROVAL_LIMIT_LOOKUP,
            "look up the approval agent's spending authority",
            agent_id=ctx.acting_agent.value,
        )
        rules = self.request_tool(
            ctx, ToolName.RISK_RULES, "load the deterministic policy rule set"
        )

        policy = self.gov.evaluate(
            ctx.to_policy_input(), invoice_id=ctx.invoice_id, correlation_id=ctx.correlation_id
        )
        ctx.policy = policy

        evidence = [e for e in (limit.call.evidence_id, rules.call.evidence_id) if e] + list(
            policy.rules_triggered
        )
        explanation = self.gov.build_explanation(
            f"risk_{policy.risk_level.value}",
            policy,
            evidence,
            missing=ctx.missing_fields,
            next_step="generate recommendation"
            if policy.auto_payment_allowed
            else "require human approval",
        )
        summary = self.ask(
            risk_reasoning_prompt(
                {
                    "risk_level": policy.risk_level.value,
                    "reason_codes": [c.value for c in policy.reason_codes],
                    "rules_triggered": policy.rules_triggered,
                    "agent_limit": (limit.result or {}).get("max_amount"),
                    "amount": ctx.amount,
                }
            ),
            SummaryOutput,
        )
        if summary:
            explanation.reasons.append(summary.summary)

        return self.decide(
            ctx,
            decision=f"risk_{policy.risk_level.value}",
            confidence=1.0,  # deterministic rules; model text is advisory
            evidence_ids=evidence,
            explanation=explanation,
            reason_codes=policy.reason_codes,
            risk_level=policy.risk_level,
        )
