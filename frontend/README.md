# frontend/

React dashboard for finance reviewers / compliance officers. Shows only what is needed to
govern invoice processing: status, risk, agent activity, tool calls, policy violations,
pending approvals, and the audit trail.

| Path | What it does |
|------|--------------|
| `package.json` | Dependencies and `dev` / `build` / `lint` scripts (Vite 5 + React 18 + react-router 6, ESLint 9 flat config). |
| `vite.config.js` | Dev server on 5173; proxies `/invoices`, `/dashboard`, `/governance`, `/mock`, `/health` to the backend (`VITE_API_BASE_URL`, default `http://localhost:8000`); allows importing the demo fixtures from `../data`. |
| `index.html`, `src/main.jsx` | Entry point; mounts `App` inside a `BrowserRouter`. |
| `eslint.config.js` | ESLint flat config: recommended + react + react-hooks. |
| `src/App.jsx` | Top bar with backend health, routes: `/` → Dashboard, `/invoices/:id` → InvoiceDetails, `/invoices/:id/audit` → AuditDetails. |
| `src/api/client.js` | Thin fetch wrapper for every backend endpoint, `ApiError` carrying the contract's error body, and formatting helpers (`fmtMoney`, `fmtTime`, `fmtPct`, `human`). |
| `src/styles/dashboard.css` | Plain CSS. Risk colors are tokens (`--risk-low/medium/high`), blocked states share `--blocked`; badges, tiles, tables, timeline, approval panel. |

## Running

```bash
npm install
npm run dev        # http://localhost:5173, backend expected on :8000
```

The Overview page has a **Submit a demo invoice** strip that posts each fixture from
`data/invoices/*.json` to `POST /invoices` and then `POST /invoices/{id}/process` — the same
files the tests assert on, so the demo and the test suite can never drift apart.

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
