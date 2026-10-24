"""POST /invoices/{id}/approve · POST /invoices/{id}/reject — the explicit human decision."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from backend.api.deps import get_approval_service
from backend.models import ApprovalRequest, HumanDecisionInput, Invoice
from backend.services.approval_service import ApprovalService

router = APIRouter(prefix="/invoices", tags=["approvals"])


class DecisionResponse(BaseModel):
    invoice: Invoice
    approval: ApprovalRequest


@router.post("/{invoice_id}/approve", response_model=DecisionResponse)
def approve(
    invoice_id: str, body: HumanDecisionInput, svc: ApprovalService = Depends(get_approval_service)
) -> DecisionResponse:
    invoice, approval = svc.approve(invoice_id, body)
    return DecisionResponse(invoice=invoice, approval=ApprovalRequest.model_validate(approval))


@router.post("/{invoice_id}/reject", response_model=DecisionResponse)
def reject(
    invoice_id: str, body: HumanDecisionInput, svc: ApprovalService = Depends(get_approval_service)
) -> DecisionResponse:
    invoice, approval = svc.reject(invoice_id, body)
    return DecisionResponse(invoice=invoice, approval=ApprovalRequest.model_validate(approval))
