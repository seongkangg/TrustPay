"""Intake Agent (acceptance B1)."""

import pytest

from backend.agents import IntakeAgent
from backend.governance import GovernanceEngine
from backend.models import AgentName, Authorization, EventType, ReasonCode, ToolName
from backend.orchestration.workflow_context import WorkflowContext
from tests.conftest import run_agents


class BrokenLLM:
    mode = "broken"

    def complete(self, prompt: str, *, temperature: float = 0.0) -> str:
        return "I'm sorry, I can't help with that."


@pytest.fixture
def gov(session, ref):
    return GovernanceEngine(session, ref)


def test_extracts_fields_with_confidence(gov, fixture_by_id):
    ctx = run_agents(gov, fixture_by_id("INV-1001"), upto=1)
    decision = ctx.decisions[0]
    assert decision.agent == AgentName.INTAKE and decision.decision == "fields_extracted"
    assert decision.confidence >= 0.9 and decision.governance_result == Authorization.ALLOWED
    assert decision.evidence_ids == ["PARSE-001"]
    assert ctx.extracted["vendor_id"] == "V-101" and ctx.amount == 4250.0
    assert not ctx.missing_fields and not ctx.malformed_fields
    by_name = {f.field: f for f in ctx.extraction}
    assert by_name["amount"].confidence > 0.9 and by_name["bank_account"].missing
    assert [e.event_type for e in gov.audit.list_for_invoice("INV-1001")] == [
        EventType.INVOICE_EXTRACTED
    ]


def test_only_tool_is_document_parser(gov, fixture_by_id):
    ctx = run_agents(gov, fixture_by_id("INV-1001"), upto=1)
    calls = gov.interceptor.calls_for(ctx.invoice_id)
    assert [c.tool for c in calls] == [ToolName.DOCUMENT_PARSER]
    assert all(c.agent == AgentName.INTAKE for c in calls)


def test_sensitive_fields_are_masked_before_the_agent_sees_them(gov, fixture_by_id):
    ctx = run_agents(gov, fixture_by_id("INV-1003"), upto=1)
    assert ctx.extracted["bank_account"] == "****6789"
    assert ctx.sensitive_detected and "SCAN-001" in ctx.decisions[0].evidence_ids
    parser_call = gov.interceptor.calls_for("INV-1003")[0]
    assert "987654326789" not in str(parser_call.parameters)


def test_flags_missing_due_date_and_malformed_amount(gov, fixture_by_id):
    fx = fixture_by_id("INV-1001")
    upload = {**fx["upload"], "due_date": None, "amount": -5}
    scan = gov.ingest(upload, invoice_id="INV-2001", correlation_id="c")
    ctx = WorkflowContext.from_scan(scan, invoice_id="INV-2001", correlation_id="c")
    decision = IntakeAgent(gov).run(ctx)
    assert "due_date" in ctx.missing_fields and "amount" in ctx.malformed_fields
    assert set(decision.reason_codes) == {
        ReasonCode.MISSING_REQUIRED_FIELD,
        ReasonCode.MALFORMED_FIELD,
    }
    assert (
        decision.confidence == 0.0
    )  # the malformed amount counts as 0 (missing due date does not)
    assert decision.governance_result == Authorization.ESCALATED  # low confidence → human review
    assert "due_date" in decision.explanation.missing_information


def test_malformed_model_output_becomes_agent_failure(gov, fixture_by_id):
    ctx = run_agents(gov, fixture_by_id("INV-1001"), llm=BrokenLLM(), upto=1)
    decision = ctx.decisions[0]
    assert decision.decision == "agent_failed" and ctx.agent_failure
    assert ReasonCode.AGENT_FAILURE in decision.reason_codes
    assert EventType.AGENT_FAILED in [e.event_type for e in gov.audit.list_for_invoice("INV-1001")]
    assert gov.audit.get_trail("INV-1001").chain_valid
