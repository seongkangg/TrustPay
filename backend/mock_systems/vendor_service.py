"""Mock vendor master — GET /vendors/{vendor_id}. Read-only."""

from typing import Any

from backend.database.seed_data import ReferenceData, get_reference_data
from backend.mock_systems import MockSystemUnavailable, NotFound, is_available

NAME = "vendor"


class VendorService:
    def __init__(self, ref: ReferenceData | None = None, available: bool | None = None):
        self.ref = ref or get_reference_data()
        self._available = available

    def get_vendor(self, vendor_id: str) -> dict[str, Any]:
        if not is_available(NAME, self._available):
            raise MockSystemUnavailable("vendor service unavailable")
        vendor = self.ref.vendors.get(vendor_id)
        if vendor is None:
            raise NotFound(f"vendor {vendor_id} not found")
        return dict(vendor)

    def find_by_name(self, name: str) -> dict[str, Any] | None:
        if not is_available(NAME, self._available):
            raise MockSystemUnavailable("vendor service unavailable")
        wanted = name.strip().lower()
        for vendor in self.ref.vendors.values():
            if vendor["name"].lower() == wanted:
                return dict(vendor)
        return None
