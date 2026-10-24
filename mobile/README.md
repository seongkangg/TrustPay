# mobile/

Expo (React Native) companion to the web dashboard in `frontend/`. Same backend, same screens,
same rule: the dashboard is read-only except the explicit human approve / reject on an invoice.
Runs in **Expo Go** — every dependency is one Expo Go already bundles, so no native build is needed.

| Path | What it does |
|------|--------------|
| `package.json` | Expo SDK 58, Expo Router, `react-native-svg` (trend chart). `start` / `lint` scripts. |
| `app.json` | App name, `trustpay://` scheme, `expo-router` plugin. |
| `.env.example` | `EXPO_PUBLIC_API_URL` — only needed when the backend is not on the laptop running Expo. |
| `src/app/_layout.js` | Root stack: the tab group and the invoice screen, inside `DashboardProvider`. |
| `src/app/(tabs)/_layout.js` | Overview / Inbox / Invoices tabs with `BubbleNav` as the tab bar. The Inbox tab shows the number of invoices waiting for a human decision; the round button opens the next one. |
| `src/app/(tabs)/index.js` | Overview, same design as the web dashboard: **Invoice volume** hero (total in whole dollars, % paid, paid / withheld) over the 14-day teal volume chart (its line and fill draw in left to right over 900ms each time the tab opens; a short fade with Reduce Motion; touch and drag to scrub day by day with a cursor and a counts card, like the desktop tooltip) → Received / Completed / Blocked cards with sparklines → **Risk mix** bars (grow up from the baseline, staggered, each time the tab opens) → **Received per day** calendar (UTC days) → recent policy violations. The approval list lives on the Inbox tab. |
| `src/app/(tabs)/inbox.js` | Inbox tab: a summary of what waits on you (count, money on hold, blocked) or an "All caught up" card, the waiting invoices (`ApprovalQueue`), then the email inbox (`InboxCard`). |
| `src/app/(tabs)/invoices.js` | Invoices tab: a summary card (total amount and count for the current filter; on All, a Pending / Accepted / Rejected split bar), then invoices grouped by day ("Today", "Yesterday", "Oct 22") with a vendor-initials avatar, ID and time, status / risk / masked badges and the amount. A three-line header button filters by All / Pending / Accepted / Rejected (Pending = not yet decided, Accepted = approved or completed, Rejected = rejected; failed only under All; teal dot when filtered). Shows 8 at a time with a "Show 8 more · n left" pill (and "Show less"); a new filter resets to the first 8. Each row opens the invoice screen. |
| `src/app/invoices/[id].js` | One invoice, built around the decision: vendor, amount and due date (overdue flagged); a banner saying where it stands; the **AI recommendation** (verdict, a bar chart of confidence by agent step, reason tags, why, evidence on demand); the **source document** as a **Download PDF** button (`GET /invoices/{id}/document.pdf`: the original PDF with bank, routing and tax numbers blacked out when `has_source_pdf`, else a masked copy; opened in the phone's viewer to save or share); reviewer and note; then invoice details (masked fields labelled), tool calls (collapsed, with a summary) and the activity timeline (latest steps first, "Show all"). While a decision is needed, **Approve / Reject** sit in a bar pinned to the bottom, each behind a confirm. |
| `src/api/client.js` | Fetch wrapper mirroring `frontend/src/api/client.js`; picks the backend URL (see below). |
| `src/data.js` | `DashboardProvider` / `useDashboard`: summary, invoices and inbox status fetched once for all tabs, polled every 15 s, pull to refresh. |
| `src/useReduceMotion.js` | The live system Reduce Motion setting, shared by the charts and rolling numbers. |
| `src/components/ui.js`, `Charts.js` | Sentence-case badges, grey panels, count pills, pill buttons with press feedback, alerts, the TrustPay logo (shield + wordmark, drawn in SVG); SVG volume chart and sparklines, View-based risk bars and the day calendar. |
| `src/components/BubbleNav.js`, `InboxCard.js` | Floating bottom nav: a white pill of tabs with a grey bubble that springs to the active tab, an optional count badge on a tab icon's top-right corner, and a navy round action button. The Gmail inbox card: connection dot (Connected / Not authorized / Off), last checked time, the last check as four stats, "Check inbox now". |
| `src/components/FilterMenu.js` | The header filter button (three lines, teal dot when filtered) and its menu, which scales in from the top-right corner. |
| `src/components/ApprovalQueue.js` | Waiting invoices as rows in one card: vendor avatar, vendor and amount, ID and how long it has waited, status / risk and up to two reason tags (+n more), and a chevron to the invoice screen. |
| `src/components/RollingText.js` | `RollingText` / `useRolling`: a figure that rolls to its new value over 300ms (interruptible) instead of jumping; used by the Overview hero while scrubbing the chart. |
| `src/components/ConfidenceChart.js` | Bar chart of confidence by agent step (Intake → Verify → Risk → Approval): bar height = that step's confidence, value on top, amber below the policy threshold (dashed line, from `GET /mock/thresholds`); bars grow in on open. |
| `src/components/VendorAvatar.js` | Round vendor badge with initials in a pale tint picked stably from the name; shared by the Invoices and Inbox tabs. |
| `src/theme.js` | The tokens from `frontend/src/styles/dashboard.css` / `DESIGN.md` (the logo's teal `accent` and navy `brandNavy`, `panel`, `--risk-*`, `--blocked`, `--ok`) plus the shared radii. |

## Running on an iPhone with Expo Go

1. Install **Expo Go** from the App Store. Phone and laptop must be on the same Wi-Fi.
2. Start the backend so it listens on the LAN, not just localhost (the default `uvicorn` bind
   is `127.0.0.1`, which the phone cannot reach), and allow the phone's origin through CORS is
   not needed (native fetch has no CORS):

   ```bash
   python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
   ```

3. Start Expo and scan the QR code with the iPhone camera:

   ```bash
   npm --prefix mobile install
   npm --prefix mobile start
   ```

### How the app finds the backend

`src/api/client.js` uses `EXPO_PUBLIC_API_URL` when set. Otherwise it takes the host that Expo Go
loaded the JavaScript bundle from (your laptop's LAN IP) and calls port **8000** on it. So when
uvicorn runs on the same laptop as `expo start`, nothing needs configuring. If the backend lives
elsewhere, copy `.env.example` to `.env` and set the URL, then restart `expo start`.

If the Overview shows a red error, the backend URL it tried is logged to the dev console
(Metro / Expo logs), so you can tell whether the host or the bind address is the problem.

## Checks

```bash
npm --prefix mobile run lint
npx --prefix mobile expo export --platform ios   # compiles the bundle without a device
```

## Design rules (same as `frontend/README.md`)

- Never display raw sensitive data (bank accounts / tax IDs arrive masked as `****6789`).
- Separate the AI recommendation from the final human decision.
- Show "why" next to every major decision.
- Keep raw technical logs off the overview; they live on the invoice screen.
