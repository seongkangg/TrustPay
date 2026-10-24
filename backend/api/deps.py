"""FastAPI dependencies. One GovernanceEngine per request over the request's session;
the simulated payment ledger is process-wide so the double-payment guard survives requests."""

from fastapi import Depends
from sqlalchemy.orm import Session

from backend.database.database import get_session
from backend.governance import GovernanceEngine
from backend.llm.granite_client import LLMClient, get_llm_client
from backend.mock_systems.payment_service import PaymentService
from backend.services.approval_service import ApprovalService
from backend.services.invoice_service import InvoiceService

_payment_service = PaymentService()


def get_payment_service() -> PaymentService:
    return _payment_service


def get_llm() -> LLMClient:
    return get_llm_client()


def get_engine(
    session: Session = Depends(get_session),
    payments: PaymentService = Depends(get_payment_service),
) -> GovernanceEngine:
    return GovernanceEngine(session, payment_service=payments)


def get_invoice_service(
    session: Session = Depends(get_session),
    gov: GovernanceEngine = Depends(get_engine),
    llm: LLMClient = Depends(get_llm),
) -> InvoiceService:
    return InvoiceService(session, gov, llm)


def get_approval_service(
    session: Session = Depends(get_session),
    gov: GovernanceEngine = Depends(get_engine),
    invoices: InvoiceService = Depends(get_invoice_service),
) -> ApprovalService:
    return ApprovalService(session, gov, invoices)
