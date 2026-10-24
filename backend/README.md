# backend/

Python FastAPI service. Hosts the HTTP API, the four AI agents, the governance middleware,
the workflow orchestrator, the mock enterprise systems, and the SQLite audit store.

**Key constraint:** agents never call tools directly. Every tool call goes
`agent → governance/tool_call_interceptor → mock_systems`, and every call is logged.

| Path | Purpose |
|------|---------|
| `main.py` | FastAPI app factory. Mounts the routers in `api/`, initializes the database, loads seed data, configures structured JSON logging. |
| `api/` | HTTP route handlers. Thin — they validate input, call a service, return a model. |
| `agents/` | The four agents (Intake, Verification, Policy/Risk, Approval) and their shared base class. |
| `governance/` | Deterministic governance layer: permission allowlist, policy matrix, sensitive-data scanner, tool-call interceptor, decision validator. |
| `orchestration/` | Runs an invoice through the agents in order; owns the invoice state machine. |
| `models/` | Pydantic schemas for every data contract (Invoice, AgentDecision, ToolCall, AuditEvent, Approval) plus enums. |
| `services/` | Business logic between API routes and the database (invoice CRUD, approvals, audit writes, masking). |
| `mock_systems/` | Simulated enterprise APIs: vendor DB, purchase-order DB, payment service, approval-limit service. |
| `database/` | SQLite engine/session, table definitions, seed loader that reads `data/`. |
| `llm/` | watsonx.ai / Granite client, prompt templates, and schema-validated output parser. |
| `utils/` | Logging config, UTC timestamp helpers, generic validation helpers. |

Each subfolder has its own `README.md` with per-file detail.
