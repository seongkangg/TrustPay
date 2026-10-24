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
| `src/app/(tabs)/_layout.js` | Overview / Inbox / Invoices tabs with `BubbleNav` as the tab bar; the round button opens the next invoice awaiting approval. |
| `src/app/(tabs)/index.js` | Overview, same design as the web dashboard: **Needs your approval** queue → **Invoice volume** hero (total in whole dollars, % paid, paid / withheld) over the 14-day teal volume chart → Received / Completed / Blocked cards with sparklines → **Risk mix** bars → **Received per day** calendar (UTC days) → recent policy violations. |
| `src/app/(tabs)/inbox.js` | Inbox tab: `InboxCard` (`GET /inbox/status`, "Check inbox now" → `POST /inbox/sync`) and recent messages. |
| `src/app/(tabs)/invoices.js` | Invoices tab: every invoice with status, risk, masked flag and amount, filtered by All / Pending / Accepted / Rejected (pill bar with counts; Pending = not yet decided, Accepted = approved or completed, Rejected = rejected; failed invoices show under All only). Each row opens the invoice screen. |
| `src/app/invoices/[id].js` | One invoice: status and risk, masked fields, extraction, **AI recommendation vs. human decision** (approve / reject with reviewer + note), agent timeline, tool calls. |
| `src/api/client.js` | Fetch wrapper mirroring `frontend/src/api/client.js`; picks the backend URL (see below). |
| `src/data.js` | `DashboardProvider` / `useDashboard`: summary, invoices and inbox status fetched once for all tabs, polled every 15 s, pull to refresh. |
| `src/components/ui.js`, `Charts.js` | Sentence-case badges, grey panels, count pills, pill buttons with press feedback, alerts, the TrustPay logo (shield + wordmark, drawn in SVG); SVG volume chart and sparklines, View-based risk bars and the day calendar. |
| `src/components/BubbleNav.js`, `InboxCard.js` | Floating bottom nav: a white pill of tabs with a grey bubble that springs to the active tab, plus a black round action button with the waiting count. The Gmail inbox card. |
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

If the Overview shows a red error, it includes the backend URL it tried, so you can tell at a
glance whether the host or the bind address is the problem.

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
