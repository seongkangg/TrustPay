# tests/

pytest suites. Run with `pytest tests/` from the repo root. Mock systems are used throughout;
the LLM runs in `MockLLM` mode so tests are deterministic.

| File | Covers |
|------|--------|
| `__init__.py` | Forces `LLM_MODE=mock` before anything reads settings, so the suite never calls a real model no matter what the developer's `.env` says. |
| `conftest.py` | Fixtures: fresh in-memory SQLite `session` per test, `ref`, `demo_invoices`, `fixture_by_id`. Helpers: `run_agents(gov, fixture, llm=, upto=)` drives ingest → the four agents; `insert_invoice_row` persists a fixture as already processed (for duplicate checks). |
| `test_llm.py` | Output parser rejects malformed/off-schema model output; `MockLLM` is deterministic and follows the prompt's context; factory defaults to mock and refuses watsonx without credentials. |
| `test_approval_agents.py` | Policy/Risk agent assigns risk from the engine with LIMIT/RULES/POLICY evidence; Approval agent derives its recommendation from policy, a model can make it more cautious but never more permissive, invalid model output → escalate at 0.5; all four fixtures reach their expected risk / reason codes / recommendation through the agent chain. |
| `test_mock_systems.py` | Mock vendor/PO/limit lookups return seeded records; unknown IDs raise `NotFound`; outage mode raises `MockSystemUnavailable`; payment service refuses agents and double payment; `agents/` never imports `mock_systems`. |
| `test_audit_trail.py` | Hash chain per invoice, duplicate `event_id` ignored idempotently, out-of-order events flagged not reordered, tampering breaks `verify_chain`, summaries masked before storage. |
| `test_intake_agent.py` | Field extraction from the demo invoices, extraction confidence, flagging missing due date / invalid amount / malformed fields. |
| `test_verification_agent.py` | Unknown vendor, PO amount mismatch, invalid PO, duplicate invoice ID, duplicate vendor+amount combination. |
| `test_policy_engine.py` | Each row of the policy matrix maps to the right risk level, action, and reason code. Thresholds are deterministic. |
| `test_governance.py` | Payment blocked above threshold; high-risk invoice can never auto-complete; every action creates an audit event; explanations reference real evidence IDs. |
| `test_permissions.py` | Agents can only call allowlisted tools; calls without identity/purpose are denied; payment authorization from any agent is blocked and logged. |
| `test_sensitive_data.py` | Bank account / tax ID / names detected and masked in API responses, explanations, and log output; raw values never appear. |
| `test_workflow.py` | State-machine transitions (valid and invalid), low-risk run to COMPLETED with the exact fixture event sequence, processing twice rejected, intake failure → FAILED + escalated, vendor system down → safe PENDING_APPROVAL, timeline merge ordering, human approve/reject, human limit enforced, decisions refused on unprocessed/terminal invoices. |
| `test_scenarios.py` | All four fixtures through the HTTP API in demo order asserting status, risk, reason codes, recommendation, masked fields, exact audit sequence, and the dashboard summary; the spec's worked example with a raw-secret sweep over every response; human approve/reject round-trips; error body format and status codes; list filters; governance dry-run audited; mock inspection routes; `/health`. |

| `test_reliability.py` | Model timeout and unexpected model exceptions end in `FAILED` + escalated with the chain intact; PO / approval-limit / payment service outages escalate rather than fail; a payment outage during human approval is a clean 503 that can be retried once the service is back. |
| `test_performance.py` | Each demo invoice processes in < 10 s over HTTP; 50 audit appends each < 1 s. |

## Target metrics (hackathon)

- 100% of simulated tool calls logged
- 100% of high-risk payments blocked pending approval
- < 10 s per invoice end-to-end, < 1 s per audit event
