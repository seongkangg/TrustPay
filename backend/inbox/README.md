# backend/inbox/

Gmail intake. Watches one mailbox (read-only) for emails whose attachment is named
`invoice.pdf` (any case), pulls the PDF, parses it, and runs it through the normal
`InvoiceService.create → process` path — so an emailed invoice gets exactly the same masking,
agents, policy, and audit trail as one posted to the API.

| File | What it does |
|------|--------------|
| `__init__.py` | `InboxMessage`, `InboxError`, `is_invoice_attachment(name)` (the detection rule). |
| `gmail_client.py` | `GmailClient` over the Gmail v1 API: `list_candidates(days)` (`has:attachment filename:pdf newer_than:Nd`), `fetch(id)` (walks MIME parts for `invoice.pdf`, downloads and decodes it). Scope `gmail.readonly`; the mailbox is never modified. `from_files()` loads/refreshes the token. |
| `authorize.py` | `python -m backend.inbox.authorize` — one-time OAuth consent in the browser; writes the token file. |
| `pdf_parser.py` | `extract_text(bytes)` (pypdf) and `upload_from_text(text, source)` — a regex over `Label: value` lines (`LABELS`). Unfound fields stay `None`; the Intake agent flags them. No LLM. |
| `inbox_service.py` | `InboxService.sync()` — one pass: new messages → parse → create → process; every message gets an `inbox_messages` row (`processed` / `skipped` / `failed`) so nothing is ingested twice; one bad email never stops the batch. `recent_messages()` feeds the dashboard card. |
| `poller.py` | `start_poller()` — asyncio loop started from the app lifespan when `INBOX_ENABLED`; runs `sync()` in a worker thread every `INBOX_POLL_SECONDS` and keeps the last result on `app.state.inbox`. |

## Setup (one time)

1. Google Cloud → create a project → **APIs & Services → Library** → enable **Gmail API**.
2. **APIs & Services → OAuth consent screen** → External, add yourself as a test user.
3. **Credentials → Create credentials → OAuth client ID → Desktop app** → download JSON → save as `secrets/credentials.json` (gitignored).
4. `python -m backend.inbox.authorize` → browser consent → `secrets/token.json`.
5. `.env`: `INBOX_ENABLED=true` → restart the backend. `GET /inbox/status` → `"authorized": true`.

## Demo

`python scripts/make_invoice_pdfs.py` writes `data/invoices/pdf/*.pdf` from the fixtures.
Email one to the watched account **as `invoice.pdf`**, then click **Check inbox now** on the
dashboard (or wait ≤ 60 s). `POST /demo/reset` also clears `inbox_messages`, so the same email
can be re-ingested for a repeat run.

## Privacy

PDF bytes exist only in memory during one sync. The parsed upload (including the PDF text) goes
through `GovernanceEngine.ingest()` — bank/routing/tax values are masked — before anything is
stored. Nothing is written back to Gmail.
