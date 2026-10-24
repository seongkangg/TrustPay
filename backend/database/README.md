# backend/database/

SQLite persistence for the prototype (swap for PostgreSQL later via the same engine config).

| File | What it does |
|------|--------------|
| `database.py` | Creates the SQLAlchemy engine/session from `DATABASE_URL`, provides the FastAPI dependency for sessions, `init_db()` helper. |
| `tables.py` | ORM table definitions mirroring `models/`: `invoices`, `agent_decisions`, `tool_calls`, `audit_events`, `approvals`. `audit_events` is insert-only (no update/delete paths). |
| `seed_data.py` | Loads `data/vendors.json`, `data/purchase_orders.json`, `data/approval_limits.json`, and the three demo invoices into the DB on startup so the demo is ready immediately. |
