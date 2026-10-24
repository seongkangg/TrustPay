"""Insert fake past invoices so the dashboard's "Last 14 days" chart shows history.

    python scripts/seed_history.py          # writes into DATABASE_URL (default trustpay.db)

Demo data only: every row is dated before today, uses the INV-0xxx id range (the app
numbers from INV-1001) and HIST- vendor invoice numbers so it never trips duplicate
detection for the live fixtures. Rows carry no agent decisions or audit events.
Re-running replaces the previous history; POST /demo/reset removes it.
"""

import random
import sys
import uuid
from datetime import timedelta
from pathlib import Path

from sqlalchemy import delete

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from backend.database.database import SessionLocal, init_db  # noqa: E402
from backend.database.tables import InvoiceRow  # noqa: E402
from backend.models.enums import InvoiceStatus, Recommendation, RiskLevel  # noqa: E402
from backend.utils.timestamps import now_utc  # noqa: E402

DAYS = 13  # the 13 days before today; today stays for the live demo
VENDORS = [
    ("V-101", "Acme Office Supplies"),
    ("V-102", "Northwind Logistics"),
    ("V-103", "Contoso IT Services"),
]
# (status, risk, recommendation, weight). Past invoices are already resolved — no BLOCKED or
# PENDING_APPROVAL: those would sit in the reviewer's approval queue with no approval request
# behind them, and approving one would fail.
OUTCOMES = [
    (InvoiceStatus.COMPLETED, RiskLevel.LOW, Recommendation.APPROVE, 6),
    (InvoiceStatus.COMPLETED, RiskLevel.MEDIUM, Recommendation.ESCALATE, 2),
    (InvoiceStatus.REJECTED, RiskLevel.HIGH, Recommendation.REJECT, 2),
    (InvoiceStatus.REJECTED, RiskLevel.MEDIUM, Recommendation.ESCALATE, 1),
]


def build_rows(rng: random.Random) -> list[InvoiceRow]:
    today = now_utc().replace(hour=0, minute=0, second=0, microsecond=0)
    rows, n = [], 0
    for back in range(DAYS, 0, -1):
        for _ in range(rng.randint(1, 5)):
            n += 1
            status, risk, rec, _w = rng.choices(OUTCOMES, weights=[o[3] for o in OUTCOMES])[0]
            vendor_id, vendor_name = rng.choice(VENDORS)
            created = today - timedelta(
                days=back, hours=-rng.randint(8, 17), minutes=-rng.randint(0, 59)
            )
            rows.append(
                InvoiceRow(
                    invoice_id=f"INV-{n:04d}",
                    correlation_id=str(uuid.uuid4()),
                    vendor_invoice_number=f"HIST-{n:04d}",
                    vendor_id=vendor_id,
                    vendor_name=vendor_name,
                    # cents keep amounts from matching a fixture amount exactly
                    amount=round(rng.uniform(300, 18000)) + 0.37,
                    currency="USD",
                    due_date=(created + timedelta(days=30)).date(),
                    status=status.value,
                    risk_level=risk.value,
                    recommendation=rec.value,
                    recommendation_confidence=round(rng.uniform(0.7, 0.98), 2),
                    sensitive_data_detected=False,
                    extraction=[],
                    created_at=created,
                    updated_at=created + timedelta(minutes=rng.randint(1, 90)),
                )
            )
    return rows


def main() -> None:
    init_db()
    rows = build_rows(random.Random(42))
    assert all(r.created_at.date() < now_utc().date() for r in rows)
    with SessionLocal() as session:
        session.execute(delete(InvoiceRow).where(InvoiceRow.invoice_id.like("INV-0%")))
        session.add_all(rows)
        session.commit()
    print(f"inserted {len(rows)} historical invoices over the last {DAYS} days")


if __name__ == "__main__":
    main()
