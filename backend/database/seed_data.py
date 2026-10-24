"""Loads the fixed demo dataset from data/ into in-memory reference stores.

Vendors, purchase orders, and approval limits back the mock enterprise systems and are
read-only. Demo invoices are NOT inserted automatically — they enter through
POST /invoices during the demo so the full workflow (including duplicate detection order)
is exercised. `load_demo_invoices()` returns them for tests and the demo script.
"""

import json
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

from backend.config import DATA_DIR


@dataclass
class ReferenceData:
    vendors: dict[str, dict[str, Any]] = field(default_factory=dict)
    purchase_orders: dict[str, dict[str, Any]] = field(default_factory=dict)
    approval_limits: dict[str, dict[str, Any]] = field(default_factory=dict)
    thresholds: dict[str, Any] = field(default_factory=dict)


def _read(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def load_reference_data(data_dir: Path = DATA_DIR) -> ReferenceData:
    vendors = _read(data_dir / "vendors.json")["vendors"]
    pos = _read(data_dir / "purchase_orders.json")["purchase_orders"]
    limits_doc = _read(data_dir / "approval_limits.json")
    return ReferenceData(
        vendors={v["vendor_id"]: v for v in vendors},
        purchase_orders={p["purchase_order_id"]: p for p in pos},
        approval_limits={a["agent_id"]: a for a in limits_doc["approval_limits"]},
        thresholds=limits_doc["thresholds"],
    )


@lru_cache
def get_reference_data() -> ReferenceData:
    return load_reference_data()


DEMO_INVOICE_ORDER = (
    "low_risk_invoice.json",
    "policy_violation_invoice.json",
    "suspicious_invoice.json",
    "duplicate_invoice.json",  # must follow low_risk_invoice.json
)


def load_demo_invoices(data_dir: Path = DATA_DIR) -> list[dict[str, Any]]:
    """Fixtures in demo order; each has `scenario`, `upload`, and `expected`."""
    return [_read(data_dir / "invoices" / name) for name in DEMO_INVOICE_ORDER]
