# API Contracts

Base URL: `http://localhost:8000`. All bodies are JSON. All timestamps ISO-8601 UTC.
Sensitive fields are **always** masked in responses. Schemas reference `backend/models/`.

## Conventions

### Error format

```json
{
  "error": "INVALID_TRANSITION",
  "message": "Cannot move invoice INV-1001 from REJECTED to APPROVED",
  "invoice_id": "INV-1001",
  "correlation_id": "c0a8f3e2-...",
  "timestamp": "2026-10-24T10:00:00Z"
}
```

| Status | When |
|--------|------|
| 200 | Success |
| 201 | Created |
| 400 | Validation error / malformed body |
| 403 | Unauthorized tool call or actor over limit |
| 404 | Invoice / resource not found |
| 409 | Invalid state transition, duplicate event |
| 422 | Pydantic validation error (FastAPI default) |
| 500 | Unexpected — always also emits `agent_failed` or equivalent audit event. Body is `INTERNAL_ERROR` with a generic message and an `ERR-…` ref; the traceback goes to the dev log (`DEV_LOG_FILE`) only |

### Authorization (prototype)

Simulated identities. Human endpoints take `reviewer` in the body; agent identity is
internal. Header `X-Actor` is optional and logged when present.

---

## Backend API

### `POST /invoices`
Create an invoice from an upload. Runs the sensitive-data scanner **before** storing.

**Request** — `InvoiceUpload`
```json
{
  "vendor_invoice_number": "ACME-2026-0917",
  "vendor_name": "Acme Office Supplies",
  "vendor_id": "V-101",
  "amount": 4250.0,
  "currency": "USD",
  "due_date": "2026-11-15",
  "purchase_order_id": "PO-5001",
  "source_document": "acme_2026_0917.pdf"
}
```
**Response 201** — `Invoice` (status `RECEIVED`, masked fields)
**Audit events:** `invoice_received`, `sensitive_data_masked` (if any)

### `GET /invoices`
**Query:** `status?`, `risk_level?`, `limit=50`, `offset=0`
**Response 200** — `{ "items": [InvoiceSummary], "total": n }`

### `GET /invoices/{invoice_id}`
**Response 200** — `Invoice` · **404** if unknown

### `POST /invoices/{invoice_id}/process`
Run the full agent workflow. Synchronous for the demo (< 10 s).

**Request:** none
**Response 200**
```json
{
  "invoice": { "...Invoice..." },
  "decisions": [ "...AgentDecision..." ],
  "tool_calls": [ "...ToolCall..." ],
  "approval_request": { "...ApprovalRequest | null..." }
}
```
**409** if invoice not in `RECEIVED`
**Audit events:** the full sequence per scenario (see `data/invoices/*.json → expected.audit_event_sequence`)

### `GET /invoices/{invoice_id}/timeline`
Chronological merge of decisions, tool calls, and governance events.

**Response 200**
```json
{
  "invoice_id": "INV-1002",
  "entries": [
    { "kind": "decision",  "timestamp": "...", "data": { "...AgentDecision..." } },
    { "kind": "tool_call", "timestamp": "...", "data": { "...ToolCall..." } },
    { "kind": "event",     "timestamp": "...", "data": { "...AuditEvent..." } }
  ]
}
```

### `GET /invoices/{invoice_id}/audit`
**Response 200** — `AuditTrail` (`events[]` in sequence order, `chain_valid`)

### `POST /invoices/{invoice_id}/approve`
**Request** — `HumanDecisionInput`
```json
{ "reviewer": "finance.reviewer@example.com", "note": "PO confirmed with procurement" }
```
**Response 200** — `{ "invoice": Invoice, "approval": ApprovalRequest }`
**403** if amount > human reviewer limit · **409** if not `PENDING_APPROVAL`/`BLOCKED`
**Audit events:** `human_decision_recorded`, `payment_authorized`, `audit_record_created`

### `POST /invoices/{invoice_id}/reject`
Same request/response shape. **Audit events:** `human_decision_recorded`, `audit_record_created`

### `POST /governance/evaluate-tool-call`
Dry-run the permission checker (for the demo and tests). The body is a `ToolCallRequest` plus two
optional context fields: `payment_permitted` (bool, default false) and `risk_level`.

**Request** — `ToolCallRequest`
```json
{
  "agent": "approval_agent",
  "tool": "payment_authorize",
  "purpose": "Pay invoice",
  "parameters": { "invoice_id": "INV-1002", "amount": 25000 },
  "invoice_id": "INV-1002",
  "correlation_id": "..."
}
```
**Response 200**
```json
{
  "authorization": "blocked",
  "denial_reason": "UNAUTHORIZED_TOOL_CALL",
  "policy_rules_triggered": ["POLICY-014"],
  "explanation": "approval_agent is not permitted to call payment_authorize"
}
```
**Audit events:** `tool_call_denied` when blocked (dry-run still logs)

### `GET /dashboard/summary`
**Response 200**
```json
{
  "total_invoices": 4,
  "by_risk": { "low": 1, "medium": 0, "high": 3 },
  "by_status": { "COMPLETED": 1, "PENDING_APPROVAL": 1, "BLOCKED": 2 },
  "blocked_actions": 3,
  "pending_approvals": 3,
  "sensitive_data_detections": 1,
  "recent_violations": [
    { "invoice_id": "INV-1003", "reason_codes": ["UNKNOWN_VENDOR", "SENSITIVE_DATA_DETECTED"], "timestamp": "..." }
  ],
  "by_day": [
    { "date": "2026-10-11", "received": 0, "completed": 0, "blocked": 0, "amount": 0.0, "paid": 0.0, "withheld": 0.0 },
    "… 14 entries, oldest first, ending today …",
    { "date": "2026-10-24", "received": 4, "completed": 1, "blocked": 2, "amount": 58500.0, "paid": 4250.0, "withheld": 54250.0 }
  ],
  "amounts": { "total": 58500.0, "paid": 4250.0, "withheld": 54250.0 }
}
```
- `by_day`: the last 14 UTC calendar days by invoice `created_at`. `received` counts every
  invoice that day and `amount` sums their amounts; `completed` / `paid` cover `COMPLETED`;
  `blocked` counts `BLOCKED`; `withheld` sums `PENDING_APPROVAL` + `BLOCKED`. Amounts are rounded
  to cents. Older invoices fall outside the window but still count in `amounts`.
- `amounts`: all invoices, any age. `paid` and `withheld` use the same statuses as `by_day`.

### `GET /inbox/status`
Gmail intake state.
**Response 200**
```json
{
  "enabled": true,
  "authorized": true,
  "poll_seconds": 60,
  "last_sync_at": "2026-10-24T10:00:00Z",
  "last_result": { "checked": 2, "created": ["INV-1005"], "skipped": 1, "failed": [] },
  "last_error": null,
  "recent": [
    { "message_id": "18f3…", "sender": "ap@vendor.example", "subject": "Invoice", "received_at": "…",
      "attachment_name": "invoice.pdf", "invoice_id": "INV-1005", "status": "processed", "error": null, "synced_at": "…" }
  ]
}
```
`status` ∈ `processed` (invoice created and run) · `skipped` (no `invoice.pdf` on the email) · `failed` (unreadable PDF or processing error; see `error`).

### `POST /inbox/sync`
Run one intake pass now. Same result shape as `last_result`.
**503** `INBOX_NOT_AUTHORIZED` — no OAuth token yet (generic message; setup detail goes to the dev log) · **503** `MOCK_SYSTEM_UNAVAILABLE` — Gmail unreachable (generic message, no provider text).
**Audit events:** per created invoice, the full workflow sequence (starting `invoice_received`).

### `GET /health`
**Response 200** — `{ "status": "ok", "llm_mode": "mock" | "watsonx" | "ollama", "db": "ok" }`

---

## Mock enterprise APIs

Internal; reachable only through `tool_call_interceptor`. The **read-only** ones are also exposed
under `/mock/*` for inspection in the demo (plus `GET /mock/thresholds`); the mutating ones
(`/payments/authorize`, `/approvals/request`) are not reachable over HTTP at all.
Every interceptor call requires an agent identity and purpose.

| Endpoint | Method | R/W | Permitted agents | Governance checks before access |
|----------|--------|-----|------------------|--------------------------------|
| `/mock/vendors/{vendor_id}` | GET | R | verification_agent | allowlist |
| `/mock/purchase-orders/{po_id}` | GET | R | verification_agent | allowlist |
| `/mock/approval-limits/{agent_id}` | GET | R | policy_risk_agent | allowlist |
| `/mock/payments/authorize` | POST | **W** | governance_layer, human_reviewer | allowlist + policy `allowed` + state ∈ {RISK_REVIEW low, APPROVED} |
| `/mock/approvals/request` | POST | **W** | approval_agent, governance_layer | allowlist + risk ≥ medium |
| `/mock/audit-events/{invoice_id}` | GET | R | governance_layer | allowlist |

### `GET /mock/vendors/{vendor_id}`
**200**
```json
{ "vendor_id": "V-101", "name": "Acme Office Supplies", "verification_status": "verified", "bank_account_masked": "****1234" }
```
**404** `{ "error": "VENDOR_NOT_FOUND" }` → maps to `UNKNOWN_VENDOR`
**503** `{ "error": "SERVICE_UNAVAILABLE" }` → maps to `MOCK_SYSTEM_UNAVAILABLE` (failure-mode toggle)

### `GET /mock/purchase-orders/{po_id}`
**200**
```json
{ "purchase_order_id": "PO-5001", "vendor_id": "V-101", "approved_amount": 4250.0, "currency": "USD", "status": "open" }
```
**404** → `INVALID_PURCHASE_ORDER`

### `GET /mock/approval-limits/{agent_id}`
**200** `{ "agent_id": "approval_agent", "max_amount": 10000.0, "may_execute_payment": false }`

### `POST /mock/payments/authorize`
**Request** `{ "invoice_id": "INV-1001", "amount": 4250.0, "currency": "USD", "actor": "governance_layer" }`
**200** `{ "payment_id": "PAY-0001", "status": "authorized", "simulated": true }`
**403** `{ "error": "UNAUTHORIZED_ACTOR" }` — any agent other than governance/human
Never moves real money.

### `POST /mock/approvals/request`
**Request** `{ "invoice_id": "INV-1002", "recommendation": "escalate", "risk_level": "high", "reason_codes": ["AMOUNT_ABOVE_LIMIT"] }`
**201** — `ApprovalRequest`

---

## Evidence ID formats

| Prefix | Produced by |
|--------|-------------|
| `PARSE-NNN` | document_parser |
| `VENDOR-LOOKUP-NNN` | vendor_lookup |
| `PO-LOOKUP-NNN` | po_lookup |
| `DUP-CHECK-NNN` | duplicate check inside verification |
| `LIMIT-LOOKUP-NNN` | approval_limit_lookup |
| `POLICY-NNN` | policy_engine rule IDs (fixed, see policy-matrix.md) |
| `SCAN-NNN` | sensitive_data_scanner |
