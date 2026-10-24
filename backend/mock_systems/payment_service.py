"""Mock payment service — POST /payments/authorize. MUTATING. Nothing real moves.

Defense in depth: even if the governance allowlist were bypassed, this service refuses
any actor other than the governance layer or a human reviewer, and refuses to authorize
the same invoice twice.
"""

from typing import Any

from backend.mock_systems import MockSystemUnavailable, UnauthorizedActor, is_available
from backend.models.enums import AgentName
from backend.utils.timestamps import now_utc, to_iso

NAME = "payment"
PERMITTED_ACTORS = {AgentName.GOVERNANCE.value, AgentName.HUMAN_REVIEWER.value}


class PaymentService:
    def __init__(self, available: bool | None = None):
        self._available = available
        self._payments: dict[str, dict[str, Any]] = {}  # invoice_id -> payment

    def authorize(
        self, invoice_id: str, amount: float, currency: str, actor: str
    ) -> dict[str, Any]:
        if not is_available(NAME, self._available):
            raise MockSystemUnavailable("payment service unavailable")
        actor_value = AgentName(actor).value
        if actor_value not in PERMITTED_ACTORS:
            raise UnauthorizedActor(f"{actor_value} may not authorize payments")
        if invoice_id in self._payments:
            raise UnauthorizedActor(f"invoice {invoice_id} already authorized")
        payment = {
            "payment_id": f"PAY-{len(self._payments) + 1:04d}",
            "invoice_id": invoice_id,
            "amount": amount,
            "currency": currency,
            "actor": actor_value,
            "status": "authorized",
            "simulated": True,
            "authorized_at": to_iso(now_utc()),
        }
        self._payments[invoice_id] = payment
        return dict(payment)

    def get_payment(self, invoice_id: str) -> dict[str, Any] | None:
        payment = self._payments.get(invoice_id)
        return dict(payment) if payment else None
