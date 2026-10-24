# TrustPay — Governed Multi-Agent Invoice Approval Platform

A governance layer for autonomous AI agents that process business invoices. Four specialized
agents (Intake → Verification → Policy/Risk → Approval) collaborate on each invoice while a
deterministic governance layer records every decision and tool call, masks sensitive data,
enforces spending/approval policies, and requires human approval before any high-risk action.

**Core rule:** AI may *recommend*; deterministic governance logic *decides* whether an action is allowed.

## MVP workflow

```
Invoice received → extracted → verified → policy checked → recommendation → human approval → audit record
```

## Demo scenarios

| # | Scenario | Expected outcome |
|---|----------|------------------|
| 1 | Low-risk invoice (vendor + PO match, under threshold) | Auto-processed |
| 2 | Policy violation (amount exceeds agent limit) | Blocked, human approval requested |
| 3 | Suspicious invoice (unknown/duplicate vendor, bank data present) | Data masked, payment stopped, audit record created |

## Tech stack

| Layer | Choice |
|-------|--------|
| Frontend | React (Vite) |
| Backend | Python FastAPI |
| Agent logic | watsonx.ai / Granite (or mocked LLM calls) |
| Workflow | Lightweight in-process orchestrator (watsonx Orchestrate optional) |
| Database | SQLite (prototype) |
| Mock enterprise APIs | FastAPI routes + JSON fixtures in `data/` |
| Secrets | `.env` for demo (HashiCorp Vault target) |
| Hosting | Docker Compose locally (OpenShift target) |

## Repository structure

Each folder has its own `README.md` describing its files in detail.

```
TrustPay/
├── README.md               ← this file
├── .env.example            ← template of required environment variables (watsonx keys, DB URL, etc.)
├── docker-compose.yml      ← runs backend + frontend containers together
├── requirements.txt        ← Python dependencies for backend/ and tests/
├── package.json            ← root scripts (e.g. start both services, lint)
│
├── backend/                ← FastAPI service: API, agents, governance, orchestration, mock systems
│   ├── main.py             ← app entrypoint; mounts routers, initializes DB, configures logging
│   ├── api/                ← HTTP route handlers (invoices, approvals, governance, dashboard)
│   ├── agents/             ← the four AI agents + shared base class
│   ├── governance/         ← deterministic governance middleware (permissions, policy, masking, audit)
│   ├── orchestration/      ← invoice workflow runner and state machine
│   ├── models/             ← Pydantic data contracts (Invoice, AgentDecision, ToolCall, AuditEvent…)
│   ├── services/           ← business-logic layer between API and DB
│   ├── mock_systems/       ← simulated enterprise APIs (vendors, POs, payments, approval limits)
│   ├── database/           ← SQLite engine, table definitions, seed loader
│   ├── llm/                ← Granite / watsonx.ai client, prompts, structured-output parser
│   └── utils/              ← logging config, timestamps, validation helpers
│
├── frontend/               ← React dashboard
│   └── src/
│       ├── App.jsx         ← router + layout shell
│       ├── api/            ← backend HTTP client
│       ├── components/     ← reusable UI (risk/status badges, timeline, tool-call table, audit log, approval panel)
│       ├── pages/          ← Dashboard, InvoiceDetails, AuditDetails screens
│       └── styles/         ← dashboard.css
│
├── data/                   ← fixed demo dataset (3 invoice scenarios + vendors, POs, approval limits)
├── tests/                  ← pytest suites: agents, policy engine, governance, permissions, masking, workflow, scenarios
└── docs/                   ← architecture, API contracts, policy matrix, agent permissions, demo script
```

## Architecture (high level)

```
Frontend Dashboard
        |
   Backend API  (backend/api)
        |
 Workflow Orchestrator  (backend/orchestration)
        |
 +-----------------------------------------+
 | Intake | Verification | Risk | Approval |   (backend/agents)
 +-----------------------------------------+
        |
 Governance Middleware  (backend/governance)   ← every tool call passes through here
        |
 Mock Enterprise APIs  (backend/mock_systems)
        |
    Audit Store  (backend/database)
```

## Invoice states

```
RECEIVED → EXTRACTED → VERIFYING → VERIFIED → RISK_REVIEW
RISK_REVIEW → APPROVED | PENDING_APPROVAL | REJECTED | BLOCKED
PENDING_APPROVAL → APPROVED | REJECTED
APPROVED → COMPLETED
any → FAILED
```

Invalid transitions (e.g. `RECEIVED → COMPLETED`, `BLOCKED → COMPLETED`, `REJECTED → APPROVED`)
are rejected by `backend/orchestration/state_machine.py`.

## Governance reason codes

`AMOUNT_ABOVE_LIMIT` · `UNKNOWN_VENDOR` · `DUPLICATE_INVOICE` · `PO_AMOUNT_MISMATCH` ·
`SENSITIVE_DATA_DETECTED` · `UNAUTHORIZED_TOOL_CALL` · `LOW_CONFIDENCE` · `MISSING_REQUIRED_FIELD` ·
`MALFORMED_FIELD` · `INVALID_PURCHASE_ORDER` · `VENDOR_UNVERIFIED` · `AGENT_FAILURE` · `MOCK_SYSTEM_UNAVAILABLE` ·
`INSUFFICIENT_EVIDENCE` · `POLICY_PASSED` — full list in `backend/models/enums.py`, rules in `docs/policy-matrix.md`.

## Out of scope

Real payment execution, real banking/accounting integrations, production authentication,
training a foundation model, multiple enterprise domains, regulatory certification, unlimited agents/tools.

## Getting started (once implemented)

```bash
cp .env.example .env
pip install -r requirements.txt
uvicorn backend.main:app --reload
```

```bash
cd frontend && npm install && npm run dev
```

```bash
pytest tests/
```
