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
| `src/App.jsx` | Desktop shell inside `DashboardProvider`: a left sidebar (TrustPay logo, Overview / Inbox / Invoices with a red waiting count on Inbox, backend health at the foot; it folds into a top bar on narrow screens) beside the full-width page; routes: `/` → Dashboard, `/inbox` → Inbox, `/invoices` → Invoices, `/invoices/:id` → InvoiceDetails, `/invoices/:id/audit` → AuditDetails. The same three pages as the phone app. |
| `src/api/client.js` | Thin fetch wrapper for every backend endpoint (including `inboxStatus` / `inboxSync`, `thresholds` from `GET /mock/thresholds`, and `downloadDocument` which fetches `GET /invoices/{id}/document.pdf` and saves it, so the dev proxy forwards it), `ApiError` carrying the contract's error body and HTTP status, and formatting helpers (`fmtMoney`, `fmtTime`, `fmtAgo`, `fmtPct`, `human`). |
| `src/data.jsx` | `DashboardProvider` / `useDashboard`: summary, invoices and inbox status fetched once for every page and the nav's waiting count, polled every 15 s. |
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
| `ApprovalPanel.jsx` | Earlier combined recommendation + approve/reject panel; no longer used by a page (the review page builds its own recommendation and decision panel). |
| `ApprovalQueue.jsx` | Inbox page list of invoices in `PENDING_APPROVAL` / `BLOCKED`, as a table: vendor and ID, how long it has waited, status / risk and up to two reason tags, the amount, and a Review button (blocked rows tinted). |
| `SummaryCharts.jsx` | Overview charts fed by `GET /dashboard/summary` and the invoice list: `VolumeChart` (smooth recharts area of `by_day` received, completed as the quiet line, dashed day grid; `onHover` reports the day under the pointer), `Sparkline` (SVG line for a KPI card), `RiskBars` (low / medium / high counts and amounts in a teal ramp), `DayCalendar` (the 14 `by_day` days as a calendar grid, today highlighted). |
| `Icons.jsx` | Small outline SVG icon set for the pill nav, buttons and labels (home, inbox, list, calendar, arrows, chevrons, check, x). |
| `ConfidenceChart.jsx` | Review page bar chart of confidence by agent step (Intake → Verify → Risk → Approval), value on top, amber below the policy threshold (dashed line from `GET /mock/thresholds`). |
| `RollingNumber.jsx` | `RollingNumber` / `useRolling`: a figure that rolls to its new value over 300 ms (interruptible) instead of jumping; the Overview hero while hovering the chart. |
| `VendorAvatar.jsx` | Round vendor initials in a stable pale tint. |
| `PageHeader.jsx` | Page title and one-line description at the top of Overview, Inbox and Invoices. |
| `InboxCard.jsx` | `GET /inbox/status`: authorized or not, last sync, "Check inbox now" (`POST /inbox/sync`, shows the backend's message on 503 `INBOX_NOT_AUTHORIZED`) and the last sync result, as on the phone. Renders "Inbox not available" when the backend answers 404. |

## Pages (`src/pages/`)

| File | Screen |
|------|--------|
| `Dashboard.jsx` | Overview: **Invoice volume** hero (total from `summary.amounts`, % paid, paid / withheld) over the 14-day volume chart; hovering a day rolls the hero to that day's `by_day` amounts → Received / Completed / Blocked cards with sparklines → **Risk mix**, **Received per day** and **Recent policy violations** side by side. |
| `Inbox.jsx` | **Needs your approval** (count and money on hold, then the queue; "All caught up" when empty) beside the **Email inbox** card. |
| `Invoices.jsx` | Summary strip (total, count, pending / accepted / rejected split) → segmented filters All / Pending / Accepted / Rejected with counts → a table (vendor, received, status, risk, AI recommendation, amount), 12 rows at a time with Show more. Rows open the invoice page. |
| `InvoiceDetails.jsx` | Review page in two columns. Left: vendor, amount and due date (overdue flagged), a status banner, the **AI recommendation** (verdict, confidence-by-step chart, reason tags, why, what to do, evidence on demand), the **source document** PDF download (redacted original, else masked copy), invoice details (masked fields labelled), activity (latest steps, Show all) and collapsed tool calls. Right, sticky: the **decision** panel (reviewer, note, Reject / Approve behind a confirm), the only write action in the UI. |
| `AuditDetails.jsx` | Full audit view for one invoice. |

## Design rules

- Never display raw sensitive data (bank accounts / tax IDs as `****6789`).
- Separate AI recommendation from the final human decision.
- Show "why" next to every major decision.
- Keep raw technical logs off the main dashboard.
