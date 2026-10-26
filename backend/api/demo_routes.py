"""POST /demo/reset — wipe all invoice state so the demo can be rerun without a restart.

Disabled when APP_ENV=production. Reference data (vendors, POs, limits) is untouched
because it is read-only fixture data, not state.
"""

from fastapi import APIRouter, Depends
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from backend.api.deps import get_payment_service
from backend.config import get_settings
from backend.database.database import get_session
from backend.database.tables import (
    AgentDecisionRow,
    ApprovalRow,
    AuditEventRow,
    InboxMessageRow,
    InvoiceRow,
    SourceDocumentRow,
    ToolCallRow,
)
from backend.mock_systems.payment_service import PaymentService
from backend.services.errors import ForbiddenError

router = APIRouter(prefix="/demo", tags=["demo"])

STATE_TABLES = (
    AuditEventRow,
    ToolCallRow,
    AgentDecisionRow,
    ApprovalRow,
    InboxMessageRow,
    SourceDocumentRow,
    InvoiceRow,
)


@router.post("/reset")
def reset_demo(
    session: Session = Depends(get_session),
    payments: PaymentService = Depends(get_payment_service),
) -> dict:
    if get_settings().app_env == "production":
        raise ForbiddenError("demo reset is disabled in production")
    removed = {}
    for table in STATE_TABLES:
        count = session.scalar(select(func.count()).select_from(table)) or 0
        session.execute(delete(table))
        removed[table.__tablename__] = count
    session.commit()
    payments.clear()
    return {"status": "reset", "removed": removed}
