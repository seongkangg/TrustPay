# Governance Policy Matrix

All rules here are **deterministic** and implemented in `backend/governance/policy_engine.py`.
The language model never invents, modifies, or overrides a rule. Constants live in
`data/approval_limits.json` and are loaded at startup.

## Constants

| Constant | Value | Source |
|----------|-------|--------|
| `AUTO_APPROVE_MAX_AMOUNT` | 10,000 USD | `approval_limits.json → thresholds` |
| `CONFIDENCE_THRESHOLD` | 0.75 | `approval_limits.json → thresholds` |
| `APPROVAL_TIMEOUT_HOURS` | 48 | `approval_limits.json → thresholds` |
| `approval_agent` limit | 10,000 USD | `approval_limits.json` |
| `human_reviewer` limit | 100,000 USD | `approval_limits.json` |

## Policy rules

Rules are evaluated in order; **the highest resulting risk wins**. Any `block` or `escalate`
action prevents automatic completion.

| Rule ID | Condition | Risk | Governance action | Reason code |
|---------|-----------|------|-------------------|-------------|
| POLICY-001 | Vendor verified **and** PO exists **and** PO amount == invoice amount | Low | Permit recommendation | `POLICY_PASSED` |
| POLICY-002 | Amount ≤ `AUTO_APPROVE_MAX_AMOUNT` (and no other rule raised risk) | Low | Allow automatic processing → `payment_authorize` | `POLICY_PASSED` |
| POLICY-003 | Amount > acting agent's approval limit | **High** | Block payment, create approval request | `AMOUNT_ABOVE_LIMIT` |
| POLICY-004 | Vendor not found in vendor master (by ID or name) | Medium | Escalate — a human confirms it's a real supplier; never auto-paid. Still High when combined with bank details on the invoice (POLICY-009) or any other High rule | `UNKNOWN_VENDOR` |
| POLICY-005 | Vendor found but `verification_status != verified` | Medium | Escalate for review | `VENDOR_UNVERIFIED` |
| POLICY-006 | Same vendor + vendor_invoice_number already processed, **or** same vendor + amount within 30 days | **High** | Block, recommend reject, escalate | `DUPLICATE_INVOICE` |
| POLICY-007 | PO not found or PO vendor ≠ invoice vendor | **High** | Block, escalate | `INVALID_PURCHASE_ORDER` |
| POLICY-008 | PO found but amount differs from invoice amount | Medium (High if > 10% over) | Escalate for review | `PO_AMOUNT_MISMATCH` |
| POLICY-009 | Sensitive data detected in invoice fields or raw text | Medium (High if also unknown vendor) | Mask data, log `sensitive_data_masked`; continue evaluation | `SENSITIVE_DATA_DETECTED` |
| POLICY-010 | Tool call not on the agent's allowlist | **High** | Block call, record violation; invoice → escalate | `UNAUTHORIZED_TOOL_CALL` |
| POLICY-011 | Required invoice field missing | Medium | Escalate for review | `MISSING_REQUIRED_FIELD` |
| POLICY-012 | Field present but malformed (bad date, non-numeric amount, bad ID format) | Medium | Escalate for review | `MALFORMED_FIELD` |
| POLICY-013 | **Reading** (intake) confidence < `CONFIDENCE_THRESHOLD` — the invoice itself was hard to read (fields model-read below threshold, assumed, placeholder, or malformed). Unconfirmed vendor / PO / duplicate checks are flagged by their own rules, not here | Medium | Require human review | `LOW_CONFIDENCE` |
| POLICY-014 | `payment_authorize` requested by any actor other than `governance_layer` / `human_reviewer` | **High** | Block immediately, record violation | `UNAUTHORIZED_TOOL_CALL` |
| POLICY-015 | Agent raised an exception, timed out, or returned unparseable output | Medium | Invoice → `FAILED`, escalate | `AGENT_FAILURE` |
| POLICY-016 | Mock enterprise system unavailable | Medium | Stop, escalate (never assume vendor/PO is valid) | `MOCK_SYSTEM_UNAVAILABLE` |
| DEFAULT-SAFETY | POLICY-001 did not fire (vendor/PO evidence incomplete) and no other rule raised risk | Medium | Escalate — missing evidence is never a pass | `INSUFFICIENT_EVIDENCE` |

### Required invoice fields (POLICY-011)

`vendor_invoice_number`, `vendor_name` or `vendor_id`, `amount`, `currency`, `due_date`, `purchase_order_id`

## Risk → outcome mapping

| Highest risk | Recommendation agent may give | Governance outcome | Resulting status |
|--------------|-------------------------------|--------------------|------------------|
| Low | approve | `payment_authorize` executed by governance layer | `APPROVED` → `COMPLETED` |
| Medium | escalate | Approval request created; payment not executed | `PENDING_APPROVAL` |
| High | escalate or reject | Payment blocked; approval request created | `BLOCKED` (or `PENDING_APPROVAL` when the only reason is `AMOUNT_ABOVE_LIMIT`) |

A human decision moves `PENDING_APPROVAL` / `BLOCKED` to `APPROVED` or `REJECTED`.
A human can approve amounts up to the `human_reviewer` limit. Above that → stays blocked.

## Default safety behavior

> If evidence is missing, policy evaluation fails, or authorization is unclear — **stop the action and escalate.**

## Sensitive-data handling

### Sensitive field types

| Type | Detection | Dashboard | Logs / audit | Model prompt | Stored |
|------|-----------|-----------|--------------|--------------|--------|
| Bank account number | 8–17 digit sequence near "account"/"acct"/"IBAN", or `bank_account` field | last 4 (`****6789`) | last 4 | last 4 | masked only |
| Routing number | 9-digit ABA pattern or `routing_number` field | last 4 | last 4 | last 4 | masked only |
| Tax ID | `NN-NNNNNNN` EIN / `NNN-NN-NNNN` SSN pattern or `tax_id` field | last 4 | last 4 | last 4 | masked only |
| Personal name (non-vendor) | Contact/attention lines | redacted | redacted | redacted | not stored |
| Address | Street/postal pattern | redacted | redacted | redacted | not stored |
| Payment credentials | Card-number / CVV patterns | fully redacted | fully redacted | never sent | never stored |
| API keys / tokens | `sk-`, `Bearer`, long base64 | fully redacted | fully redacted | never sent | never stored |

### Rules

1. Masking happens at ingestion, **before** persistence and before any LLM call.
2. The stored `Invoice` model rejects any unmasked value (validator in `models/invoice.py`).
3. No agent receives raw values. Only `sensitive_data_scanner` touches raw input, in memory, and discards it.
4. Raw values never appear in an explanation, audit event, or log line. `decision_validator` re-scans explanations and rejects violations.
5. Every detection produces a `SCAN-NNN` evidence ID and a `sensitive_data_masked` event.
6. Retention: raw values are not retained at all; masked values follow the invoice record.

## Reason code reference

| Code | Meaning |
|------|---------|
| `AMOUNT_ABOVE_LIMIT` | Invoice amount exceeds the acting agent's approval limit |
| `UNKNOWN_VENDOR` | Vendor ID not in vendor master |
| `VENDOR_UNVERIFIED` | Vendor exists but is pending/suspended |
| `DUPLICATE_INVOICE` | Matches an already-processed invoice |
| `PO_AMOUNT_MISMATCH` | PO exists but amount differs |
| `INVALID_PURCHASE_ORDER` | PO missing or belongs to another vendor |
| `SENSITIVE_DATA_DETECTED` | Scanner found and masked protected data |
| `UNAUTHORIZED_TOOL_CALL` | Agent attempted a tool outside its allowlist |
| `LOW_CONFIDENCE` | Invoice fields couldn't be read reliably (Reading confidence below threshold) |

## Confidence scores (evidence-based)

Confidence is computed from what the system actually checked — never from the model's opinion of
itself (a local model reports 1.0 for everything). The model's self-reported confidence can only
make an outcome more cautious: an "approve" it is unsure about is escalated.

| Step | Score |
|------|-------|
| Reading (Intake) | Lowest field found. Per field: exact label or structured upload **98%** · read by the model and found verbatim in the PDF **80%** · assumed default (currency) **50%** · placeholder (unreadable invoice number) / malformed / missing **0%** |
| Verification | Share of three checks confirmed: vendor on the list and verified · PO matches vendor and amount · not a duplicate (1/3 = 33%) |
| Policy / Risk | 100% — fixed rules |
| Recommendation | Lower of Reading and Verification |
| `MISSING_REQUIRED_FIELD` | A required field could not be extracted |
| `MALFORMED_FIELD` | A field was present but invalid |
| `AGENT_FAILURE` | Agent error, timeout, or invalid output |
| `MOCK_SYSTEM_UNAVAILABLE` | Vendor/PO/limit service failed |
| `INSUFFICIENT_EVIDENCE` | Vendor/PO lookups did not happen or did not complete; default-safety escalation |
| `POLICY_PASSED` | All checks passed |
