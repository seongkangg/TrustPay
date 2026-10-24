"""GET /inbox/status · POST /inbox/sync — Gmail intake."""

import logging
from typing import Any

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from backend.api.deps import get_engine, get_llm
from backend.config import Settings, get_settings
from backend.database.database import get_session
from backend.governance import GovernanceEngine
from backend.inbox import InboxError
from backend.inbox.gmail_client import GmailClient
from backend.inbox.inbox_service import InboxService, recent_messages
from backend.inbox.poller import InboxState
from backend.llm.granite_client import LLMClient
from backend.services.errors import InboxNotAuthorizedError, UpstreamUnavailableError
from backend.utils.logging_config import log_dev_error

log = logging.getLogger(__name__)

router = APIRouter(prefix="/inbox", tags=["inbox"])


def get_gmail_client(settings: Settings = Depends(get_settings)) -> GmailClient:
    try:
        return GmailClient.from_files(settings.gmail_credentials_file, settings.gmail_token_file)
    except InboxError as exc:
        log_dev_error(log, "inbox: Gmail client could not load")
        raise InboxNotAuthorizedError("Gmail is not authorized for this inbox.") from exc


def _state(request: Request) -> InboxState:
    state = getattr(request.app.state, "inbox", None)
    if state is None:
        state = request.app.state.inbox = InboxState()
    return state


@router.get("/status")
def inbox_status(
    request: Request,
    settings: Settings = Depends(get_settings),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    state = _state(request)
    return {
        "enabled": settings.inbox_enabled,
        "authorized": GmailClient.token_exists(settings.gmail_token_file),
        "poll_seconds": settings.inbox_poll_seconds,
        "last_sync_at": state.last_sync_at,
        "last_result": state.last_result,
        "last_error": state.last_error,
        "recent": recent_messages(session),
    }


@router.post("/sync")
def inbox_sync(
    request: Request,
    settings: Settings = Depends(get_settings),
    session: Session = Depends(get_session),
    gov: GovernanceEngine = Depends(get_engine),
    llm: LLMClient = Depends(get_llm),
    client: GmailClient = Depends(get_gmail_client),
) -> dict[str, Any]:
    state = _state(request)
    try:
        result = (
            InboxService(session, gov, client, llm, settings.inbox_lookback_days).sync().as_dict()
        )
    except InboxError as exc:
        log_dev_error(log, "inbox sync: Gmail unreachable")
        message = "Couldn't reach the inbox. Please try again later."
        state.record(None, message)
        raise UpstreamUnavailableError(message) from exc
    state.record(result, None)
    return result
