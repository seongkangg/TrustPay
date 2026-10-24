"""Shared agent behaviour.

- Tool access only through `GovernanceEngine.call_tool` (never mock_systems directly).
- Model access through `ask()`, which schema-validates the response and returns None on
  any model or parsing failure — callers decide what a failure means for them.
- Every decision goes through `GovernanceEngine.accept_decision`.
- Any unhandled error becomes an `agent_failed` event plus a failure decision that cites
  POLICY-015, so the workflow can continue to a safe terminal state.
"""

import logging
from abc import ABC, abstractmethod
from typing import ClassVar, TypeVar

from pydantic import BaseModel
from sqlalchemy import func, select

from backend.database.tables import AgentDecisionRow
from backend.governance.governance_engine import GovernanceEngine
from backend.governance.tool_call_interceptor import ToolCallOutcome
from backend.llm.granite_client import LLMClient, LLMError, MockLLM
from backend.llm.output_parser import MalformedOutput, parse_as
from backend.models import (
    AgentDecision,
    AgentName,
    AuditEvent,
    EventType,
    Explanation,
    ReasonCode,
    Recommendation,
    RiskLevel,
    Severity,
    ToolCallRequest,
    ToolName,
)
from backend.orchestration.workflow_context import WorkflowContext
from backend.utils.timestamps import now_utc

log = logging.getLogger(__name__)
T = TypeVar("T", bound=BaseModel)


class BaseAgent(ABC):
    name: ClassVar[AgentName]

    def __init__(self, gov: GovernanceEngine, llm: LLMClient | None = None):
        self.gov = gov
        self.llm = llm or MockLLM()

    # ---------------------------------------------------------------- tools

    def request_tool(
        self, ctx: WorkflowContext, tool: ToolName, purpose: str, **params
    ) -> ToolCallOutcome:
        out = self.gov.call_tool(
            ToolCallRequest(
                agent=self.name,
                tool=tool,
                purpose=purpose,
                parameters=params,
                invoice_id=ctx.invoice_id,
                correlation_id=ctx.correlation_id,
            )
        )
        if not out.allowed:
            ctx.unauthorized_tool_call = True
        elif out.error == ReasonCode.MOCK_SYSTEM_UNAVAILABLE:
            ctx.mock_unavailable = True
        ctx.add_evidence(out.call.evidence_id)
        return out

    # ---------------------------------------------------------------- model

    def ask(self, prompt: str, schema: type[T]) -> T | None:
        try:
            return parse_as(schema, self.llm.complete(prompt))
        except (LLMError, MalformedOutput, TimeoutError) as exc:
            log.warning(
                "%s: model output rejected: %s",
                self.name.value,
                exc,
                extra={"agent": self.name.value},
            )
            return None

    # ---------------------------------------------------------------- audit

    def record(
        self, ctx: WorkflowContext, event_type: EventType, severity: Severity, **kw
    ) -> AuditEvent:
        return self.gov.record(
            invoice_id=ctx.invoice_id,
            correlation_id=ctx.correlation_id,
            event_type=event_type,
            severity=severity,
            actor=self.name,
            **kw,
        )

    # ------------------------------------------------------------- decisions

    def decide(
        self,
        ctx: WorkflowContext,
        *,
        decision: str,
        confidence: float,
        evidence_ids: list[str],
        explanation: Explanation,
        reason_codes: list[ReasonCode] | None = None,
        risk_level: RiskLevel | None = None,
        recommendation: Recommendation | None = None,
    ) -> AgentDecision:
        proposed = AgentDecision(
            decision_id=self._next_decision_id(),
            invoice_id=ctx.invoice_id,
            correlation_id=ctx.correlation_id,
            agent=self.name,
            decision=decision,
            confidence=max(0.0, min(1.0, confidence)),
            risk_level=risk_level,
            recommendation=recommendation,
            reason_codes=list(reason_codes or []),
            evidence_ids=list(evidence_ids),
            explanation=explanation,
            timestamp=now_utc(),
        )
        accepted, result = self.gov.accept_decision(proposed)
        if not result.valid:
            ctx.agent_failure = True
        ctx.decisions.append(accepted)
        return accepted

    def _next_decision_id(self) -> str:
        count = self.gov.session.scalar(select(func.count()).select_from(AgentDecisionRow)) or 0
        return f"DEC-{count + 1:03d}"

    # ------------------------------------------------------------------ run

    def run(self, ctx: WorkflowContext) -> AgentDecision:
        try:
            return self._run(ctx)
        except Exception as exc:  # noqa: BLE001 — any agent error must end in a recorded failure
            log.exception("%s failed", self.name.value, extra={"invoice_id": ctx.invoice_id})
            ctx.agent_failure = True
            self.record(
                ctx,
                EventType.AGENT_FAILED,
                Severity.MEDIUM,
                reason_codes=[ReasonCode.AGENT_FAILURE],
                output_summary=f"{type(exc).__name__}: {exc}"[:200],
                evidence_refs=["POLICY-015"],
            )
            return self.decide(
                ctx,
                decision="agent_failed",
                confidence=0.0,
                evidence_ids=["POLICY-015"],
                explanation=Explanation(
                    decision="agent_failed",
                    reasons=[f"{self.name.value} failed with {type(exc).__name__}"],
                    evidence=["POLICY-015"],
                    policy_rules_triggered=["POLICY-015"],
                    recommended_next_step="escalate to a human reviewer",
                ),
                reason_codes=[ReasonCode.AGENT_FAILURE],
            )

    @abstractmethod
    def _run(self, ctx: WorkflowContext) -> AgentDecision: ...
