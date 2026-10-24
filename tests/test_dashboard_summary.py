"""dashboard_summary: per-day history (`by_day`) and money tiles (`amounts`) added for the
read-only overview. The pre-existing keys are covered by tests/test_scenarios.py."""

from datetime import timedelta

import pytest

from backend.governance import GovernanceEngine
from backend.models import InvoiceStatus, InvoiceUpload
from backend.services.invoice_service import DASHBOARD_DAYS, InvoiceService
from backend.utils.timestamps import now_utc

WITHHELD = {InvoiceStatus.PENDING_APPROVAL.value, InvoiceStatus.BLOCKED.value}


@pytest.fixture
def invoices(session, ref):
    return InvoiceService(session, GovernanceEngine(session, ref))


def _process_all(invoices, demo_invoices):
    """Create and process the four fixtures in order; returns the fixtures."""
    for fx in demo_invoices:
        created = invoices.create(InvoiceUpload(**fx["upload"]))
        invoices.process(created.invoice_id)
    return demo_invoices


def test_empty_summary_has_full_window_and_zero_amounts(invoices):
    summary = invoices.dashboard_summary()
    assert summary["amounts"] == {"total": 0, "paid": 0, "withheld": 0}
    assert len(summary["by_day"]) == DASHBOARD_DAYS == 14
    assert all(d["received"] == d["completed"] == d["blocked"] == 0 for d in summary["by_day"])


def test_by_day_window_is_contiguous_and_ends_today(invoices):
    dates = [d["date"] for d in invoices.dashboard_summary()["by_day"]]
    today = now_utc().date()
    assert dates[-1] == today.isoformat()
    assert dates == [(today - timedelta(days=13 - i)).isoformat() for i in range(14)]


def test_amounts_follow_final_status(invoices, demo_invoices):
    fixtures = _process_all(invoices, demo_invoices)
    summary = invoices.dashboard_summary()

    by_status = {fx["expected"]["final_status"]: 0.0 for fx in fixtures}
    for fx in fixtures:
        by_status[fx["expected"]["final_status"]] += fx["upload"]["amount"]

    total = sum(fx["upload"]["amount"] for fx in fixtures)
    paid = by_status.get(InvoiceStatus.COMPLETED.value, 0.0)
    withheld = sum(v for k, v in by_status.items() if k in WITHHELD)
    assert summary["amounts"] == {
        "total": round(total, 2),
        "paid": round(paid, 2),
        "withheld": round(withheld, 2),
    }
    # the three money tiles are consistent with each other
    assert (
        summary["amounts"]["paid"] + summary["amounts"]["withheld"] <= summary["amounts"]["total"]
    )


def test_by_day_counts_todays_invoices_by_outcome(invoices, demo_invoices):
    fixtures = _process_all(invoices, demo_invoices)
    summary = invoices.dashboard_summary()
    today = summary["by_day"][-1]
    finals = [fx["expected"]["final_status"] for fx in fixtures]

    assert today["date"] == now_utc().date().isoformat()
    assert today["received"] == len(fixtures) == summary["total_invoices"]
    assert today["completed"] == finals.count(InvoiceStatus.COMPLETED.value)
    assert today["blocked"] == finals.count(InvoiceStatus.BLOCKED.value)
    assert all(d["received"] == 0 for d in summary["by_day"][:-1])


def test_by_day_amounts_match_the_money_tiles(invoices, demo_invoices):
    # Each day carries the same money split as the `amounts` tiles, so a client can show any one
    # day's volume / paid / withheld; with every invoice created today, today equals the totals.
    _process_all(invoices, demo_invoices)
    summary = invoices.dashboard_summary()
    today = summary["by_day"][-1]

    assert {k: today[k] for k in ("amount", "paid", "withheld")} == {
        "amount": summary["amounts"]["total"],
        "paid": summary["amounts"]["paid"],
        "withheld": summary["amounts"]["withheld"],
    }
    assert all(d["amount"] == d["paid"] == d["withheld"] == 0 for d in summary["by_day"][:-1])
    assert today["paid"] + today["withheld"] <= today["amount"]


def test_older_invoices_leave_by_day_amounts_but_stay_in_the_tiles(
    invoices, demo_invoices, session
):
    _process_all(invoices, demo_invoices)
    row = invoices.get_row("INV-1001")
    row.created_at = now_utc() - timedelta(days=DASHBOARD_DAYS + 1)
    session.commit()

    summary = invoices.dashboard_summary()
    in_window = round(sum(d["amount"] for d in summary["by_day"]), 2)
    assert in_window == round(summary["amounts"]["total"] - (row.amount or 0), 2)


def test_invoices_older_than_the_window_are_excluded_from_by_day(invoices, demo_invoices, session):
    _process_all(invoices, demo_invoices)
    row = invoices.get_row("INV-1001")
    row.created_at = now_utc() - timedelta(days=DASHBOARD_DAYS + 1)
    session.commit()

    summary = invoices.dashboard_summary()
    assert sum(d["received"] for d in summary["by_day"]) == summary["total_invoices"] - 1
    # ...but it still counts toward the money tiles
    assert summary["amounts"]["total"] == round(
        sum(fx["upload"]["amount"] for fx in demo_invoices), 2
    )


def test_existing_keys_are_unchanged(invoices, demo_invoices):
    _process_all(invoices, demo_invoices)
    summary = invoices.dashboard_summary()
    assert set(summary) == {
        "total_invoices",
        "by_risk",
        "by_status",
        "blocked_actions",
        "pending_approvals",
        "sensitive_data_detections",
        "recent_violations",
        "by_day",
        "amounts",
    }
    assert summary["by_risk"] == {"low": 1, "medium": 0, "high": 3}
