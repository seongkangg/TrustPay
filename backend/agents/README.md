# backend/agents/

The four cooperating agents. Each agent receives a `WorkflowContext`, may request tool calls
*through the governance layer only*, and returns an `AgentDecision` with a confidence score
and evidence IDs.

| File | Agent | Responsible for | Allowed tools | NOT allowed to |
|------|-------|-----------------|---------------|----------------|
| `base_agent.py` | — | Abstract base: agent identity, `request_tool()` helper that routes through `governance/tool_call_interceptor`, LLM call wrapper, decision builder, failure behavior (stop + escalate on error). | — | Call `mock_systems` directly |
| `intake_agent.py` | Intake | Extract invoice fields (invoice ID, vendor name/ID, amount, currency, due date, PO number, bank account, tax ID) from the uploaded document. Reports extraction confidence and flags missing/malformed fields. | `document_parser` | Approve, reject, or execute payments |
| `verification_agent.py` | Verification | Compare invoice to vendor and PO records. Detect unknown vendors, amount mismatches, invalid POs, duplicate invoice IDs, duplicate vendor/amount combos. | `vendor_lookup`, `po_lookup` | Change vendor or PO records |
| `policy_risk_agent.py` | Policy / Risk | Check approval thresholds, vendor verification status, data-access permissions, suspicious conditions. Assign **low / medium / high** risk with explicit reason codes. | `approval_limit_lookup`, `risk_rules` | Approve payment |
| `approval_agent.py` | Approval | Produce **Approve / Reject / Escalate** recommendation with confidence score. Must escalate anything high-risk — cannot complete payment without a human. | `approval_request_create` | Execute high-risk actions |

## Rules all agents follow

- Every tool call carries agent identity + purpose and is checked against the allowlist.
- Model output must be structured JSON validated against a schema (`llm/output_parser.py`).
- Factual claims require evidence IDs; unsupported reasoning is rejected by `governance/decision_validator.py`.
- Confidence is advisory; it never overrides governance policy.
- If evidence is missing or a call errors, the agent stops and escalates rather than guessing.
