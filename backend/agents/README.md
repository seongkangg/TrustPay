# backend/agents/

The four cooperating agents. Each agent receives a `WorkflowContext`, may request tool calls
*through the governance layer only*, and returns an `AgentDecision` with a confidence score
and evidence IDs.

| File | Agent | Responsible for | Allowed tools | NOT allowed to |
|------|-------|-----------------|---------------|----------------|
| `base_agent.py` | — | Abstract base: agent identity, `request_tool()` helper that routes through `governance/tool_call_interceptor`, LLM call wrapper, decision builder, failure behavior (stop + escalate on error). | — | Call `mock_systems` directly |
| `intake_agent.py` | Intake | Extract invoice fields (invoice ID, vendor name/ID, amount, currency, due date, PO number, bank account, tax ID) from the uploaded document. Reports extraction confidence and flags missing/malformed fields. | `document_parser` | Approve, reject, or execute payments |
| `verification_agent.py` | Verification | Compare invoice to vendor and PO records. With no vendor ID but a vendor name, looks the name up (exact after normalization) and adopts the matched ID. Detect unknown vendors, amount mismatches, invalid POs, duplicate invoice IDs, duplicate vendor/amount combos. | `vendor_lookup`, `po_lookup` | Change vendor or PO records |
| `policy_risk_agent.py` | Policy / Risk | Check approval thresholds, vendor verification status, data-access permissions, suspicious conditions. Assign **low / medium / high** risk with explicit reason codes. | `approval_limit_lookup`, `risk_rules` | Approve payment |
| `approval_agent.py` | Approval | Produce **Approve / Reject / Escalate** recommendation with confidence score. Must escalate anything high-risk — cannot complete payment without a human. | `approval_request_create` | Execute high-risk actions |
| `explanations.py` | — | Reviewer-facing explanation for the Approval Agent: one plain-English reason per flag (what was found, why it matters, what to check) and a numbered next step, built only from recorded evidence — no model text. | — | Call the LLM or any tool |

## How an agent runs

`BaseAgent.run(ctx)` wraps `_run(ctx)`. Inside `_run` an agent may only:

- `request_tool(ctx, tool, purpose, **params)` → `GovernanceEngine.call_tool` (sets `ctx.unauthorized_tool_call` / `ctx.mock_unavailable` and collects evidence IDs)
- `ask(prompt, Schema)` → model call, schema-validated; returns `None` on any failure
- `record(ctx, event_type, severity, …)` → `GovernanceEngine.record`
- `decide(ctx, …)` → `GovernanceEngine.accept_decision`, which validates and persists

Any exception inside `_run` becomes an `agent_failed` event plus an `agent_failed` decision citing POLICY-015, so the workflow still reaches a safe terminal state.

Where the model is used — and where it is not:

| Agent | Deterministic | Model (advisory) |
|-------|---------------|------------------|
| Intake | `document_parser`, missing/malformed checks | per-field confidence |
| Verification | vendor / PO / duplicate lookups (confidence 1.0) | one-sentence summary |
| Policy/Risk | the policy engine assigns risk | reviewer-facing explanation sentence |
| Approval | duplicate → reject, auto-allowed → approve, else escalate | confidence, reasons, next step; may turn approve → escalate, never the reverse |

## Rules all agents follow

- Every tool call carries agent identity + purpose and is checked against the allowlist.
- Model output must be structured JSON validated against a schema (`llm/output_parser.py`).
- Factual claims require evidence IDs; unsupported reasoning is rejected by `governance/decision_validator.py`.
- Confidence is advisory; it never overrides governance policy.
- If evidence is missing or a call errors, the agent stops and escalates rather than guessing.
