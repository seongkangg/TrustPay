# backend/mock_systems/

Simulated enterprise systems. No real banking, ERP, or accounting integrations — these read
from the JSON fixtures in `data/` and behave deterministically so the demo is repeatable.

Agents never import these directly; access goes through `governance/tool_call_interceptor.py`.

| File | Mock endpoint(s) | Read/Write | Permitted agents | What it does |
|------|------------------|-----------|------------------|--------------|
| `vendor_service.py` | `GET /vendors/{vendor_id}` | Read | Verification | Looks up a vendor in `data/vendors.json`. Returns verification status or 404 for unknown vendors. |
| `purchase_order_service.py` | `GET /purchase-orders/{po_id}` | Read | Verification | Looks up a PO in `data/purchase_orders.json`; used to detect amount mismatches and invalid POs. |
| `approval_limit_service.py` | `GET /approval-limits/{agent_id}` | Read | Policy/Risk | Returns the spending authority for an agent from `data/approval_limits.json`. |
| `payment_service.py` | `POST /payments/authorize` | **Write** | Governance layer only | Simulates payment authorization. Any call from an agent is blocked and logged as `UNAUTHORIZED_TOOL_CALL`. Never moves real money. |

Each mock can be configured to fail (timeout / 500) for reliability tests in `tests/`.
