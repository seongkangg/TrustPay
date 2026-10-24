"""Background poll: every INBOX_POLL_SECONDS run one sync in a worker thread.

Started from the app lifespan only when INBOX_ENABLED. Keeps its last result on
`app.state.inbox` for GET /inbox/status. Never lets an exception escape the loop.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from backend.config import get_settings
from backend.database.database import SessionLocal
from backend.governance import GovernanceEngine
from backend.inbox import InboxError
from backend.inbox.gmail_client import GmailClient
from backend.inbox.inbox_service import InboxService
from backend.llm.granite_client import get_llm_client
from backend.utils.logging_config import log_dev_error
from backend.utils.timestamps import now_utc

log = logging.getLogger(__name__)


@dataclass
class InboxState:
    last_sync_at: datetime | None = None
    last_result: dict[str, Any] | None = None
    last_error: str | None = None
    runs: int = 0
    tasks: list[asyncio.Task] = field(default_factory=list)

    def record(self, result: dict[str, Any] | None, error: str | None) -> None:
        self.last_sync_at = now_utc()
        self.last_result = result
        self.last_error = error
        self.runs += 1


def run_sync_once(payment_service) -> dict[str, Any]:
    """Blocking: one sync with its own session. Raises InboxError when Gmail is unreachable."""
    settings = get_settings()
    client = GmailClient.from_files(settings.gmail_credentials_file, settings.gmail_token_file)
    session = SessionLocal()
    try:
        gov = GovernanceEngine(session, payment_service=payment_service)
        service = InboxService(
            session, gov, client, get_llm_client(settings), settings.inbox_lookback_days
        )
        return service.sync().as_dict()
    finally:
        session.close()


async def _loop(state: InboxState, payment_service, poll_seconds: int) -> None:
    while True:
        try:
            result = await asyncio.to_thread(run_sync_once, payment_service)
            state.record(result, None)
            if result["created"] or result["failed"]:
                log.info("inbox poll: %s", result)
        except InboxError:
            log_dev_error(log, "inbox poll: Gmail unreachable")
            state.record(None, "Couldn't reach the inbox. Check Gmail authorization.")
        except Exception:  # noqa: BLE001 — the poller must survive anything
            ref = log_dev_error(log, "inbox poll crashed")
            state.record(None, f"Inbox check failed ({ref}).")
        await asyncio.sleep(poll_seconds)


def start_poller(state: InboxState, payment_service, poll_seconds: int) -> asyncio.Task:
    task = asyncio.create_task(_loop(state, payment_service, poll_seconds))
    state.tasks.append(task)
    return task
