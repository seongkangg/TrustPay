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
| `suspicious_invoice.json` | 3 — Suspicious / sensitive | Unknown vendor, PO not found, raw bank account + routing + tax ID present | High | Mask data, block payment, escalate; reasons `UNKNOWN_VENDOR`, `INVALID_PURCHASE_ORDER`, `AMOUNT_ABOVE_LIMIT`, `SENSITIVE_DATA_DETECTED` |
| `duplicate_invoice.json` | 3b — Duplicate | Resubmission of scenario 1 (same vendor + invoice number + amount). Process after scenario 1. | High | Block, recommend reject, escalate; reason `DUPLICATE_INVOICE` |

Each invoice file has two parts: `upload` (exactly what `POST /invoices` receives — may
contain raw fake sensitive values) and `expected` (risk, reason codes, recommendation,
final status, masked values, dashboard state, and audit event sequence) so
`tests/test_scenarios.py` can assert on them.

Policy constants live in `approval_limits.json → thresholds`: auto-approve max **$10,000**,
confidence threshold **0.75**, approval timeout 48 h.
