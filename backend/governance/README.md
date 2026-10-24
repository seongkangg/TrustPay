# backend/governance/

The deterministic governance middleware. This is the heart of the project — nothing an agent
does reaches an enterprise system, the dashboard, or the audit log without passing through here.
No LLM calls happen in this folder; all rules are hard-coded and testable.

| File | What it does |
|------|--------------|
| `governance_engine.py` | Facade that the orchestrator and agents talk to. Coordinates the other modules: for each agent action it runs permission check → policy evaluation → sensitive-data scan → decision validation, then emits the appropriate audit event (`allowed` / `blocked` / `escalated`). |
| `permission_checker.py` | Agent → tool allowlist (see table below). Rejects any call without an agent identity or purpose. Write operations require stricter authorization. Denied calls are logged with the reason `UNAUTHORIZED_TOOL_CALL`. |
| `policy_engine.py` | The governance policy matrix as code. Maps conditions (amount above limit, unknown vendor, duplicate invoice, PO mismatch, missing field, low confidence, …) to a risk level and action (permit / block / escalate / mask). Emits reason codes. Policies are never invented by the model. |
| `sensitive_data_scanner.py` | Detects bank account numbers, routing numbers, tax IDs, personal names, addresses, payment credentials, API keys/tokens in invoice fields, agent explanations, and log messages. Returns scan IDs used as evidence. |
| `tool_call_interceptor.py` | The only path from an agent to `mock_systems/`. Builds a `ToolCall` record, asks `permission_checker`, executes the call if allowed, summarizes the result, and logs the call regardless of outcome. |
| `decision_validator.py` | Validates an `AgentDecision` before it is accepted: schema-valid JSON, evidence IDs reference real tool calls/scans, no raw sensitive values in explanations, confidence within range, decision value is a known enum. Low confidence → `LOW_CONFIDENCE` escalation. |

## Permission allowlist

| Agent | Allowed tools |
|-------|---------------|
| Intake | `document_parser` |
| Verification | `vendor_lookup`, `po_lookup` |
| Policy/Risk | `approval_limit_lookup`, `risk_rules` |
| Approval | `approval_request_create` |
| Governance layer only | `payment_authorize`, `audit_log_write` |

## Policy matrix (summary)

| Condition | Risk | Action |
|-----------|------|--------|
| Verified vendor + matching PO | Low | Permit recommendation |
| Amount below threshold | Low | Allow automatic processing |
| Amount above agent limit | High | Block, request approval |
| Unknown vendor | Medium (High with bank details or another High rule) | Escalate — human confirms the supplier |
| Duplicate invoice | High | Reject or escalate |
| Sensitive bank info exposed | Med/High | Mask data, log event |
| Unauthorized tool call | High | Block, record violation |
| Missing required field | Medium | Escalate for review |
| Low AI confidence | Medium | Require human review |
| Payment requested by unauthorized agent | High | Block immediately |

Default safety behavior: **if evidence is missing, policy evaluation fails, or authorization is unclear — stop and escalate.**

Full matrix lives in `docs/policy-matrix.md`.

## Engine API (what agents and the orchestrator call)

| Method | Does | Emits |
|--------|------|-------|
| `ingest(upload, invoice_id, correlation_id)` | Masks sensitive fields/text before anything is stored | `sensitive_data_masked` + `SCAN-NNN` evidence |
| `call_tool(request, payment_permitted=, risk_level=)` | Allowlist check → execute → persist `ToolCall` | `tool_call_denied` when blocked |
| `accept_decision(decision)` | Validates evidence, masking, role; persists; sets `governance_result` | `agent_failed` when rejected |
| `evaluate(PolicyInput, invoice_id, correlation_id)` | Runs the matrix | `risk_assigned` |
| `finalize(...)` | Low risk + approve → governance pays; otherwise block + create approval request | `payment_authorized` **or** `payment_blocked` + `approval_requested` |
| `record_human_decision(...)` / `execute_human_payment(...)` | Human approve/reject and the human-authorized payment | `human_decision_recorded`, `payment_authorized` |
| `build_explanation(...)` | Fixed Decision / Reasons / Evidence format from policy hits | — |
| `record(actor=, ...)` | Agents report workflow progress through the governance layer instead of touching the audit store | `invoice_extracted`, `vendor_verified`, `purchase_order_checked`, `duplicate_detected`, `recommendation_generated`, … |

Evidence ID prefixes: `PARSE-`, `VENDOR-LOOKUP-`, `PO-LOOKUP-`, `LIMIT-LOOKUP-`, `RULES-`, `APPROVAL-REQ-`, `PAYMENT-`, `SCAN-`, plus `POLICY-NNN` rule IDs.
`document_parser` has no handler here — the intake agent registers one (Sprint 3).
