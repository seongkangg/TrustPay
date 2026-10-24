# backend/orchestration/

Runs one invoice through the four agents in sequence and keeps the invoice state consistent.
This is the lightweight stand-in for watsonx Orchestrate in the prototype.

| File | What it does |
|------|--------------|
| `invoice_workflow.py` | The pipeline: Intake → Verification → Policy/Risk → Approval. After each agent it hands the decision to `governance_engine`, advances the state machine, and writes audit events. Stops early and escalates on any blocked action, failed agent, or timeout. Continues operating if one agent fails (marks `FAILED` with reason rather than crashing). |
| `state_machine.py` | Valid invoice states and transitions. Raises on invalid transitions (`RECEIVED → COMPLETED`, `BLOCKED → COMPLETED`, `REJECTED → APPROVED`, …). |
| `workflow_context.py` | Mutable per-invoice context passed between agents: the invoice, accumulated decisions, tool calls, evidence IDs, scan results, current risk level, and correlation ID. |

## States

```
RECEIVED, EXTRACTED, VERIFYING, VERIFIED, RISK_REVIEW,
PENDING_APPROVAL, APPROVED, REJECTED, BLOCKED, COMPLETED, FAILED
```

## Event sequence emitted during a run

```
invoice_received → invoice_extracted → vendor_lookup_requested → vendor_verified
→ purchase_order_checked → risk_assigned → recommendation_generated
→ approval_requested | payment_blocked → human_decision_recorded → audit_record_created
```
