"""Read-only inspection of the mock enterprise systems for the demo (GET /mock/*).

Mutating mocks (payments, approval requests) are deliberately NOT exposed over HTTP:
they are reachable only through the governance tool-call interceptor.
"""

from typing import Any

from fastapi import APIRouter

from backend.mock_systems import NotFound
from backend.mock_systems.approval_limit_service import ApprovalLimitService
from backend.mock_systems.purchase_order_service import PurchaseOrderService
from backend.mock_systems.vendor_service import VendorService
from backend.services.errors import NotFoundError

router = APIRouter(prefix="/mock", tags=["mock systems"])


@router.get("/vendors/{vendor_id}")
def vendor(vendor_id: str) -> dict[str, Any]:
    try:
        return VendorService().get_vendor(vendor_id)
    except NotFound as exc:
        raise NotFoundError(str(exc)) from exc


@router.get("/purchase-orders/{po_id}")
def purchase_order(po_id: str) -> dict[str, Any]:
    try:
        return PurchaseOrderService().get_purchase_order(po_id)
    except NotFound as exc:
        raise NotFoundError(str(exc)) from exc


@router.get("/approval-limits/{agent_id}")
def approval_limit(agent_id: str) -> dict[str, Any]:
    try:
        return ApprovalLimitService().get_limit(agent_id)
    except NotFound as exc:
        raise NotFoundError(str(exc)) from exc


@router.get("/thresholds")
def thresholds() -> dict[str, Any]:
    return ApprovalLimitService().get_thresholds()
