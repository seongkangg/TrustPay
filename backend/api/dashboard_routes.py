"""GET /dashboard/summary — aggregates for the overview screen."""

from typing import Any

from fastapi import APIRouter, Depends

from backend.api.deps import get_invoice_service
from backend.services.invoice_service import InvoiceService

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary")
def summary(svc: InvoiceService = Depends(get_invoice_service)) -> dict[str, Any]:
    return svc.dashboard_summary()
