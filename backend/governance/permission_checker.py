"""Agent → tool allowlist (docs/agent-permissions.md). Anything not listed is denied.

Deterministic. No LLM. Called by `tool_call_interceptor` before every tool call.
"""

from dataclasses import dataclass

from backend.models import (
    AgentName,
    Authorization,
    ReasonCode,
    RiskLevel,
    ToolCallRequest,
    ToolName,
)

ALLOWLIST: dict[AgentName, frozenset[ToolName]] = {
    AgentName.INTAKE: frozenset({ToolName.DOCUMENT_PARSER}),
    AgentName.VERIFICATION: frozenset({ToolName.VENDOR_LOOKUP, ToolName.PO_LOOKUP}),
    AgentName.POLICY_RISK: frozenset({ToolName.APPROVAL_LIMIT_LOOKUP, ToolName.RISK_RULES}),
    AgentName.APPROVAL: frozenset({ToolName.APPROVAL_REQUEST_CREATE}),
    AgentName.GOVERNANCE: frozenset(
        {ToolName.APPROVAL_REQUEST_CREATE, ToolName.PAYMENT_AUTHORIZE, ToolName.AUDIT_LOG_WRITE}
    ),
    AgentName.HUMAN_REVIEWER: frozenset({ToolName.PAYMENT_AUTHORIZE}),
    AgentName.SYSTEM: frozenset(),
}

WRITE_TOOLS: frozenset[ToolName] = frozenset(
    {ToolName.APPROVAL_REQUEST_CREATE, ToolName.PAYMENT_AUTHORIZE, ToolName.AUDIT_LOG_WRITE}
)

PAYMENT_ACTORS: frozenset[AgentName] = frozenset({AgentName.GOVERNANCE, AgentName.HUMAN_REVIEWER})


@dataclass(frozen=True)
class PermissionResult:
    authorization: Authorization
    reason: ReasonCode | None = None
    rule_id: str | None = None
    message: str = ""

    @property
    def allowed(self) -> bool:
        return self.authorization == Authorization.ALLOWED


def is_write(tool: ToolName) -> bool:
    return tool in WRITE_TOOLS


def check_permission(
    request: ToolCallRequest,
    *,
    payment_permitted: bool = False,
    risk_level: RiskLevel | None = None,
) -> PermissionResult:
    """Decide whether `request.agent` may call `request.tool` right now.

    `payment_permitted` must be True (set only by the governance engine after the policy
    engine returned a low-risk result, or after a recorded human approval) for
    `payment_authorize` to pass. `risk_level`, when known, gates approval-request creation.
    """
    agent, tool = request.agent, request.tool

    if not request.purpose or not request.purpose.strip():
        return PermissionResult(
            Authorization.BLOCKED,
            ReasonCode.UNAUTHORIZED_TOOL_CALL,
            "POLICY-010",
            "purpose is required",
        )

    # POLICY-014: payment execution by any actor other than governance / human → block immediately.
    if tool == ToolName.PAYMENT_AUTHORIZE and agent not in PAYMENT_ACTORS:
        return PermissionResult(
            Authorization.BLOCKED,
            ReasonCode.UNAUTHORIZED_TOOL_CALL,
            "POLICY-014",
            f"{agent.value} may never authorize payments",
        )

    # POLICY-010: not on the allowlist.
    if tool not in ALLOWLIST.get(agent, frozenset()):
        return PermissionResult(
            Authorization.BLOCKED,
            ReasonCode.UNAUTHORIZED_TOOL_CALL,
            "POLICY-010",
            f"{agent.value} is not permitted to call {tool.value}",
        )

    # Write operations require stricter authorization.
    if tool == ToolName.PAYMENT_AUTHORIZE and not payment_permitted:
        return PermissionResult(
            Authorization.BLOCKED,
            ReasonCode.UNAUTHORIZED_TOOL_CALL,
            "POLICY-014",
            "payment requires a permitting policy result or recorded human approval",
        )
    if tool == ToolName.APPROVAL_REQUEST_CREATE and risk_level == RiskLevel.LOW:
        return PermissionResult(
            Authorization.BLOCKED,
            ReasonCode.UNAUTHORIZED_TOOL_CALL,
            "POLICY-010",
            "approval requests are only created for medium or high risk",
        )

    return PermissionResult(Authorization.ALLOWED, message="allowed")
