# tests/

pytest suites. Run with `pytest tests/` from the repo root. Mock systems are used throughout;
the LLM runs in `MockLLM` mode so tests are deterministic.

| File | Covers |
|------|--------|
| `conftest.py` | Fixtures: fresh in-memory SQLite `session` per test, `ref` (reference data), `demo_invoices` (the four fixtures). |
| `test_mock_systems.py` | Mock vendor/PO/limit lookups return seeded records; unknown IDs raise `NotFound`; outage mode raises `MockSystemUnavailable`; payment service refuses agents and double payment; `agents/` never imports `mock_systems`. |
| `test_audit_trail.py` | Hash chain per invoice, duplicate `event_id` ignored idempotently, out-of-order events flagged not reordered, tampering breaks `verify_chain`, summaries masked before storage. |
| `test_intake_agent.py` | Field extraction from the demo invoices, extraction confidence, flagging missing due date / invalid amount / malformed fields. |
| `test_verification_agent.py` | Unknown vendor, PO amount mismatch, invalid PO, duplicate invoice ID, duplicate vendor+amount combination. |
| `test_policy_engine.py` | Each row of the policy matrix maps to the right risk level, action, and reason code. Thresholds are deterministic. |
| `test_governance.py` | Payment blocked above threshold; high-risk invoice can never auto-complete; every action creates an audit event; explanations reference real evidence IDs. |
| `test_permissions.py` | Agents can only call allowlisted tools; calls without identity/purpose are denied; payment authorization from any agent is blocked and logged. |
| `test_sensitive_data.py` | Bank account / tax ID / names detected and masked in API responses, explanations, and log output; raw values never appear. |
| `test_workflow.py` | State-machine transitions (valid and invalid), early stop on block, continued operation when one agent fails, agent timeout, mock API failure, malformed model output. |
| `test_scenarios.py` | End-to-end runs of the three demo invoices asserting expected risk, governance decision, dashboard state, and audit event sequence. Also duplicate and out-of-order event handling. |

## Target metrics (hackathon)

- 100% of simulated tool calls logged
- 100% of high-risk payments blocked pending approval
- < 10 s per invoice end-to-end, < 1 s per audit event
