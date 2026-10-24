# backend/database/

One set of SQLAlchemy tables, two places it can live (chosen by `DATABASE_URL`):

- **Supabase Postgres** — the shared team database. Every invoice received from Gmail, its
  status (`PENDING_APPROVAL`, `BLOCKED`, `APPROVED` → `COMPLETED`, `REJECTED`, `FAILED`), the
  human decision, the agent decisions, tool calls and the hash-chained audit trail.
- **SQLite** (`sqlite:///./trustpay.db`) — local solo dev; the test suite always uses in-memory SQLite.

| File | What it does |
|------|--------------|
| `database.py` | Builds the engine from `DATABASE_URL`. Supabase URLs are accepted as pasted (`postgres://…` / `postgresql://…` → psycopg 3), with reconnect-on-stale (`pool_pre_ping`) and prepared statements off so the transaction pooler works too. `init_db()` creates the tables and, on Postgres, enables row-level security on each (see below). FastAPI session dependency. |
| `tables.py` | ORM tables mirroring `models/`: `invoices`, `agent_decisions`, `tool_calls`, `audit_events`, `approvals`, `inbox_messages`. `audit_events` is insert-only (no update/delete paths). |
| `seed_data.py` | Loads `data/vendors.json`, `data/purchase_orders.json`, `data/approval_limits.json` into an in-memory `ReferenceData` store that the mock systems read. Invoices are never pre-inserted — they arrive from Gmail (or `POST /invoices`). `load_demo_invoices()` returns the fixtures for tests. |

## Supabase setup

1. supabase.com → New project (note the database password).
2. Project → **Connect** → **Session pooler** → copy the URI, put your password in it.
3. `.env`: `DATABASE_URL=<that URI>` (`.env` is gitignored — never commit it).
4. Start the backend. Tables are created on first start; the poller then pulls your Gmail invoices in.

**Row-level security.** Supabase exposes every `public` table through its REST API to anyone
holding the project's anon key, which is meant to be public. `init_db()` turns RLS on for every
table with no policies, so that route returns nothing; the backend connects directly as the
table owner and is unaffected. Read the data in the Supabase **Table Editor** or SQL editor.

**Run one backend against it.** IDs (`INV-1001`, `EVT-001`, …) are assigned as "count + 1",
which is fine for one writer. Two backends writing to the same database at once can collide;
teammates should point the web or mobile app at the one running backend instead.
