"""Mock vendor master — GET /vendors/{vendor_id}. Read-only."""

import re
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
        """Exact match after normalization ("ACME Office Supplies, Inc." == "Acme Office
        Supplies"). Deliberately not fuzzy: "ACME INC." does not match "Acme Office Supplies"
        — an unknown vendor must surface as UNKNOWN_VENDOR, not be guessed into a known one."""
        if not is_available(NAME, self._available):
            raise MockSystemUnavailable("vendor service unavailable")
        wanted = normalize_vendor_name(name)
        if not wanted:
            return None
        matches = [
            v for v in self.ref.vendors.values() if normalize_vendor_name(v["name"]) == wanted
        ]
        return dict(matches[0]) if len(matches) == 1 else None


_COMPANY_SUFFIXES = {
    "inc", "incorporated", "llc", "ltd", "limited", "corp", "corporation",
    "co", "company", "plc", "gmbh", "sa", "ag", "bv",
}  # fmt: skip


def normalize_vendor_name(name: str | None) -> str:
    """Lowercase, drop punctuation and trailing legal suffixes: 'Acme, Inc.' → 'acme'."""
    words = re.sub(r"[^a-z0-9 ]", " ", (name or "").lower()).split()
    while words and words[-1] in _COMPANY_SUFFIXES:
        words.pop()
    return " ".join(words)
