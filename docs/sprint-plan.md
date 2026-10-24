# Sprint Plan

Ordered by dependency. Each sprint ends in something demoable so the project degrades
gracefully if time runs out. Follows the spec's priority: specs → mock systems →
governance → agents → orchestration → API → dashboard → demo polish → IBM integration.

## Sprint 0 — Agree before coding ✅
- [x] `docs/architecture.md`
- [x] `backend/models/` + `enums.py`
- [x] `docs/policy-matrix.md`
- [x] `docs/agent-permissions.md`
- [x] `docs/api-contracts.md`
- [x] `data/*.json` with expected outputs
- [x] `.env.example`, `requirements.txt`, `package.json`, lint config
- [ ] Assign owners per folder

## Sprint 1 — Foundation + mock systems
- [ ] `database/` engine, tables, seed loader
- [ ] `utils/` logging, timestamps, validation
- [ ] `mock_systems/` vendor, PO, limits, payment (+ failure toggle)
- [ ] `main.py` app factory + `/health`
- [ ] `services/audit_service.py` (append-only, hash chain, dup/out-of-order)
- [ ] `services/masking_service.py`
- [ ] Tests: masking, audit chain

**Done:** server boots, mocks return seeded records.

## Sprint 2 — Governance layer ⭐
- [ ] `permission_checker.py`
- [ ] `policy_engine.py` (every POLICY-NNN row)
- [ ] `sensitive_data_scanner.py`
- [ ] `tool_call_interceptor.py`
- [ ] `decision_validator.py`
- [ ] `governance_engine.py`
- [ ] Tests: `test_policy_engine`, `test_permissions`, `test_governance`

**Done:** agent payment attempt blocked + logged; unknown vendor → High; 100% tool calls audited.

## Sprint 3 — Agents with mocked LLM
- [ ] `llm/granite_client.py` with `MockLLM`
- [ ] `llm/prompts.py`, `llm/output_parser.py`
- [ ] `agents/base_agent.py`
- [ ] four agents
- [ ] Tests: `test_intake_agent`, `test_verification_agent`

**Done:** each agent returns a valid `AgentDecision` with evidence IDs for every fixture.

## Sprint 4 — Orchestration + API
- [ ] `state_machine.py`, `workflow_context.py`, `invoice_workflow.py`
- [ ] `services/invoice_service.py`, `services/approval_service.py`
- [ ] all `api/` routes per `docs/api-contracts.md`
- [ ] Tests: `test_workflow`, `test_scenarios`

**Done:** all four fixtures produce expected status/risk/reason codes/audit sequence via HTTP. *Demoable via Swagger from here.*

## Sprint 5 — Dashboard
- [ ] `api/client.js`, `App.jsx`, `dashboard.css`
- [ ] components: RiskBadge, StatusBadge, AgentTimeline, ToolCallTable, AuditLog, ApprovalPanel
- [ ] pages: Dashboard, InvoiceDetails, AuditDetails
- [ ] human approve/reject round-trip

**Done:** full scenario walk-through in the browser; no raw sensitive data anywhere.

## Sprint 6 — Demo hardening
- [ ] `docs/demo-script.md`
- [ ] `docker-compose.yml` one-command start
- [ ] reliability tests: timeout, mock failure, malformed output, dup/out-of-order events
- [ ] perf check: < 10 s/invoice, < 1 s/event
- [ ] demo reset script
- [ ] backup video

## Sprint 7 — IBM integration (stretch)
- [ ] real watsonx.ai / Granite behind a flag
- [ ] watsonx.governance hooks
- [ ] watsonx Orchestrate (or documented rationale for in-process)
- [ ] HashiCorp Vault
- [ ] OpenShift manifests
- [ ] observability export

## Parallelization
- Frontend starts after Sprint 0 against a static JSON mock of the API contract.
- Sprints 2 and 3 can run in parallel once the interceptor interface is agreed.
- One owner for `data/` + `test_scenarios.py` throughout — the "demo truth".
