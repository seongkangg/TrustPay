# TrustPay — End Deliverables (enforced)

Source: *Governed Multi-Agent Invoice Approval Platform* spec (IBM Hacks PDF, §1–22).
This file is the acceptance contract for the finished MVP. Any agent or person working on
TrustPay must treat each item below as **done only when every acceptance check passes**.
Nothing here widens scope — see `CLAUDE.md` ground rules and the out-of-scope list at the end.

How to use:
- Before starting a sprint item (`docs/sprint-plan.md`), find the deliverable(s) it serves here.
- Before marking it done, run the listed checks. A check that cannot be verified is not passed.
- If code and the referenced doc disagree, the doc wins (per `CLAUDE.md`).

---

## Part A — Design deliverables (agreed before coding, spec §1–§22)

| ID | Deliverable | Lives in | Accept when |
|----|-------------|----------|-------------|
| A1 | MVP spec (§1) | `README.md` | States problem, target user (finance reviewer / compliance officer / security admin), the 7-step workflow, the 4 scenarios, non-goals, and a definition of done (Part D below). |
| A2 | Functional requirements (§2) | `docs/architecture.md` + Part B below | Every bullet in Part B maps to a module and a test. |
| A3 | Nonfunctional requirements (§3) | Part C below | Every target has a measurable check. |
| A4 | Agent responsibility matrix (§4) | `docs/agent-permissions.md` | Each agent defines inputs, outputs, allowed tools, forbidden tools, required evidence, failure behavior, confidence requirement, escalation conditions. |
| A5 | Data contracts (§5) | `backend/models/` | Invoice, AgentDecision, ToolCall, AuditEvent, Approval defined with required fields, types, ranges, null rules, ISO-8601 UTC timestamps, ID prefixes, correlation IDs, enums, error format. |
| A6 | Mock enterprise systems (§6) | `backend/mock_systems/`, `docs/api-contracts.md` | Vendor DB, PO DB, approval-limit service, payment service, audit log service exist; each endpoint documents request, response, auth, permitted agents, errors, read-only vs mutating, pre-access governance checks. |
| A7 | Governance policy matrix (§7) | `docs/policy-matrix.md` | Every condition → risk → action → reason code; POLICY-001…016 implemented one-to-one in `policy_engine.py`. |
| A8 | Permission / tool allowlist (§8) | `docs/agent-permissions.md`, `permission_checker.py` | Allowlist matches the doc exactly; anything unlisted is denied. |
| A9 | Sensitive-data rules (§9) | `docs/policy-matrix.md` | Defines fields, dashboard/log masking, who sees raw values (nobody downstream of the scanner), model input (masked only), detection method, storage, retention. |
| A10 | Evidence & explainability rules (§10) | `docs/agent-permissions.md` | Explanation format fixed (Decision / Reasons / Evidence); AI text is never evidence on its own. |
| A11 | Event & audit-trail design (§11) | `backend/models/audit_event.py`, `services/audit_service.py` | Append-only, ordered, duplicate handling, out-of-order handling, simulated hash chain, every event tied to an invoice, failures recorded. |
| A12 | Architecture diagram (§12) | `docs/architecture.md` | Frontend → API → Orchestrator → Agents → Governance → Mock APIs → Audit Store; each component classified. |
| A13 | Technology decisions (§13) | `README.md`, `docs/architecture.md` | Stack locked; explicit real-vs-simulated table. |
| A14 | API specification (§14) | `docs/api-contracts.md` | All 10 endpoints in Part B7 with request, response, status codes, errors, authorization, audit events generated. |
| A15 | Dashboard wireframes (§15) | `frontend/README.md` or `docs/` | Overview, Invoice Detail, Agent Timeline, Audit View. |
| A16 | State machine (§16) | `orchestration/state_machine.py` | Valid transitions per `README.md`; invalid ones rejected. |
| A17 | Failure & security rules (§17) | `docs/policy-matrix.md` (POLICY-015/016, default safety) | Each failure case in Part B9 has a defined outcome. |
| A18 | Test specification (§18) | `tests/` | Every case in Part E exists as a named test. |
| A19 | Demo data (§19) | `data/` | Each scenario fixture has invoice, vendor, PO, approval limit, expected agent outputs, risk, governance decision, dashboard state, audit events. |
| A20 | AI guardrails (§20) | `llm/output_parser.py`, `decision_validator.py` | Rules in Part B8 enforced in code. |
| A21 | Repo & engineering setup (§21) | root files | Repo structure, branching, `.env.example`, setup instructions, Docker, DB init, seed data, API docs, lint config, shared schemas, error conventions, logging format, task board (`docs/sprint-plan.md`). |
| A22 | Pre-coding checklist (§22) | `docs/sprint-plan.md` Sprint 0 | All items agreed, including **team ownership per folder**. |

**Hackathon priority** (spec §22): A1, A5, A7, A8, A12, A15, A19, Part E demo tests.

---

## Part B — Functional deliverables (what the running system must do)

### B1. Invoice intake — `intake_agent.py`
- [ ] Accepts PDF, image, or structured JSON mock invoice.
- [ ] Extracts: invoice ID, vendor name, vendor ID, amount, currency, due date, PO number, bank account, tax ID.
- [ ] Reports per-field and overall extraction confidence (overall = min of fields).
- [ ] Flags missing (`MISSING_REQUIRED_FIELD`) and malformed (`MALFORMED_FIELD`) fields.
- [ ] Only tool: `document_parser`; cites a `PARSE-NNN` evidence ID.

### B2. Verification — `verification_agent.py`
- [ ] Compares invoice to mock vendor records and mock purchase orders.
- [ ] Detects unknown vendor, amount mismatch, invalid PO, duplicate invoice ID, duplicate vendor+amount.
- [ ] Only tools: `vendor_lookup`, `po_lookup`; never writes vendor or PO records.
- [ ] Mock system down → `MOCK_SYSTEM_UNAVAILABLE`, stop and escalate; never assumes valid.

### B3. Policy & risk — `policy_risk_agent.py` + `governance/policy_engine.py`
- [ ] Checks approval thresholds, vendor verification status, data-access permissions, suspicious conditions.
- [ ] Assigns exactly one of `low` / `medium` / `high`; highest triggered rule wins.
- [ ] Every risk decision lists reason codes and `POLICY-NNN` rule IDs.
- [ ] Thresholds read from `data/approval_limits.json` only.
- [ ] Cannot approve payment or create approval requests.

### B4. Approval — `approval_agent.py`
- [ ] Produces exactly one of `approve` / `reject` / `escalate` with a confidence score.
- [ ] Risk ≥ medium or confidence < 0.75 → `escalate` (or `reject` for duplicates).
- [ ] Cannot call `payment_authorize` (always blocked, POLICY-014).
- [ ] Invalid model output → defaults to `escalate`.

### B5. Human approval — `services/approval_service.py`, `api/approval_routes.py`
- [ ] Approve/reject endpoints record reviewer identity and timestamp.
- [ ] Human can approve up to the `human_reviewer` limit; above that, stays blocked.
- [ ] Approval timeout (`APPROVAL_TIMEOUT_HOURS`) leaves the invoice unpaid and escalated.
- [ ] Recommendation and final human decision are stored and shown separately.

### B6. Governance — `backend/governance/`
- [ ] Logs every agent action and every tool call (allowed, blocked, escalated).
- [ ] Verifies agent authorization per tool and per data field.
- [ ] Detects and masks bank accounts, routing numbers, tax IDs, personal names, addresses, payment credentials, API keys.
- [ ] Blocks unauthorized payment and vendor-update actions.
- [ ] Requires human approval for high-value or suspicious transactions.
- [ ] Produces an explanation for every final decision.
- [ ] Maintains an append-only, hash-chained audit trail.
- [ ] Contains **no LLM calls**.

### B7. Backend API — `backend/api/`
`POST /invoices` · `GET /invoices` · `GET /invoices/{id}` · `POST /invoices/{id}/process` ·
`GET /invoices/{id}/timeline` · `GET /invoices/{id}/audit` · `POST /invoices/{id}/approve` ·
`POST /invoices/{id}/reject` · `POST /governance/evaluate-tool-call` · `GET /dashboard/summary`
- [ ] Each matches `docs/api-contracts.md` (body, status codes, errors, auth, audit events).
- [ ] No response contains a raw sensitive value.

### B8. AI guardrails — `backend/llm/`, `decision_validator.py`
- [ ] All model output is structured JSON validated against a schema; invalid → rejected.
- [ ] Model never executes tools; all calls go through `tool_call_interceptor`.
- [ ] Every factual claim carries an evidence ID that resolves to a recorded tool call, scan, or policy rule.
- [ ] Unsupported reasoning is rejected; confidence is advisory only.
- [ ] Model cannot override policy; limits and authorization are deterministic.
- [ ] Model used only for extraction, summarization, recommendation text.
- [ ] A mocked LLM (`MockLLM`) makes all demo runs deterministic.

### B9. Failure handling (spec §17) — default: **stop the action and escalate**
| Case | Required outcome |
|------|------------------|
| Extraction fails | `AGENT_FAILURE`, invoice `FAILED`, escalated |
| Vendor API unavailable | `MOCK_SYSTEM_UNAVAILABLE`, escalated |
| PO data missing | `INVALID_PURCHASE_ORDER`, blocked |
| Agent returns invalid JSON | `AGENT_FAILURE`, recommendation defaults to escalate |
| Unsupported model claim | Rejected by `decision_validator`, escalated |
| Unauthorized tool call | Blocked, `tool_call_denied` event, `UNAUTHORIZED_TOOL_CALL` |
| Duplicate event | Ignored idempotently; chain unchanged |
| Out-of-order event | Recorded and flagged; chain not corrupted |
| Sensitive data detected | Masked, `sensitive_data_masked` event, `SCAN-NNN` evidence |
| Human approval timeout | Payment not executed; stays escalated |
| One agent fails | Workflow continues to a safe terminal state; others' records kept |

### B10. Dashboard — `frontend/`
- [ ] **Overview:** total invoices, low/medium/high counts, blocked actions, pending approvals, recent policy violations.
- [ ] **Invoice Detail:** invoice info, status, risk, final recommendation, sensitive-data warnings, approval controls.
- [ ] **Agent Timeline:** chronological agent activity, tool calls, governance decisions, blocked actions, confidence, evidence links.
- [ ] **Audit View:** immutable event list with actor, action, timestamp, policy result, integrity status.
- [ ] Design rules: blocked actions obvious; consistent risk colors; never raw sensitive data; recommendation separate from human decision; "why" next to each major decision; explicit human approval action; no raw technical logs on the main page.

---

## Part C — Nonfunctional targets (spec §3)

| Requirement | Target | Checked by |
|-------------|--------|------------|
| Decisions traceable to evidence | 100% of decisions cite ≥1 resolvable evidence ID | `test_governance.py` |
| Agents never call enterprise tools directly | 0 imports of `mock_systems` from `agents/` | grep check + `test_permissions.py` |
| Tool calls logged | 100% of simulated tool calls produce a `ToolCall` record | `test_governance.py` |
| High-risk payments blocked pending approval | 100% | `test_scenarios.py` |
| Sensitive fields never unmasked in UI/API/logs/prompts | 0 raw occurrences | `test_sensitive_data.py` |
| Invalid events rejected or flagged | 100% | `test_workflow.py` |
| Duplicate/out-of-order events don't corrupt trail | hash chain verifies after replay | audit chain test |
| Demo response time | < 10 s per invoice | Sprint 6 perf check |
| Audit event creation | < 1 s | Sprint 6 perf check |
| Agent failure tolerance | System reaches safe terminal state | reliability tests |

---

## Part D — Demo scenarios (end-to-end acceptance)

Fixtures in `data/invoices/` are the source of truth. `test_scenarios.py` must assert each
fixture's full `expected` block (status, risk, reason codes, recommendation, dashboard state,
audit-event sequence).

| Fixture | Invoice | Risk | Reason codes | Recommendation | Final status |
|---------|---------|------|--------------|----------------|--------------|
| `low_risk_invoice.json` | INV-1001 | low | `POLICY_PASSED` | approve | `COMPLETED` (auto-processed) |
| `policy_violation_invoice.json` | INV-1002 | high | `AMOUNT_ABOVE_LIMIT` | escalate | `PENDING_APPROVAL` |
| `suspicious_invoice.json` | INV-1003 | high | `UNKNOWN_VENDOR`, `INVALID_PURCHASE_ORDER`, `AMOUNT_ABOVE_LIMIT`, `SENSITIVE_DATA_DETECTED` | escalate | `BLOCKED` (data masked, payment stopped, audit record) |
| `duplicate_invoice.json` | INV-1004 | high | `DUPLICATE_INVOICE` | reject | `BLOCKED` |

Plus the spec's worked example: a $25,000 invoice from a new vendor with banking info must be
blocked, masked, escalated to a human, and have full reasoning + tool-call history recorded.

`docs/demo-script.md` walks all of the above in the browser, including one human approve and
one human reject round-trip.

---

## Part E — Required tests (spec §18)

**Functional:** valid low-risk · high-value · unknown vendor · duplicate invoice · PO mismatch ·
missing due date · invalid amount · sensitive banking info · unauthorized tool call ·
human approval · human rejection

**Governance:** payment blocked above threshold · agent cannot call unauthorized tool ·
sensitive data masked · every action creates an audit event · explanation references real
evidence · high-risk invoice cannot auto-complete

**Reliability:** duplicate event · out-of-order event · agent timeout · mock API failure ·
malformed model output · missing vendor record

All live in the existing `tests/test_*.py` files; `pytest tests/` passes with zero failures.

---

## Part F — MVP definition of done

The MVP is done when **all** of the following are true:
1. Every Part B checkbox is ticked and covered by a passing test.
2. Every Part C target is met and recorded.
3. All four Part D fixtures pass `test_scenarios.py` through the HTTP API.
4. All Part E tests exist and `pytest tests/` is green; `ruff` is clean.
5. Dashboard walk-through of all scenarios works with no raw sensitive data visible anywhere.
6. `docker-compose up` starts the full system; `.env.example` is sufficient to run the demo.
7. Each folder `README.md` matches what its files actually do.

Sprint 7 (real watsonx.ai, watsonx.governance, Orchestrate, Vault, OpenShift, observability)
is **stretch** and not required for done.

---

## Out of scope — do not build

General-purpose governance for other workflows · fully autonomous payment execution ·
HR/legal/sales/healthcare domains · training a foundation model · real banking or accounting
integrations · production identity management · regulatory certification · unlimited agents
or tools. Vendor records, POs, approvals, and payments stay simulated.
