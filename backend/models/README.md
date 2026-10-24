# backend/models/

Pydantic data contracts shared by the API, agents, governance, and database layers.
Define these before writing any logic — they are the schema the whole team codes against.

| File | Model | Key fields |
|------|-------|-----------|
| `invoice.py` | `Invoice` | `invoice_id`, `vendor_id`, `vendor_name`, `amount`, `currency`, `due_date`, `purchase_order_id`, `bank_account` (masked), `tax_id` (masked), `source_document`, `source_text` (masked text of the source document), `status`, `risk_level` |
| `agent_decision.py` | `AgentDecision` | `decision_id`, `invoice_id`, `agent`, `decision`, `confidence` (0–1), `evidence_ids[]`, `reason_codes[]`, `explanation`, `timestamp` |
| `tool_call.py` | `ToolCall` | `tool_call_id`, `agent`, `tool`, `parameters`, `purpose`, `authorization` (`allowed`/`blocked`/`escalated`), `result_summary`, `timestamp` |
| `audit_event.py` | `AuditEvent` | `event_id`, `invoice_id`, `event_type`, `severity`, `actor`, `reason_codes[]`, `input_summary`, `output_summary`, `policy_result`, `evidence_refs[]`, `previous_event_hash`, `timestamp` |
| `approval.py` | `Approval` / `ApprovalRequest` | `approval_id`, `invoice_id`, `requested_by`, `recommendation`, `reviewer`, `human_decision`, `decided_at` |
| `enums.py` | `InvoiceStatus`, `RiskLevel`, `AgentName`, `ToolName`, `Authorization`, `Recommendation`, `EventType`, `ReasonCode` | All enum values used across the system; no free-text strings for these. |

## Conventions

- Timestamps: ISO-8601 UTC (`2026-10-24T10:00:00Z`).
- IDs are prefixed: `INV-`, `DEC-`, `TOOL-`, `EVT-`, `APR-`, `VENDOR-LOOKUP-`, `POLICY-`, `SCAN-`.
- Every event carries the invoice's correlation ID.
- Audit events are append-only; `previous_event_hash` chains them (simulated integrity).
- Sensitive fields are stored masked (last 4 digits only) — raw values never enter a model or log message.
