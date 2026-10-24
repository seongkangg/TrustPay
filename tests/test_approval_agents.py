"""Policy/Risk Agent and Approval Agent (acceptance B3, B4), plus the four-agent chain over
every demo fixture — the agent-level half of test_scenarios (the HTTP half lands in Sprint 4)."""

import pytest

from backend.governance import GovernanceEngine
from backend.models import AgentName, Authorization, EventType, Recommendation, RiskLevel, ToolName
from tests.conftest import insert_invoice_row, run_agents


class BrokenLLM:
    mode = "broken"

    def complete(self, prompt: str) -> str:
        return '{"recommendation": "approve"'  # truncated JSON


class PermissiveLLM:
    """A model that always says approve — must never make the outcome more permissive."""

    mode = "permissive"

    def complete(self, prompt: str) -> str:
        if "<schema>recommendation</schema>" in prompt:
            return '{"recommendation": "approve", "confidence": 0.99, "reasons": ["looks fine"], "next_step": "pay"}'
        return (
            '{"summary": "fine", "confidence": 0.99}'
            if "<schema>summary</schema>" in prompt
            else '{"fields": [{"field": "amount", "value": "1", "confidence": 0.99}], "notes": ""}'
        )


@pytest.fixture
def gov(session, ref):
    return GovernanceEngine(session, ref)


def by_agent(ctx, agent):
    return next(d for d in ctx.decisions if d.agent == agent)


# --- policy/risk agent -----------------------------------------------------


def test_policy_agent_assigns_risk_from_engine(gov, fixture_by_id):
    ctx = run_agents(gov, fixture_by_id("INV-1002"), upto=3)
    d = by_agent(ctx, AgentName.POLICY_RISK)
    assert d.decision == "risk_high" and d.risk_level == RiskLevel.HIGH
    assert d.confidence == 1.0 and d.governance_result == Authorization.ALLOWED
    assert "POLICY-003" in d.explanation.policy_rules_triggered
    assert {"LIMIT-LOOKUP-001", "RULES-001", "POLICY-003"} <= set(d.evidence_ids)
    assert ctx.policy is not None and ctx.policy.risk_level == RiskLevel.HIGH
    tools = {
        c.tool for c in gov.interceptor.calls_for("INV-1002") if c.agent == AgentName.POLICY_RISK
    }
    assert tools == {ToolName.APPROVAL_LIMIT_LOOKUP, ToolName.RISK_RULES}
    assert EventType.RISK_ASSIGNED in [e.event_type for e in gov.audit.list_for_invoice("INV-1002")]


# --- approval agent --------------------------------------------------------


def test_approval_agent_recommends_from_policy(gov, fixture_by_id):
    ctx = run_agents(gov, fixture_by_id("INV-1001"))
    d = by_agent(ctx, AgentName.APPROVAL)
    assert d.recommendation == Recommendation.APPROVE and d.decision == "recommend_approve"
    assert d.confidence >= 0.75 and d.governance_result == Authorization.ALLOWED
    assert d.explanation.decision == "Approve" and d.explanation.recommended_next_step
    assert ctx.recommendation == Recommendation.APPROVE
    assert [e.event_type for e in gov.audit.list_for_invoice("INV-1001")][
        -1
    ] == EventType.RECOMMENDATION_GENERATED


def test_approval_agent_never_calls_payment(gov, fixture_by_id):
    ctx = run_agents(gov, fixture_by_id("INV-1001"))
    calls = gov.interceptor.calls_for(ctx.invoice_id)
    assert all(c.tool != ToolName.PAYMENT_AUTHORIZE for c in calls)
    assert gov.payments.get_payment(ctx.invoice_id) is None


def test_model_cannot_make_outcome_more_permissive(gov, fixture_by_id):
    ctx = run_agents(gov, fixture_by_id("INV-1002"), llm=PermissiveLLM())
    d = by_agent(ctx, AgentName.APPROVAL)
    assert (
        d.recommendation == Recommendation.ESCALATE
    )  # policy says high → escalate, model overruled
    assert any("policy requires escalate" in r for r in d.explanation.reasons)


def test_model_may_make_outcome_more_cautious(gov, fixture_by_id):
    class CautiousLLM(PermissiveLLM):
        def complete(self, prompt):
            if "<schema>recommendation</schema>" in prompt:
                return '{"recommendation": "escalate", "confidence": 0.8, "reasons": ["unsure"], "next_step": "review"}'
            return super().complete(prompt)

    ctx = run_agents(gov, fixture_by_id("INV-1001"), llm=CautiousLLM())
    assert by_agent(ctx, AgentName.APPROVAL).recommendation == Recommendation.ESCALATE


def test_invalid_model_output_defaults_to_escalate(gov, fixture_by_id):
    ctx = run_agents(gov, fixture_by_id("INV-1001"), upto=3)
    from backend.agents import ApprovalAgent

    d = ApprovalAgent(gov, BrokenLLM()).run(ctx)
    assert d.recommendation == Recommendation.ESCALATE
    # confidence is evidence-based (exact fields 98%, all checks confirmed), not the model's
    assert d.confidence == 0.98
    assert any("invalid" in r for r in d.explanation.reasons)


# --- all four fixtures through the agent chain -----------------------------


def test_every_fixture_reaches_expected_recommendation(gov, fixture_by_id, demo_invoices, session):
    insert_invoice_row(session, fixture_by_id("INV-1001"))  # so INV-1004 is a duplicate
    for fx in demo_invoices:
        exp = fx["expected"]
        ctx = run_agents(gov, fx)
        assert len(ctx.decisions) == 4, exp["invoice_id"]
        assert all(d.governance_result == Authorization.ALLOWED for d in ctx.decisions), exp[
            "invoice_id"
        ]
        assert ctx.policy.risk_level == RiskLevel(exp["risk_level"]), exp["invoice_id"]
        assert {c.value for c in ctx.policy.reason_codes} == set(exp["reason_codes"]), exp[
            "invoice_id"
        ]
        assert ctx.recommendation == Recommendation(exp["recommendation"]), exp["invoice_id"]
        assert ctx.sensitive_detected == exp["sensitive_data_detected"], exp["invoice_id"]
        assert gov.audit.get_trail(exp["invoice_id"]).chain_valid
        # every decision cites only evidence that resolves
        known = gov.known_evidence(exp["invoice_id"])
        for d in ctx.decisions:
            assert all(e in known or e.startswith("POLICY-") for e in d.evidence_ids), (
                exp["invoice_id"],
                d.agent,
            )


def test_agent_event_sequence_matches_fixture(gov, fixture_by_id):
    """Agent-emitted events appear in the fixture's order (service-level events come in Sprint 4)."""
    ctx = run_agents(gov, fixture_by_id("INV-1003"))
    emitted = [e.event_type.value for e in gov.audit.list_for_invoice(ctx.invoice_id)]
    expected = fixture_by_id("INV-1003")["expected"]["audit_event_sequence"]
    agent_level = [e for e in expected if e in emitted]
    assert [e for e in emitted if e in agent_level] == agent_level
    assert emitted[0] == "sensitive_data_masked"
