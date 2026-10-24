"""The only path from an agent to an enterprise (mock) system.

For every request: check the allowlist → execute (or block) → record a ToolCall row →
emit `tool_call_denied` when blocked. Every call, allowed or not, is persisted, so
"100% of tool calls logged" holds by construction.
"""

import json
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.database.tables import ToolCallRow
from backend.governance.permission_checker import check_permission, is_write
from backend.mock_systems import MockSystemUnavailable, NotFound, UnauthorizedActor
from backend.models import (
    AgentName,
    Authorization,
    EventType,
    ReasonCode,
    RiskLevel,
    Severity,
    ToolCall,
    ToolCallRequest,
    ToolName,
)
from backend.services.audit_service import AuditService
from backend.services.masking_service import mask_text
from backend.utils.timestamps import now_utc

Handler = Callable[[dict[str, Any]], Any]

EVIDENCE_PREFIX: dict[ToolName, str] = {
    ToolName.DOCUMENT_PARSER: "PARSE",
    ToolName.VENDOR_LOOKUP: "VENDOR-LOOKUP",
    ToolName.PO_LOOKUP: "PO-LOOKUP",
    ToolName.APPROVAL_LIMIT_LOOKUP: "LIMIT-LOOKUP",
    ToolName.RISK_RULES: "RULES",
    ToolName.APPROVAL_REQUEST_CREATE: "APPROVAL-REQ",
    ToolName.PAYMENT_AUTHORIZE: "PAYMENT",
    ToolName.AUDIT_LOG_WRITE: "AUDIT",
}

SUMMARY_MAX_CHARS = 200


@dataclass
class ToolCallOutcome:
    call: ToolCall
    result: Any | None = None
    error: ReasonCode | None = None

    @property
    def allowed(self) -> bool:
        return self.call.authorization == Authorization.ALLOWED

    @property
    def ok(self) -> bool:
        return self.allowed and self.error is None

    @property
    def not_found(self) -> bool:
        return self.ok and self.result is None


def summarize(result: Any) -> str:
    if result is None:
        return "not found"
    text = result if isinstance(result, str) else json.dumps(result, default=str, sort_keys=True)
    if len(text) > SUMMARY_MAX_CHARS:
        text = text[: SUMMARY_MAX_CHARS - 1] + "…"
    return mask_text(text)[0] or ""


class ToolCallInterceptor:
    def __init__(self, session: Session, audit: AuditService, handlers: dict[ToolName, Handler]):
        self.session = session
        self.audit = audit
        self.handlers = dict(handlers)

    def register(self, tool: ToolName, handler: Handler) -> None:
        self.handlers[tool] = handler

    # ------------------------------------------------------------------

    def execute(
        self,
        request: ToolCallRequest,
        *,
        payment_permitted: bool = False,
        risk_level: RiskLevel | None = None,
    ) -> ToolCallOutcome:
        perm = check_permission(request, payment_permitted=payment_permitted, risk_level=risk_level)
        if not perm.allowed:
            return self._deny(
                request, perm.reason or ReasonCode.UNAUTHORIZED_TOOL_CALL, perm.message
            )

        handler = self.handlers.get(request.tool)
        if handler is None:
            raise RuntimeError(f"no handler registered for {request.tool.value}")

        started = time.perf_counter()
        result: Any | None = None
        error: ReasonCode | None = None
        summary: str
        try:
            result = handler(request.parameters)
            summary = summarize(result)
        except NotFound as exc:
            result, summary = None, f"not found: {exc}"
        except MockSystemUnavailable as exc:
            error, summary = ReasonCode.MOCK_SYSTEM_UNAVAILABLE, f"unavailable: {exc}"
        except UnauthorizedActor as exc:
            return self._deny(request, ReasonCode.UNAUTHORIZED_TOOL_CALL, str(exc))
        latency_ms = int((time.perf_counter() - started) * 1000)

        call = self._record(
            request,
            authorization=Authorization.ALLOWED,
            denial_reason=None,
            result_summary=summary,
            evidence_id=self._next_evidence_id(request.tool),
            latency_ms=latency_ms,
        )
        return ToolCallOutcome(call=call, result=result, error=error)

    # ------------------------------------------------------------------

    def _deny(self, request: ToolCallRequest, reason: ReasonCode, message: str) -> ToolCallOutcome:
        call = self._record(
            request,
            authorization=Authorization.BLOCKED,
            denial_reason=reason,
            result_summary=f"blocked: {message}",
            evidence_id=None,
            latency_ms=0,
        )
        self.audit.append(
            invoice_id=request.invoice_id,
            correlation_id=request.correlation_id,
            event_type=EventType.TOOL_CALL_DENIED,
            severity=Severity.HIGH,
            actor=AgentName.GOVERNANCE,
            reason_codes=[reason],
            policy_result=Authorization.BLOCKED,
            input_summary=f"{request.agent.value} requested {request.tool.value}: {request.purpose}",
            output_summary=message,
            related_tool_call_id=call.tool_call_id,
        )
        return ToolCallOutcome(call=call, result=None, error=reason)

    def _record(self, request: ToolCallRequest, **fields: Any) -> ToolCall:
        call = ToolCall(
            tool_call_id=self._next_call_id(),
            invoice_id=request.invoice_id,
            correlation_id=request.correlation_id,
            agent=request.agent,
            tool=request.tool,
            purpose=request.purpose,
            parameters=request.parameters,
            is_write=is_write(request.tool),
            timestamp=now_utc(),
            **fields,
        )
        row = ToolCallRow(**call.model_dump(mode="json"))
        row.timestamp = call.timestamp
        self.session.add(row)
        self.session.commit()
        return call

    def _count(self, tool: ToolName | None = None) -> int:
        stmt = select(func.count()).select_from(ToolCallRow)
        if tool is not None:
            stmt = stmt.where(
                ToolCallRow.tool == tool.value, ToolCallRow.authorization == "allowed"
            )
        return self.session.scalar(stmt) or 0

    def _next_call_id(self) -> str:
        return f"TOOL-{self._count() + 1:03d}"

    def _next_evidence_id(self, tool: ToolName) -> str:
        return f"{EVIDENCE_PREFIX[tool]}-{self._count(tool) + 1:03d}"

    def evidence_ids_for(self, invoice_id: str) -> set[str]:
        stmt = select(ToolCallRow.evidence_id).where(
            ToolCallRow.invoice_id == invoice_id, ToolCallRow.evidence_id.is_not(None)
        )
        return set(self.session.scalars(stmt))

    def calls_for(self, invoice_id: str) -> list[ToolCall]:
        stmt = (
            select(ToolCallRow)
            .where(ToolCallRow.invoice_id == invoice_id)
            .order_by(ToolCallRow.timestamp, ToolCallRow.tool_call_id)
        )
        return [
            ToolCall.model_validate(r, from_attributes=True) for r in self.session.scalars(stmt)
        ]
