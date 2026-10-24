# data/

Fixed demo dataset. Loaded by `backend/database/seed_data.py` and read by `backend/mock_systems/`.
Keeping this fixed means the demo does not depend on unpredictable model behavior.

| File | What it contains |
|------|------------------|
| `vendors.json` | Mock vendor database: vendor ID, name, verification status, on-file bank account (masked). Scenario 3's vendor is intentionally **absent**. |
| `purchase_orders.json` | Mock PO records: PO ID, vendor ID, approved amount, currency, status. |
| `approval_limits.json` | Spending authority per agent (e.g. `approval_agent: 10000 USD`). Scenario 2 exceeds this. |

## Demo invoices (`invoices/`)

| File | Scenario | Setup | Expected risk | Expected governance decision |
|------|----------|-------|---------------|------------------------------|
| `low_risk_invoice.json` | 1 — Low risk | Verified vendor, PO matches, amount below threshold | Low | Auto-approve, `COMPLETED` |
| `policy_violation_invoice.json` | 2 — Policy violation | Verified vendor, but amount above agent limit | High | `payment_blocked`, `PENDING_APPROVAL`, reason `AMOUNT_ABOVE_LIMIT` |
| `suspicious_invoice.json` | 3 — Suspicious / sensitive | Unknown vendor and/or duplicate invoice ID, raw bank account + tax ID present | High | Mask data, block payment, escalate; reasons `UNKNOWN_VENDOR`, `DUPLICATE_INVOICE`, `SENSITIVE_DATA_DETECTED` |

Each invoice file should include the expected agent outputs, expected audit events, and
expected dashboard state alongside the input so `tests/test_scenarios.py` can assert on them.
