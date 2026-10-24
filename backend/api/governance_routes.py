"""POST /governance/evaluate-tool-call (dry run) · GET /invoices/{id}/audit"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from backend.api.deps import get_engine, get_invoice_service
from backend.governance import GovernanceEngine
from backend.governance.permission_checker import check_permission
from backend.models import (
    AgentName,
    AuditTrail,
    Authorization,
    EventType,
    ReasonCode,
    RiskLevel,
    Severity,
    ToolCallRequest,
)
from backend.services.invoice_service import InvoiceService

router = APIRouter(tags=["governance"])


class EvaluateToolCallBody(ToolCallRequest):
    payment_permitted: bool = False
    risk_level: RiskLevel | None = None


class EvaluateToolCallResponse(BaseModel):
    authorization: Authorization
    denial_reason: ReasonCode | None = None
    policy_rules_triggered: list[str]
    explanation: str


@router.post("/governance/evaluate-tool-call", response_model=EvaluateToolCallResponse)
def evaluate_tool_call(
    body: EvaluateToolCallBody, gov: GovernanceEngine = Depends(get_engine)
) -> EvaluateToolCallResponse:
    """Dry-run the permission checker. Nothing is executed; a denial is still audited."""
    request = ToolCallRequest.model_validate(
        body.model_dump(exclude={"payment_permitted", "risk_level"})
    )
    result = check_permission(
        request, payment_permitted=body.payment_permitted, risk_level=body.risk_level
    )
    if not result.allowed:
        gov.record(
            actor=AgentName.GOVERNANCE,
            invoice_id=request.invoice_id,
            correlation_id=request.correlation_id,
            event_type=EventType.TOOL_CALL_DENIED,
            severity=Severity.HIGH,
            reason_codes=[result.reason] if result.reason else [],
            policy_result=Authorization.BLOCKED,
            input_summary=f"dry run: {request.agent.value} requested {request.tool.value}",
            output_summary=result.message,
        )
    return EvaluateToolCallResponse(
        authorization=result.authorization,
        denial_reason=result.reason,
        policy_rules_triggered=[result.rule_id] if result.rule_id else [],
        explanation=result.message,
    )


@router.get("/invoices/{invoice_id}/audit", response_model=AuditTrail)
def get_audit(
    invoice_id: str,
    gov: GovernanceEngine = Depends(get_engine),
    invoices: InvoiceService = Depends(get_invoice_service),
) -> AuditTrail:
    invoices.get_row(invoice_id)  # 404 if unknown
    return gov.audit.get_trail(invoice_id)
