# backend/api/

FastAPI routers. Each file groups related endpoints; routes stay thin and delegate to `services/`.

| File | Endpoints | What it does |
|------|-----------|--------------|
| `invoice_routes.py` | `POST /invoices` · `GET /invoices` · `GET /invoices/{id}` · `POST /invoices/{id}/process` · `GET /invoices/{id}/timeline` | Upload/list/fetch invoices, trigger the agent workflow, return the chronological agent + tool-call timeline. |
| `approval_routes.py` | `POST /invoices/{id}/approve` · `POST /invoices/{id}/reject` | Human reviewer decisions. Records reviewer identity + timestamp, transitions state, emits `human_decision_recorded` audit event. |
| `governance_routes.py` | `POST /governance/evaluate-tool-call` · `GET /invoices/{id}/audit` | Expose the governance engine for inspection: evaluate whether a hypothetical tool call would be allowed, and return the append-only audit trail for an invoice. |
| `dashboard_routes.py` | `GET /dashboard/summary` | Aggregates for the overview screen: total invoices, low/medium/high risk counts, blocked actions, pending approvals, recent policy violations. |

Every mutating endpoint generates at least one audit event. Responses never contain
unmasked sensitive fields — masking is applied in `services/masking_service.py` before serialization.
