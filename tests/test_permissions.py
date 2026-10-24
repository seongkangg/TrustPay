"""Agent → tool allowlist (docs/agent-permissions.md; acceptance A8)."""

import pytest
from pydantic import ValidationError

from backend.governance.permission_checker import ALLOWLIST, WRITE_TOOLS, check_permission, is_write
from backend.models import (
    AgentName,
    Authorization,
    ReasonCode,
    RiskLevel,
    ToolCallRequest,
    ToolName,
)


def req(agent, tool, purpose="verify the vendor record", **params):
    return ToolCallRequest(
        agent=agent,
        tool=tool,
        purpose=purpose,
        parameters=params,
        invoice_id="INV-1001",
        correlation_id="c",
    )


def test_allowlist_matches_the_permissions_doc():
    assert ALLOWLIST[AgentName.INTAKE] == {ToolName.DOCUMENT_PARSER}
    assert ALLOWLIST[AgentName.VERIFICATION] == {ToolName.VENDOR_LOOKUP, ToolName.PO_LOOKUP}
    assert ALLOWLIST[AgentName.POLICY_RISK] == {ToolName.APPROVAL_LIMIT_LOOKUP, ToolName.RISK_RULES}
    assert ALLOWLIST[AgentName.APPROVAL] == {ToolName.APPROVAL_REQUEST_CREATE}
    assert ToolName.PAYMENT_AUTHORIZE in ALLOWLIST[AgentName.GOVERNANCE]
    assert ToolName.PAYMENT_AUTHORIZE in ALLOWLIST[AgentName.HUMAN_REVIEWER]
    assert WRITE_TOOLS == {
        ToolName.APPROVAL_REQUEST_CREATE,
        ToolName.PAYMENT_AUTHORIZE,
        ToolName.AUDIT_LOG_WRITE,
    }


@pytest.mark.parametrize(
    "agent,tool",
    [
        (AgentName.INTAKE, ToolName.DOCUMENT_PARSER),
        (AgentName.VERIFICATION, ToolName.VENDOR_LOOKUP),
        (AgentName.VERIFICATION, ToolName.PO_LOOKUP),
        (AgentName.POLICY_RISK, ToolName.APPROVAL_LIMIT_LOOKUP),
        (AgentName.POLICY_RISK, ToolName.RISK_RULES),
    ],
)
def test_allowlisted_read_calls_pass(agent, tool):
    assert check_permission(req(agent, tool)).allowed


@pytest.mark.parametrize(
    "agent,tool",
    [
        (AgentName.INTAKE, ToolName.VENDOR_LOOKUP),
        (AgentName.VERIFICATION, ToolName.APPROVAL_LIMIT_LOOKUP),
        (AgentName.VERIFICATION, ToolName.APPROVAL_REQUEST_CREATE),
        (AgentName.POLICY_RISK, ToolName.APPROVAL_REQUEST_CREATE),
        (AgentName.APPROVAL, ToolName.VENDOR_LOOKUP),
        (AgentName.SYSTEM, ToolName.DOCUMENT_PARSER),
    ],
)
def test_unlisted_calls_are_blocked_with_policy_010(agent, tool):
    result = check_permission(req(agent, tool))
    assert result.authorization == Authorization.BLOCKED
    assert result.reason == ReasonCode.UNAUTHORIZED_TOOL_CALL
    assert result.rule_id == "POLICY-010"


@pytest.mark.parametrize(
    "agent", [AgentName.INTAKE, AgentName.VERIFICATION, AgentName.POLICY_RISK, AgentName.APPROVAL]
)
def test_no_agent_may_authorize_payment_policy_014(agent):
    result = check_permission(req(agent, ToolName.PAYMENT_AUTHORIZE), payment_permitted=True)
    assert not result.allowed and result.rule_id == "POLICY-014"


def test_governance_payment_requires_permitting_policy():
    blocked = check_permission(req(AgentName.GOVERNANCE, ToolName.PAYMENT_AUTHORIZE))
    assert not blocked.allowed and blocked.rule_id == "POLICY-014"
    allowed = check_permission(
        req(AgentName.GOVERNANCE, ToolName.PAYMENT_AUTHORIZE), payment_permitted=True
    )
    assert allowed.allowed


def test_approval_request_only_for_medium_or_high_risk():
    r = req(AgentName.APPROVAL, ToolName.APPROVAL_REQUEST_CREATE)
    assert not check_permission(r, risk_level=RiskLevel.LOW).allowed
    assert check_permission(r, risk_level=RiskLevel.MEDIUM).allowed
    assert check_permission(r, risk_level=RiskLevel.HIGH).allowed
    assert check_permission(r).allowed  # risk unknown → allowlist alone decides


def test_purpose_is_required():
    with pytest.raises(ValidationError):
        req(AgentName.VERIFICATION, ToolName.VENDOR_LOOKUP, purpose="")
    whitespace = req(AgentName.VERIFICATION, ToolName.VENDOR_LOOKUP, purpose="     ")
    assert not check_permission(whitespace).allowed


def test_is_write_classification():
    assert is_write(ToolName.PAYMENT_AUTHORIZE)
    assert not is_write(ToolName.VENDOR_LOOKUP)
