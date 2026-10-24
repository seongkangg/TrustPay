# docs/

Design documents the team agrees on **before** coding. These are the highest-priority
hackathon deliverables alongside the data schemas and demo data.

| File | What it contains |
|------|------------------|
| `architecture.md` | Component diagram (Frontend → API → Orchestrator → Agents → Governance → Mock APIs → Audit Store), what is real vs. simulated, IBM technology mapping (watsonx.ai/Granite, watsonx Orchestrate, watsonx.governance, OpenShift, observability, HashiCorp Vault), deployment layout. |
| `api-contracts.md` | Every backend endpoint and mock endpoint: request/response bodies, status codes, errors, authorization behavior, audit events generated. |
| `policy-matrix.md` | The full governance policy matrix: condition → risk → action → reason code. Risk thresholds and approval limits. Sensitive-data handling rules (what is masked where, who may see raw values, retention). |
| `agent-permissions.md` | Agent responsibility matrix (responsible for / not allowed to), per-agent inputs, outputs, allowed and forbidden tools, required evidence, failure behavior, confidence requirements, escalation conditions. |
| `demo-script.md` | Step-by-step walkthrough of the three demo scenarios: what to click, what the dashboard should show, what the audit log should contain, and the talking points for each. |
