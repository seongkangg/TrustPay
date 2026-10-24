# frontend/

React dashboard for finance reviewers / compliance officers. Shows only what is needed to
govern invoice processing: status, risk, agent activity, tool calls, policy violations,
pending approvals, and the audit trail.

| Path | What it does |
|------|--------------|
| `package.json` | Frontend dependencies and `dev` / `build` scripts (Vite + React). |
| `src/App.jsx` | Router and layout shell; navigation between Dashboard, Invoice Details, and Audit Details. |
| `src/api/client.js` | Thin fetch wrapper for the backend API (`/invoices`, `/dashboard/summary`, `/approve`, `/reject`, `/audit`…). |
| `src/styles/dashboard.css` | Global styles, consistent risk colors (low = green, medium = amber, high = red), blocked-action emphasis. |

## Components (`src/components/`)

| File | What it shows |
|------|---------------|
| `RiskBadge.jsx` | Low / Medium / High pill with the shared risk colors. |
| `StatusBadge.jsx` | Invoice state badge (RECEIVED … COMPLETED / BLOCKED / FAILED). Blocked is visually loud. |
| `AgentTimeline.jsx` | Chronological agent activity: decisions, confidence scores, governance results, evidence links, blocked actions. |
| `ToolCallTable.jsx` | Every tool call made for an invoice: agent, tool, purpose, allowed/blocked, result summary, timestamp. |
| `AuditLog.jsx` | Immutable event list: actor, action, timestamp, policy result, integrity (hash chain) status. |
| `ApprovalPanel.jsx` | Explicit human approve/reject controls, clearly separated from the AI recommendation. Shows the "why" (reasons + evidence) next to the recommendation. |

## Pages (`src/pages/`)

| File | Screen |
|------|--------|
| `Dashboard.jsx` | Overview: total invoices, risk counts, blocked actions, pending approvals, recent policy violations. |
| `InvoiceDetails.jsx` | Invoice fields (sensitive data masked), current status, risk level, final recommendation, sensitive-data warnings, approval controls, agent timeline, tool calls. |
| `AuditDetails.jsx` | Full audit view for one invoice. |

## Design rules

- Never display raw sensitive data (bank accounts / tax IDs as `****6789`).
- Separate AI recommendation from the final human decision.
- Show "why" next to every major decision.
- Keep raw technical logs off the main dashboard.
