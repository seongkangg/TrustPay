"""Simulated enterprise systems backed by data/*.json.

Agents never import this package. Access is only through
backend/governance/tool_call_interceptor.py.

Each service accepts `available=False` (or reads MOCK_FAILURES from settings) to simulate
an outage for reliability tests; an unavailable service raises MockSystemUnavailable.
"""

from backend.config import get_settings


class MockSystemError(Exception):
    """Base for all mock-system errors."""


class MockSystemUnavailable(MockSystemError):
    """The simulated enterprise system is down (maps to MOCK_SYSTEM_UNAVAILABLE)."""


class NotFound(MockSystemError):
    """Record does not exist (maps to UNKNOWN_VENDOR / INVALID_PURCHASE_ORDER)."""


class UnauthorizedActor(MockSystemError):
    """A mutating call came from an actor that may never perform it."""


def is_available(name: str, override: bool | None = None) -> bool:
    if override is not None:
        return override
    return name not in get_settings().failing_mocks
