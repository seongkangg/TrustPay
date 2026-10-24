"""POST /invoices · GET /invoices · GET /invoices/{id} · GET /invoices/{id}/document.pdf ·
POST /invoices/{id}/process · GET /invoices/{id}/timeline"""

from typing import Any

from fastapi import APIRouter, Depends, Query, Response, status
from pydantic import BaseModel

from backend.api.deps import get_invoice_service
from backend.models import (
    AgentDecision,
    ApprovalRequest,
    Invoice,
    InvoiceStatus,
    InvoiceSummary,
    InvoiceUpload,
    ToolCall,
)
from backend.services.errors import NotFoundError
from backend.services.invoice_service import InvoiceService, row_to_invoice
from backend.services.source_pdf import render_masked_pdf

router = APIRouter(prefix="/invoices", tags=["invoices"])


class InvoiceList(BaseModel):
    items: list[InvoiceSummary]
    total: int


class ProcessResponse(BaseModel):
    invoice: Invoice
    decisions: list[AgentDecision]
    tool_calls: list[ToolCall]
    approval_request: ApprovalRequest | None = None


@router.post("", response_model=Invoice, status_code=status.HTTP_201_CREATED)
def create_invoice(
    upload: InvoiceUpload, svc: InvoiceService = Depends(get_invoice_service)
) -> Invoice:
    return svc.create(upload)


@router.get("", response_model=InvoiceList)
def list_invoices(
    status_: InvoiceStatus | None = Query(None, alias="status"),
    risk_level: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    svc: InvoiceService = Depends(get_invoice_service),
) -> InvoiceList:
    items, total = svc.list_invoices(
        status=status_, risk_level=risk_level, limit=limit, offset=offset
    )
    return InvoiceList(items=items, total=total)


@router.get("/{invoice_id}", response_model=Invoice)
def get_invoice(invoice_id: str, svc: InvoiceService = Depends(get_invoice_service)) -> Invoice:
    return svc.get(invoice_id)


@router.get("/{invoice_id}/document.pdf", response_class=Response)
def get_source_document_pdf(
    invoice_id: str, svc: InvoiceService = Depends(get_invoice_service)
) -> Response:
    """The source document as a PDF download: the redacted original kept at ingestion, else a
    masked copy rebuilt from its text. The unredacted original is never kept."""
    invoice = svc.get(invoice_id)
    stored = svc.source_pdf(invoice_id)
    if stored is not None:
        content, name = stored.pdf, f"{invoice_id}-redacted.pdf"
    elif invoice.source_text:
        content, name = render_masked_pdf(invoice), f"{invoice_id}-masked.pdf"
    else:
        raise NotFoundError(f"invoice {invoice_id} has no source document", invoice_id=invoice_id)
    return Response(
        content=content,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{name}"',
            "Cache-Control": "no-store",
        },
    )


@router.post("/{invoice_id}/process", response_model=ProcessResponse)
def process_invoice(
    invoice_id: str, svc: InvoiceService = Depends(get_invoice_service)
) -> ProcessResponse:
    result = svc.process(invoice_id)
    return ProcessResponse(
        invoice=row_to_invoice(result.invoice),
        decisions=result.decisions,
        tool_calls=result.tool_calls,
        approval_request=ApprovalRequest.model_validate(result.approval_request)
        if result.approval_request
        else None,
    )


@router.get("/{invoice_id}/timeline")
def get_timeline(
    invoice_id: str, svc: InvoiceService = Depends(get_invoice_service)
) -> dict[str, Any]:
    return svc.timeline(invoice_id)
