# TrustPay — Governed Multi-Agent Invoice Approval Platform

A governance layer for autonomous AI agents that process business invoices. Four specialized
agents (Intake → Verification → Policy/Risk → Approval) collaborate on each invoice while a
deterministic governance layer records every decision and tool call, masks sensitive data,
enforces spending/approval policies, and requires human approval before any high-risk action.

**Core rule:** AI may *recommend*; deterministic governance logic *decides* whether an action is allowed.

Invoices arrive by email (a read-only Gmail inbox) or through the API, run through the agents
automatically, and land on two dashboards that share one backend: a **web dashboard** (React) and
a **phone app** (Expo). A finance approver uses either one to clear what needs a human decision.

## MVP workflow

```
Invoice received → extracted → verified → policy checked → recommendation → human approval → audit record
```

## Demo scenarios

The fixtures in `data/invoices/` are the source of truth; each file's `expected` block holds the
outcome the tests check.

| # | Fixture | Scenario | Expected outcome |
|---|---------|----------|------------------|
| 1 | `low_risk_invoice.json` | Known vendor, matching PO, under the limit | `COMPLETED` — paid automatically (`POLICY_PASSED`) |
| 2 | `policy_violation_invoice.json` | Amount exceeds the agent's approval limit | `PENDING_APPROVAL` — payment withheld until a human approves (`AMOUNT_ABOVE_LIMIT`) |
| 3 | `suspicious_invoice.json` | Unknown vendor, invalid PO, bank data in the invoice | `BLOCKED` — data masked, payment never runs automatically, audit record created |
| 3b | `duplicate_invoice.json` | Same invoice received twice | `BLOCKED` (`DUPLICATE_INVOICE`) |

## Tech stack

| Layer | Choice |
|-------|--------|
| Web dashboard | React 18 + Vite, Recharts, plain CSS (`frontend/src/styles/dashboard.css`) |
| Phone app | Expo SDK 58 (React Native) + Expo Router, `react-native-svg`; runs in Expo Go |
| Backend | Python 3.11+ FastAPI, Pydantic v2 |
| Agent logic | Granite, chosen by `LLM_MODE`: `mock` (default, deterministic), `watsonx` (watsonx.ai), or `ollama` (local Granite) |
| Workflow | Lightweight in-process orchestrator (watsonx Orchestrate optional) |
| Invoice intake | Read-only Gmail API → PDF text parser, with a model fallback that keeps only values written in the document |
| Database | Supabase Postgres (shared); SQLite for local dev and tests |
| Mock enterprise APIs | FastAPI routes + JSON fixtures in `data/` |
| Secrets | `.env` for demo (HashiCorp Vault target) |
| Hosting | Docker Compose locally (OpenShift target) |

## Repository structure

Each folder has its own `README.md` describing its files in detail.

```
TrustPay/
├── README.md               ← this file
├── CLAUDE.md               ← working rules for AI-assisted changes (scope, non-negotiables, conventions)
├── PRODUCT.md              ← who the dashboard is for and what it must do (product context)
├── DESIGN.md               ← the dashboard design system: colours, type, components, rules
├── current_progress.md     ← running log of finished work and what's next
├── .env.example            ← template of required environment variables (DB URL, LLM mode, Gmail, etc.)
├── docker-compose.yml      ← runs backend + frontend containers together
├── requirements.txt        ← Python dependencies for backend/ and tests/
├── pyproject.toml          ← ruff + pytest configuration
├── package.json            ← root scripts: dev (both services), test, lint, reset
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
│   ├── database/           ← engine (Supabase Postgres or SQLite), table definitions, seed loader
│   ├── llm/                ← Granite / watsonx.ai client, prompts, structured-output parser
│   ├── utils/              ← logging config, timestamps, validation helpers
│   └── inbox/              ← Gmail intake: read-only client, OAuth authorize, PDF parser, model fallback, sync, poller
│
├── scripts/                ← make_invoice_pdfs.py renders the fixtures as PDFs for the email demo
│
├── frontend/               ← React web dashboard
│   ├── public/             ← TrustPay logo and icon (SVG + PNG)
│   └── src/
│       ├── App.jsx         ← app window, top bar with pill nav, routes
│       ├── api/            ← backend HTTP client
│       ├── components/     ← charts, badges, reason tags, approval queue, timeline, tool calls, audit log, inbox card
│       ├── pages/          ← Dashboard (overview), InvoiceDetails, AuditDetails
│       └── styles/         ← dashboard.css (the tokens recorded in DESIGN.md)
│
├── mobile/                 ← Expo phone app: Overview / Inbox / Invoices tabs + invoice screen with approve / reject
│
├── data/                   ← fixed demo dataset (4 invoice fixtures + vendors, POs, approval limits)
├── tests/                  ← pytest suites: agents, policy engine, governance, permissions, masking, auto-pay,
│                              workflow, scenarios, inbox, PDF parsing, LLM, database, reliability, performance
└── docs/                   ← architecture, API contracts, policy matrix, agent permissions, demo script, sprint plan
```

## Architecture (high level)

```
 Web dashboard (frontend)    Phone app (mobile)    Gmail inbox (backend/inbox)
                    \                |                 /
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

## Getting started

The backend serves on :8000 (Swagger at `/docs`, health at `/health`), the web dashboard on :5173.

**With Docker** — one command, both services:

```bash
docker compose up --build
```

**Locally** — first-time setup:

```bash
cp .env.example .env
pip install -r requirements.txt
npm install
npm --prefix frontend install
```

Then start both services together:

```bash
npm run dev
```

Or one at a time: `npm run backend` and `npm run frontend`.

The defaults need no accounts or keys: `LLM_MODE=mock` and a local SQLite file
(`DATABASE_URL=sqlite:///./trustpay.db`). To use the shared team database instead, set
`DATABASE_URL` to the Supabase connection string, as described in `.env.example`.

Tests and lint:

```bash
npm test
```

```bash
npm run lint
```

Rerun the demo from a clean slate without restarting anything (`POST /demo/reset`):

```bash
npm run reset
```

Then follow [docs/demo-script.md](docs/demo-script.md).

## Choosing the model

`LLM_MODE` in `.env` picks the agents' model; `/health` reports the active mode.

| `LLM_MODE` | What it does | Needs |
|------------|--------------|-------|
| `mock` (default) | Deterministic canned responses, so the demo never depends on live model behaviour | Nothing |
| `watsonx` | Granite on IBM watsonx.ai (`WATSONX_MODEL_ID`) | `WATSONX_API_KEY`, `WATSONX_PROJECT_ID` |
| `ollama` | Granite served locally by Ollama (`OLLAMA_MODEL`, default `granite3.3:8b`) | `ollama pull granite3.3:8b` |

Whatever the mode, the model only recommends: governance decides, and a failed or low-confidence
answer never leads to automatic payment. Details in [backend/llm/README.md](backend/llm/README.md).

## Phone app (Expo)

`mobile/` is an Expo companion to the web dashboard, with Overview, Inbox and Invoices tabs, a
floating bottom nav, and an invoice screen with approve / reject. It runs in **Expo Go**, so no
native build is needed. The phone must reach the backend over Wi-Fi, so bind uvicorn to the LAN:

```bash
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

```bash
npm --prefix mobile install
npm --prefix mobile start
```

Scan the QR code with the phone. The app finds the backend on the laptop running Expo; see
[mobile/README.md](mobile/README.md) to point it elsewhere.

## Design

Both dashboards follow one design system: a calm white surface, soft grey panels, and a single
indigo for data, with green and red kept for money and risk. Reason codes appear as plain-English
tags. [PRODUCT.md](PRODUCT.md) says who the dashboard is for; [DESIGN.md](DESIGN.md) records the
colours, type, components and rules. Read both before changing either UI.

## Invoices by email (Gmail)

The backend watches a Gmail inbox (read-only) for emails whose attachment is named
`invoice.pdf` — any case — and runs each one through the agents automatically.

The PDF's text is read with a `Label: value` parser first. The model fills in only the fields
the parser missed, and only from masked text. A value is kept only if it actually appears in the
document, and the model is never asked for bank, routing or tax numbers.

1. Google Cloud: create a project, enable the **Gmail API**, create an **OAuth client ID (Desktop app)**, download it to `secrets/credentials.json` (gitignored).
2. `python -m backend.inbox.authorize` — browser consent, writes `secrets/token.json`.
3. `.env`: `INBOX_ENABLED=true`, restart the backend. Poll interval `INBOX_POLL_SECONDS` (60).
4. `python scripts/make_invoice_pdfs.py` → `data/invoices/pdf/*.pdf`; email one to that account as `invoice.pdf`.

The **Inbox** card (on the web dashboard, and as its own tab in the phone app) shows
authorization, the last poll, and a **Check inbox now** button; `GET /inbox/status` and
`POST /inbox/sync` are the API behind it. Details in [backend/inbox/README.md](backend/inbox/README.md).

## Project status

What's done and what's next live in [current_progress.md](current_progress.md); the sprint
breakdown is in [docs/sprint-plan.md](docs/sprint-plan.md). Contributors (human or AI) follow
[CLAUDE.md](CLAUDE.md).
