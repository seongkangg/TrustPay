# backend/api/

FastAPI routers. Each file groups related endpoints; routes stay thin and delegate to `services/`.

| File | Endpoints | What it does |
|------|-----------|--------------|
| `invoice_routes.py` | `POST /invoices` · `GET /invoices` · `GET /invoices/{id}` · `POST /invoices/{id}/process` · `GET /invoices/{id}/timeline` | Upload/list/fetch invoices, trigger the agent workflow, return the chronological agent + tool-call timeline. |
| `approval_routes.py` | `POST /invoices/{id}/approve` · `POST /invoices/{id}/reject` | Human reviewer decisions. Records reviewer identity + timestamp, transitions state, emits `human_decision_recorded` audit event. |
| `governance_routes.py` | `POST /governance/evaluate-tool-call` · `GET /invoices/{id}/audit` | Expose the governance engine for inspection: evaluate whether a hypothetical tool call would be allowed, and return the append-only audit trail for an invoice. |
| `dashboard_routes.py` | `GET /dashboard/summary` | Aggregates for the overview screen: total invoices, low/medium/high risk counts, blocked actions (`payment_blocked` + `tool_call_denied` events), pending approvals, sensitive-data detections, recent policy violations. |
| `mock_routes.py` | `GET /mock/vendors/{id}` · `GET /mock/purchase-orders/{id}` · `GET /mock/approval-limits/{agent}` · `GET /mock/thresholds` | Read-only inspection of the mock enterprise systems for the demo. Mutating mocks (payments, approval requests) are **not** exposed over HTTP — only the governance interceptor reaches them. |
| `inbox_routes.py` | `GET /inbox/status` · `POST /inbox/sync` | Gmail intake: whether it is enabled/authorized, the poller's last result, recent fetched messages; and an on-demand sync. 503 `INBOX_NOT_AUTHORIZED` until `python -m backend.inbox.authorize` has been run. |
| `demo_routes.py` | `POST /demo/reset` | Wipes invoices, decisions, tool calls, audit events, approvals, and the simulated payment ledger so the demo can be rerun without a restart. Reference data is untouched. Returns 403 when `APP_ENV=production`. |
| `deps.py` | — | FastAPI dependencies: one `GovernanceEngine` per request over the request session; the simulated payment ledger is a process-wide singleton so the double-payment guard survives across requests. |

Errors raised by services (`services/errors.py`) and invalid state transitions are turned into the
contract's JSON error body by handlers in `main.py`: `{error, message, invoice_id, correlation_id, timestamp}`.

Every mutating endpoint generates at least one audit event. Responses never contain
unmasked sensitive fields — masking is applied in `services/masking_service.py` before serialization.
