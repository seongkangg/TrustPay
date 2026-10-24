# backend/database/

SQLite persistence for the prototype (swap for PostgreSQL later via the same engine config).

| File | What it does |
|------|--------------|
| `database.py` | Creates the SQLAlchemy engine/session from `DATABASE_URL`, provides the FastAPI dependency for sessions, `init_db()` helper. |
| `tables.py` | ORM table definitions mirroring `models/`: `invoices`, `agent_decisions`, `tool_calls`, `audit_events`, `approvals`. `audit_events` is insert-only (no update/delete paths). |
| `seed_data.py` | Loads `data/vendors.json`, `data/purchase_orders.json`, `data/approval_limits.json` into an in-memory `ReferenceData` store that the mock systems read. Demo invoices are **not** pre-inserted — they enter via `POST /invoices` so the workflow (including duplicate ordering) runs for real; `load_demo_invoices()` returns the fixtures for tests and the demo script. |
