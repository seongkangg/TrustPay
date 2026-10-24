# frontend/

React dashboard for finance reviewers / compliance officers. Shows only what is needed to
govern invoice processing: status, risk, agent activity, tool calls, policy violations,
pending approvals, and the audit trail.

| Path | What it does |
|------|--------------|
| `package.json` | Dependencies and `dev` / `build` / `lint` scripts (Vite 5 + React 18 + react-router 6 + Recharts 2, ESLint 9 flat config). |
| `vite.config.js` | Dev server on 5173; proxies `/invoices`, `/dashboard`, `/governance`, `/inbox`, `/mock`, `/health` to the backend (`API_PROXY_TARGET`, default `http://localhost:8000`). Browser navigations still get the SPA. |
| `public/` | Static brand assets served at the site root: `trustpay-logo.{svg,png}` (shield + wordmark) and `trustpay-icon.{svg,png}` (shield only). The header shows the logo and the browser tab uses the icon. |
| `index.html`, `src/main.jsx` | Entry point; mounts `App` inside a `BrowserRouter`. |
| `eslint.config.js` | ESLint flat config: recommended + react + react-hooks. |
| `src/App.jsx` | App window and top bar (TrustPay logo, centred pill nav, backend health), routes: `/` → Dashboard, `/invoices/:id` → InvoiceDetails, `/invoices/:id/audit` → AuditDetails. |
| `src/api/client.js` | Thin fetch wrapper for every backend endpoint (including `inboxStatus` / `inboxSync`), `ApiError` carrying the contract's error body and HTTP status, and formatting helpers (`fmtMoney`, `fmtTime`, `fmtPct`, `human`). |
| `src/styles/dashboard.css` | Plain CSS. A white window on a grey canvas with soft grey panels; the logo's teal (`--accent`, `--accent-strong`) on data and its navy (`--brand-navy`) on links and primary buttons. Risk colors are tokens (`--risk-low/medium/high`), blocked states share `--blocked`; badges, KPI cards, risk bars, day calendar, tables, timeline, approval panel, approval queue, inbox card. The chart series reuse the same hex values as the tokens. |

## Running

```bash
npm install
npm run dev        # http://localhost:5173, backend expected on :8000
```

The dashboard is read-only: invoices arrive from the Gmail inbox (`backend/inbox/`) and are
processed automatically, so there are no "submit" or "run agents" buttons. The one action a
person takes in the UI is the explicit approve / reject on the invoice page. The Overview
re-fetches the summary, the invoice list and the inbox status every 15 seconds.

To seed data without the inbox, post a fixture from `data/invoices/*.json` to `POST /invoices`
and `POST /invoices/{id}/process` with curl or the API docs at `http://localhost:8000/docs`.

## Components (`src/components/`)

| File | What it shows |
|------|---------------|
| `ReasonTag.jsx` | Plain-English pill for a policy reason code; hover/focus shows a one-line summary. |
| `RiskBadge.jsx` | Low / Medium / High pill with the shared risk colors. |
| `StatusBadge.jsx` | Invoice state badge (RECEIVED … COMPLETED / BLOCKED / FAILED). Blocked is visually loud. |
| `AgentTimeline.jsx` | Chronological agent activity: decisions, confidence scores, governance results, evidence links, blocked actions. |
| `ToolCallTable.jsx` | Every tool call made for an invoice: agent, tool, purpose, allowed/blocked, result summary, timestamp. |
| `AuditLog.jsx` | Immutable event list: actor, action, timestamp, policy result, integrity (hash chain) status. |
| `ApprovalPanel.jsx` | Explicit human approve/reject controls, clearly separated from the AI recommendation. Shows the "why" (reasons + evidence) next to the recommendation. |
| `ApprovalQueue.jsx` | Overview list of invoices in `PENDING_APPROVAL` / `BLOCKED`: vendor, amount, status and risk badges, reason codes when known, link to the invoice page where the decision is made. |
| `SummaryCharts.jsx` | Overview charts fed by `GET /dashboard/summary` and the invoice list: `VolumeChart` (smooth recharts area of `by_day` received, completed as the quiet line), `Sparkline` (SVG line for a KPI card), `RiskBars` (low / medium / high counts and amounts, high risk highlighted), `DayCalendar` (the 14 `by_day` days as a calendar grid, today highlighted). |
| `Icons.jsx` | Small outline SVG icon set for the pill nav and labels. |
| `InboxCard.jsx` | `GET /inbox/status`: authorized or not, last sync, "Check inbox now" (`POST /inbox/sync`, shows the backend's message on 503 `INBOX_NOT_AUTHORIZED`), recent messages with links to their invoices. Renders "Inbox not available" when the backend answers 404. |

## Pages (`src/pages/`)

| File | Screen |
|------|--------|
| `Dashboard.jsx` | Overview inside the app window, top to bottom: **Needs your approval** queue → **Invoice volume** hero (total from `summary.amounts`, % paid, paid / withheld) over the 14-day volume chart → Received / Completed / Blocked cards with sparklines → **Risk mix** bars (with blocked tool calls and sensitive-data count) beside the **Received per day** calendar → **Inbox** card → recent policy violations → invoices table. The pill nav links to these sections by hash. Auto-refreshes every 15 s. |
| `InvoiceDetails.jsx` | Invoice fields (sensitive data masked), current status, risk level, final recommendation, sensitive-data warnings, approval controls (the only write action in the UI), agent timeline, tool calls. |
| `AuditDetails.jsx` | Full audit view for one invoice. |

## Design rules

- Never display raw sensitive data (bank accounts / tax IDs as `****6789`).
- Separate AI recommendation from the final human decision.
- Show "why" next to every major decision.
- Keep raw technical logs off the main dashboard.
