"""Test package. Imported before conftest, so this is the earliest point to pin settings.

Tests must never depend on the developer's local .env (e.g. LLM_MODE=ollama would make the
HTTP scenario tests call a real model, and a real secrets/token.json would let them read the
developer's actual Gmail). Environment variables take precedence over .env in
pydantic-settings, so forcing the mock here keeps every test deterministic.
"""

import os

os.environ["LLM_MODE"] = "mock"
# Never touch the shared Supabase database: the app's module-level engine uses this URL.
os.environ["DATABASE_URL"] = "sqlite://"
# Never touch the developer's real Gmail: no poller, and no token to authorize with.
os.environ["INBOX_ENABLED"] = "false"
os.environ["GMAIL_TOKEN_FILE"] = os.path.join(os.path.dirname(__file__), "__no_such_token__.json")
