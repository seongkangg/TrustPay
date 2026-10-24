# Architecture

## Component diagram

```
┌──────────────────────────────────────────────────────────────┐
│  Frontend Dashboard  (React / Vite)          frontend/        │
│  Overview · Invoice Detail · Agent Timeline · Audit View      │
└───────────────────────────┬──────────────────────────────────┘
                            │ HTTP/JSON (masked data only)
┌───────────────────────────▼──────────────────────────────────┐
│  Backend API  (FastAPI)                      backend/api      │
│  /invoices  /approve  /reject  /audit  /governance  /dashboard│
└───────────────────────────┬──────────────────────────────────┘
                            │
┌───────────────────────────▼──────────────────────────────────┐
│  Workflow Orchestrator                 backend/orchestration  │
│  invoice_workflow · state_machine · workflow_context          │
└───────────────────────────┬──────────────────────────────────┘
                            │ runs agents in order
┌───────────────────────────▼──────────────────────────────────┐
│  ┌────────┐ ┌──────────────┐ ┌─────────────┐ ┌──────────┐    │
│  │ Intake │→│ Verification │→│ Policy/Risk │→│ Approval │    │
│  └────────┘ └──────────────┘ └─────────────┘ └──────────┘    │
│  backend/agents          (LLM via backend/llm, mock or real)  │
└───────────────────────────┬──────────────────────────────────┘
                            │ EVERY tool call & decision
┌───────────────────────────▼──────────────────────────────────┐
│  Governance Middleware                  backend/governance    │
│  permission_checker · policy_engine · sensitive_data_scanner  │
│  tool_call_interceptor · decision_validator · governance_engine│
└──────────┬────────────────────────────────────┬──────────────┘
           │ allowed calls only                 │ every outcome
┌──────────▼──────────────────┐   ┌─────────────▼──────────────┐
│  Mock Enterprise APIs       │   │  Audit Store (SQLite)      │
│  backend/mock_systems       │   │  backend/database          │
│  vendors · POs · limits ·   │   │  append-only, hash-chained │
│  payments                   │   │  audit_events              │
└─────────────────────────────┘   └────────────────────────────┘
```

## Component responsibilities

| Component | Layer | Folder | Notes |
|-----------|-------|--------|-------|
| Dashboard | Frontend | `frontend/` | Read-only except the explicit human approve/reject action. Never receives raw sensitive values. |
| REST API | Backend | `backend/api/` | Thin routers; all responses pass through `masking_service`. |
| Gmail intake | Ingestion | `backend/inbox/` | Read-only poll for `invoice.pdf` attachments → PDF text → fields → the same `create → process` path as the API. PDF bytes are never stored. |
| Orchestrator | Orchestration | `backend/orchestration/` | In-process sequential runner. Stand-in for watsonx Orchestrate. Owns the state machine. |
| Agents | Agent services | `backend/agents/` | Stateless; receive `WorkflowContext`, return `AgentDecision`. No direct tool access. |
| LLM client | Agent services | `backend/llm/` | Granite via watsonx.ai, or `MockLLM` returning fixture responses. |
| Governance | Governance middleware | `backend/governance/` | Deterministic, no LLM. The only path to mock systems and the audit store. |
| Mock systems | Mock enterprise APIs | `backend/mock_systems/` | Backed by `data/*.json`. Failure modes switchable for tests. |
| Database | Database / audit store | `backend/database/` | SQLite file for the prototype. `audit_events` has no update/delete path. |
| Observability | Observability | `backend/utils/logging_config.py` | Structured JSON logs with correlation IDs; masked. |
| Secrets | Secrets manager | `.env` | Environment variables for the demo; Vault is the target. |

## Request flow for one invoice

1. An invoice arrives — by email (the inbox poller finds an `invoice.pdf` attachment, extracts the text, parses labelled fields) or via `POST /invoices` — and is stored as an `InvoiceUpload` → status `RECEIVED`, emits `invoice_received`.
2. Sensitive-data scanner masks bank/tax fields **before** anything is persisted or passed to a model → `sensitive_data_masked` if anything was found.
3. `POST /invoices/{id}/process` starts `invoice_workflow`.
4. Intake agent → `document_parser` → `EXTRACTED`, emits `invoice_extracted`.
5. Verification agent → `vendor_lookup`, `po_lookup` → `VERIFYING` → `VERIFIED`, emits vendor/PO/duplicate events.
6. Policy/Risk agent → `approval_limit_lookup`, `risk_rules` → `RISK_REVIEW`, emits `risk_assigned`.
7. Approval agent → recommendation → emits `recommendation_generated`.
8. Governance engine decides the outcome deterministically:
   - low risk & under threshold → `payment_authorize` (governance layer only) → `APPROVED` → `COMPLETED`
   - otherwise → `payment_blocked` + `approval_requested` → `PENDING_APPROVAL` or `BLOCKED`
9. Human `POST /approve` or `/reject` → `human_decision_recorded` → `APPROVED`/`REJECTED`.
10. Every step appends to the hash-chained audit trail → `audit_record_created`.

## Real vs. simulated

| Capability | Prototype | Production target |
|------------|-----------|-------------------|
| Invoice extraction | Granite via watsonx.ai, or `MockLLM` fixtures | watsonx.ai / Granite |
| Agent coordination | In-process Python orchestrator | watsonx Orchestrate |
| Risk / compliance evaluation | Deterministic `policy_engine` | watsonx.governance for monitoring + explainability metrics |
| Vendor / PO / payment systems | JSON-backed mock FastAPI services | ERP / AP system integrations |
| Payment execution | Simulated `payment_authorize` — nothing moves | Real payment rails (explicitly out of scope) |
| Agent identity / auth | Simulated agent identities on each call | Production IAM |
| Secrets | `.env` | HashiCorp Vault |
| Hosting | Docker Compose locally | Red Hat OpenShift |
| Observability | Structured JSON logs | IBM Instana / observability stack |
| Audit integrity | SHA-256 hash chain | Signed, externally anchored log |

## IBM technology mapping

| IBM technology | Role in the prototype |
|----------------|----------------------|
| watsonx.ai / Granite | Powers extraction, verification summaries, and recommendations in the agents |
| watsonx Orchestrate | Target for agent/workflow coordination (orchestrator is swappable) |
| watsonx.governance | Evaluates risk, policy compliance, explainability, and agent behavior |
| Red Hat OpenShift | Hosts agent services and governance layer |
| IBM observability tools | Tracks agent actions, latency, failures, suspicious behavior |
| HashiCorp Vault | Secures API keys, credentials, and protected system access |

## Deployment (hackathon)

One repository, two containers via `docker-compose.yml`:

- `backend` — FastAPI + SQLite volume, port 8000
- `frontend` — Vite dev server (or static build behind nginx), port 5173

## Non-functional requirements

- Every decision traceable to evidence IDs that resolve to real tool calls / scans.
- Agents cannot call enterprise tools directly; 100% of tool calls pass through governance and are logged.
- High-risk actions never execute automatically.
- No unmasked sensitive field in any API response, log line, or model prompt.
- Duplicate and out-of-order events cannot corrupt the audit chain.
- One agent failing marks the invoice `FAILED` with reason; the service keeps running.
- Targets: < 10 s per invoice end-to-end, < 1 s per audit event write.
