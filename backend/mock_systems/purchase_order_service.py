"""Mock purchase-order database — GET /purchase-orders/{po_id}. Read-only."""

from typing import Any

from backend.database.seed_data import ReferenceData, get_reference_data
from backend.mock_systems import MockSystemUnavailable, NotFound, is_available

NAME = "purchase_order"


class PurchaseOrderService:
    def __init__(self, ref: ReferenceData | None = None, available: bool | None = None):
        self.ref = ref or get_reference_data()
        self._available = available

    def get_purchase_order(self, po_id: str) -> dict[str, Any]:
        if not is_available(NAME, self._available):
            raise MockSystemUnavailable("purchase-order service unavailable")
        po = self.ref.purchase_orders.get(po_id)
        if po is None:
            raise NotFound(f"purchase order {po_id} not found")
        return dict(po)
