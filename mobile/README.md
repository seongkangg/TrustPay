# mobile/

Expo (React Native) companion to the web dashboard in `frontend/`. Same backend, same screens,
same rule: the dashboard is read-only except the explicit human approve / reject on an invoice.
Runs in **Expo Go** — every dependency is one Expo Go already bundles, so no native build is needed.

| Path | What it does |
|------|--------------|
| `package.json` | Expo SDK 58, Expo Router, `react-native-svg` (trend chart). `start` / `lint` scripts. |
| `app.json` | App name, `trustpay://` scheme, `expo-router` plugin. |
| `.env.example` | `EXPO_PUBLIC_API_URL` — only needed when the backend is not on the laptop running Expo. |
| `src/app/_layout.js` | Root stack navigator. |
| `src/app/index.js` | Overview: **Needs your approval** queue → count and amount tiles → risk / status bar charts and a 14-day trend → **Inbox** card (`GET /inbox/status`, "Check inbox now" → `POST /inbox/sync`) → recent policy violations → invoice list. Pull to refresh; auto-refreshes every 15 s. |
| `src/app/invoices/[id].js` | One invoice: status and risk, masked fields, extraction, **AI recommendation vs. human decision** (approve / reject with reviewer + note), agent timeline, tool calls. |
| `src/api/client.js` | Fetch wrapper mirroring `frontend/src/api/client.js`; picks the backend URL (see below). |
| `src/components/ui.js`, `Charts.js` | Badges, cards, tiles, alerts; View-based bar charts and an SVG line chart. |
| `src/theme.js` | The same hex values as `frontend/src/styles/dashboard.css` (`--risk-*`, `--blocked`, `--ok`, `--pending`). |

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
