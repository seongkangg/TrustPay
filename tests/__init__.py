"""Test package. Imported before conftest, so this is the earliest point to pin settings.

Tests must never depend on the developer's local .env (e.g. LLM_MODE=ollama would make the
HTTP scenario tests call a real model). Environment variables take precedence over .env in
pydantic-settings, so forcing the mock here keeps every test deterministic.
"""

import os

os.environ["LLM_MODE"] = "mock"
