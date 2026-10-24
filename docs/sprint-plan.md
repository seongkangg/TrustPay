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

## Sprint 1 — Foundation + mock systems ✅
- [x] `database/` engine, tables, seed loader
- [x] `utils/` logging, timestamps, validation
- [x] `mock_systems/` vendor, PO, limits, payment (+ failure toggle)
- [x] `main.py` app factory + `/health` (+ `config.py` settings)
- [x] `services/audit_service.py` (append-only, hash chain, dup/out-of-order)
- [x] `services/masking_service.py`
- [x] Tests: masking, audit chain, mock systems — 23 passing

**Done:** server boots, mocks return seeded records.
Deferred to Sprint 4: HTTP exposure of mocks under `/mock/*` (they are plain Python services until the API routers land).

## Sprint 2 — Governance layer ⭐ ✅
- [x] `permission_checker.py`
- [x] `policy_engine.py` (every POLICY-NNN row + DEFAULT-SAFETY)
- [x] `sensitive_data_scanner.py`
- [x] `tool_call_interceptor.py`
- [x] `decision_validator.py`
- [x] `governance_engine.py` (incl. human-decision + human-payment paths for Sprint 4)
- [x] Tests: `test_policy_engine`, `test_permissions`, `test_governance` — 81 passing total

**Done:** agent payment attempt blocked + logged; unknown vendor → High; 100% tool calls audited.
All four fixtures produce their expected risk / reason codes / target status through the policy engine.

## Sprint 3 — Agents with mocked LLM ✅
- [x] `llm/granite_client.py` with `MockLLM` (+ `WatsonxLLM` behind `LLM_MODE=watsonx`)
- [x] `llm/prompts.py`, `llm/output_parser.py`
- [x] `agents/base_agent.py`
- [x] four agents
- [x] `orchestration/workflow_context.py` (pulled forward — agents need it)
- [x] Tests: `test_llm`, `test_intake_agent`, `test_verification_agent`, `test_approval_agents` — 114 passing total

**Done:** each agent returns a valid `AgentDecision` with evidence IDs for every fixture;
all four fixtures reach their expected risk, reason codes, and recommendation through the agent chain.

## Sprint 4 — Orchestration + API ✅
- [x] `state_machine.py`, `workflow_context.py`, `invoice_workflow.py`
- [x] `services/invoice_service.py`, `services/approval_service.py` (+ `services/errors.py`)
- [x] all `api/` routes per `docs/api-contracts.md` (+ read-only `/mock/*`, `api/deps.py`, JSON error handlers)
- [x] Tests: `test_workflow`, `test_scenarios` — 139 passing total

**Done:** all four fixtures produce expected status/risk/reason codes/exact audit sequence via HTTP,
dashboard summary matches, human approve/reject round-trip, no raw secret in any response.
*Demoable via Swagger (`/docs`) from here.*

## Sprint 5 — Dashboard ✅
Design skills (project-level in `.claude/skills/`, pinned in `skills-lock.json`):
- **impeccable** (`pbakaus/impeccable`): run `/impeccable init` once for design context
  (audience: finance reviewers / compliance; tone: calm, trustworthy, dense but legible;
  hard rules from `frontend/README.md`), then use it for the critique / polish pass.
- **design-taste-frontend** (`Leonxlnx/taste-skill`): layout, type scale, palette for the app screens.
- **emilkowalski/skill** (`emil-design-eng`, `animate`, `improve-animations`, `review-animations`):
  small CSS-only motion (badge change after approve/reject, timeline stagger,
  `prefers-reduced-motion`). No animation library, no UI framework.

- [x] `api/client.js`, `App.jsx`, `dashboard.css` (+ `vite.config.js`, `index.html`, `main.jsx`, `eslint.config.js`)
- [x] components: RiskBadge, StatusBadge, AgentTimeline, ToolCallTable, AuditLog, ApprovalPanel
- [x] pages: Dashboard (with demo-scenario buttons fed from `data/invoices/*.json`), InvoiceDetails, AuditDetails
- [x] human approve/reject round-trip
- [x] fix: API models re-attach UTC to SQLite datetimes so the browser shows one consistent clock
- [ ] design critique / polish pass with the skills above (not started)

**Done:** scenarios 1–3 walked through in the browser (`.claude/launch.json` starts both servers);
low-risk auto-completed, policy violation approved by a human to COMPLETED, suspicious invoice
BLOCKED with masked identifiers; `npm run lint` and `npm run build` clean.

## Sprint 6 — Demo hardening ✅ (except the video)
- [x] `docs/demo-script.md` — six-minute click-by-click script with talking points and a fallback table
- [x] `docker-compose.yml` + `backend/Dockerfile` + `frontend/Dockerfile` — `docker compose up --build`
- [x] reliability tests (`test_reliability.py`): model timeout, unexpected model exception, PO / limit / payment service down, payment down during human approval is retryable, chain valid under every failure
- [x] perf check (`test_performance.py`): < 10 s/invoice over HTTP, < 1 s/audit event
- [x] demo reset: `POST /demo/reset` (disabled in production) + `npm run reset`
- [x] fix: human approval now pays first and records the decision only once payment took effect, so a payment outage leaves nothing half-recorded
- [ ] backup video — record it by walking `docs/demo-script.md`

## Sprint 7 — IBM integration (stretch)
- [x] real Granite behind a flag — `LLM_MODE=ollama` runs `granite3.3:8b` locally via Ollama (≈15–20 s per invoice on a laptop; the < 10 s target holds in mock mode). `LLM_MODE=watsonx` client exists but is unexercised without credentials.
- [ ] watsonx.governance hooks
- [ ] watsonx Orchestrate (or documented rationale for in-process)
- [ ] HashiCorp Vault
- [ ] OpenShift manifests
- [ ] observability export

## Sprint 8 — Email intake + dashboard refocus
Invoices now arrive from Gmail; the web app shows graphs and data and takes the human decision.
- [x] `backend/inbox/`: read-only Gmail client, `authorize` script, PDF → fields parser, `InboxService.sync` with dedupe, background poller, `GET /inbox/status`, `POST /inbox/sync`
- [x] `inbox_messages` table (cleared by `/demo/reset`); `INBOX_*` / `GMAIL_*` settings; `secrets/` ignored
- [x] `scripts/make_invoice_pdfs.py` → `data/invoices/pdf/*.pdf` (labels shared with the parser)
- [x] tests: `test_pdf_parser`, `test_inbox` (fake Gmail service + fake client, no network)
- [x] dashboard refocus: demo buttons / "Run agents" removed; "Needs your approval" queue, amount tiles, three Recharts graphs, inbox card, 15 s refresh; `dashboard_summary` gains `by_day` + `amounts` (`test_dashboard_summary.py`)
- [x] one-time OAuth on the demo machine (Gmail authorized, poller running)
- [ ] an end-to-end emailed invoice through the real inbox
- [x] free-form invoices: Granite fills fields the labels miss, each value checked against the document text; dates normalized; vendor matched by name through the governed lookup; an invalid field no longer drops the email; null model confidence read as 0 (`test_llm_extraction.py`, 201 tests). Real Granite reads the two-column example correctly in ~16 s end to end.

## Parallelization
- Frontend starts after Sprint 0 against a static JSON mock of the API contract.
- Sprints 2 and 3 can run in parallel once the interceptor interface is agreed.
- One owner for `data/` + `test_scenarios.py` throughout — the "demo truth".
