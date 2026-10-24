# Agent Responsibilities & Permissions

## Responsibility matrix

| Actor | Responsible for | NOT allowed to |
|-------|-----------------|----------------|
| Intake Agent | Extract invoice fields, report per-field confidence, flag missing/malformed fields | Approve, reject, or execute payments; look up vendors or POs |
| Verification Agent | Validate vendor, PO, and detect duplicates | Change vendor or PO records; assign risk; recommend |
| Policy/Risk Agent | Evaluate rules and assign low/medium/high risk with reason codes | Approve payment; create approval requests |
| Approval Agent | Recommend approve / reject / escalate with confidence | Execute any payment or high-risk action; change state |
| Governance Layer | Authorize, block, mask, log, escalate; execute `payment_authorize` only when policy permits | Make unsupported claims; skip logging |
| Human Reviewer | Final approve/reject on escalated invoices, up to their limit | Bypass the audit trail |

## Tool allowlist

Enforced by `backend/governance/permission_checker.py`. Anything not listed is denied with
`UNAUTHORIZED_TOOL_CALL`.

| Tool | Read/Write | Intake | Verification | Policy/Risk | Approval | Governance | Human |
|------|-----------|:------:|:------------:|:-----------:|:--------:|:----------:|:-----:|
| `document_parser` | R | ✅ | | | | | |
| `vendor_lookup` | R | | ✅ | | | | |
| `po_lookup` | R | | ✅ | | | | |
| `approval_limit_lookup` | R | | | ✅ | | | |
| `risk_rules` | R | | | ✅ | | | |
| `approval_request_create` | **W** | | | | ✅ | ✅ | |
| `payment_authorize` | **W** | | | | | ✅ | ✅ (via API) |
| `audit_log_write` | **W** | | | | | ✅ | |

## Tool-call rules

1. Agents never import or call `mock_systems/` directly — only `governance.tool_call_interceptor`.
2. Every call carries `agent` identity, `purpose`, `invoice_id`, and `correlation_id`.
3. Every call is checked against the allowlist before execution.
4. Write operations additionally require: the invoice is in a state that permits the write, and (for `payment_authorize`) the policy engine returned `allowed`.
5. High-risk actions require a recorded human decision first.
6. Denied calls are still recorded as `ToolCall` with `authorization=blocked` and emit `tool_call_denied`.
7. Every executed call returns an `evidence_id` the agent must cite.

## Per-agent specification

### Intake Agent (`intake_agent.py`)

| | |
|---|---|
| **Inputs** | `InvoiceUpload` (already masked by scanner), `source_document` |
| **Outputs** | `AgentDecision` with `decision="fields_extracted"`, list of `ExtractedField` (value + confidence), flags for missing/malformed |
| **Allowed tools** | `document_parser` |
| **Forbidden tools** | everything else |
| **Required evidence** | `PARSE-NNN` evidence ID from the parser call |
| **Failure behavior** | Parser error or unparseable LLM output → `AGENT_FAILURE`, invoice `FAILED`, escalate |
| **Confidence** | Per-field, by how the value was obtained (exact 98%, model-read 80%, assumed 50%, placeholder 0%); overall = min over fields found. Below 0.75 → `LOW_CONFIDENCE` |
| **Escalates when** | Any required field missing or malformed |

### Verification Agent (`verification_agent.py`)

| | |
|---|---|
| **Inputs** | Extracted invoice fields |
| **Outputs** | `AgentDecision` with `decision ∈ {vendor_verified, vendor_unverified, vendor_unknown, po_mismatch, po_invalid, duplicate_detected}` |
| **Allowed tools** | `vendor_lookup`, `po_lookup` |
| **Forbidden tools** | Any write; `approval_limit_lookup` |
| **Required evidence** | `VENDOR-LOOKUP-NNN`, `PO-LOOKUP-NNN`, `DUP-CHECK-NNN` |
| **Failure behavior** | Mock system unavailable → `MOCK_SYSTEM_UNAVAILABLE`, stop and escalate (never assume valid) |
| **Confidence** | Share of checks confirmed (vendor verified, PO matches, not a duplicate); a check that couldn't run counts as unconfirmed |
| **Escalates when** | Unknown vendor, unverified vendor, invalid PO, amount mismatch, duplicate |

### Policy / Risk Agent (`policy_risk_agent.py`)

| | |
|---|---|
| **Inputs** | Invoice + all prior decisions and evidence |
| **Outputs** | `AgentDecision` with `risk_level`, `reason_codes`, `policy_rules_triggered` |
| **Allowed tools** | `approval_limit_lookup`, `risk_rules` |
| **Forbidden tools** | `approval_request_create`, `payment_authorize` |
| **Required evidence** | `LIMIT-LOOKUP-NNN`, `POLICY-NNN` rule IDs |
| **Failure behavior** | Rule evaluation error → treat as High, escalate |
| **Confidence** | Rules are deterministic (1.0); LLM-written reasoning text is advisory |
| **Escalates when** | Any rule yields Medium or High |

### Approval Agent (`approval_agent.py`)

| | |
|---|---|
| **Inputs** | Invoice, risk decision, all evidence |
| **Outputs** | `AgentDecision` with `recommendation ∈ {approve, reject, escalate}` and `Explanation` |
| **Allowed tools** | `approval_request_create` |
| **Forbidden tools** | `payment_authorize` (always blocked → POLICY-014) |
| **Required evidence** | Must cite every evidence ID used in reasons |
| **Failure behavior** | Invalid output → default recommendation `escalate` |
| **Confidence** | Lower of Reading and Verification (evidence-based; the model's self-report is not used as the score) |
| **Escalates when** | Risk ≥ Medium, or the model is unsure (< 0.75) about an approve; must escalate — can never complete a high-risk payment |

### Governance Layer (`governance/`)

| | |
|---|---|
| **Inputs** | Every `ToolCallRequest` and `AgentDecision` |
| **Outputs** | `Authorization`, `AuditEvent`s, masked data, `ApprovalRequest`s |
| **Allowed tools** | `payment_authorize`, `audit_log_write`, `approval_request_create` |
| **Rules** | Deterministic only. No LLM calls. |
| **Failure behavior** | Any internal error → block and escalate |

## Explanation format (required on every decision)

```
Decision: Escalate
Reasons:
  - Vendor was not found in the approved vendor database.
  - Invoice amount exceeds the agent approval limit.
  - Payment information was detected and masked.
Evidence:
  - Vendor lookup: VENDOR-LOOKUP-14
  - Approval policy: POLICY-003
  - Sensitive-data scan: SCAN-088
```

An AI-generated explanation is **not** evidence by itself; every reason must reference an evidence ID that resolves to a recorded tool call, scan, or policy rule.
