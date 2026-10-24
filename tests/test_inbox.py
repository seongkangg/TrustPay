"""Gmail intake: client parsing with a fake service, sync with a fake client, and the API."""

import base64

import pytest
from fastapi.testclient import TestClient

from backend.api.deps import get_payment_service
from backend.api.inbox_routes import get_gmail_client
from backend.database.database import get_session
from backend.database.tables import InboxMessageRow
from backend.governance import GovernanceEngine
from backend.inbox import InboxError, InboxMessage
from backend.inbox.gmail_client import GmailClient
from backend.inbox.inbox_service import InboxService
from backend.main import app
from backend.mock_systems.payment_service import PaymentService
from backend.services.invoice_service import InvoiceService
from scripts.make_invoice_pdfs import render_invoice_pdf


def b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


# --- a fake Gmail *service* (googleapiclient shape) ------------------------------------


class _Call:
    def __init__(self, result):
        self._result = result

    def execute(self):
        if isinstance(self._result, Exception):
            raise self._result
        return self._result


class FakeService:
    def __init__(self, pages, messages, attachments):
        self.pages, self.messages_, self.attachments_ = pages, messages, attachments
        self.listed = []

    def users(self):
        return self

    def messages(self):
        return self

    def attachments(self):
        return self

    def list(self, userId, q, maxResults, pageToken=None):  # noqa: N803 — googleapiclient names
        self.listed.append(q)
        return _Call(self.pages[pageToken or 0])

    def get(self, userId, id=None, messageId=None, format=None):  # noqa: A002, N803
        if messageId is not None:
            return _Call(self.attachments_[id])
        return _Call(self.messages_[id])


def message(mid, filename, data=None, attachment_id=None, nested=False):
    part = {"filename": filename, "mimeType": "application/pdf", "body": {}}
    if data is not None:
        part["body"]["data"] = b64(data)
    if attachment_id:
        part["body"]["attachmentId"] = attachment_id
    parts = [{"filename": "", "mimeType": "text/plain", "body": {"data": b64(b"hi")}}, part]
    if nested:
        parts = [{"mimeType": "multipart/mixed", "parts": parts}]
    return {
        "id": mid,
        "threadId": f"t-{mid}",
        "internalDate": "1761000000000",
        "payload": {
            "headers": [
                {"name": "From", "value": "ap@vendor.example"},
                {"name": "Subject", "value": f"Invoice {mid}"},
            ],
            "parts": parts,
        },
    }


def test_gmail_client_lists_pages_and_fetches_nested_invoice_pdf():
    pdf = b"%PDF-fake"
    svc = FakeService(
        pages={
            0: {"messages": [{"id": "m1"}], "nextPageToken": "p2"},
            "p2": {"messages": [{"id": "m2"}]},
        },
        messages={
            "m1": message("m1", "Invoice.PDF", attachment_id="att-1", nested=True),
            "m2": message("m2", "invoice_1001.pdf", data=pdf),
        },
        attachments={"att-1": {"data": b64(pdf)}},
    )
    client = GmailClient(svc)
    assert client.list_candidates(30) == ["m1", "m2"]
    assert "newer_than:30d" in svc.listed[0] and "filename:pdf" in svc.listed[0]

    msg = client.fetch("m1")
    assert msg.pdf_bytes == pdf and msg.attachment_name == "Invoice.PDF"
    assert msg.sender == "ap@vendor.example" and msg.subject == "Invoice m1"
    assert msg.received_at is not None and msg.thread_id == "t-m1"
    assert client.fetch("m2") is None  # name contains 'invoice' but is not invoice.pdf


def test_gmail_client_wraps_provider_errors():
    svc = FakeService(pages={0: RuntimeError("quota")}, messages={}, attachments={})
    with pytest.raises(InboxError):
        GmailClient(svc).list_candidates(7)


# --- sync with a fake *client* -----------------------------------------------------------


class FakeGmailClient:
    def __init__(self, items: dict[str, InboxMessage | None | Exception]):
        self.items = items

    def list_candidates(self, lookback_days):
        return list(self.items)

    def fetch(self, message_id):
        item = self.items[message_id]
        if isinstance(item, Exception):
            raise item
        return item


def inbox_msg(mid, pdf_bytes, name="invoice.pdf"):
    return InboxMessage(
        mid, f"t-{mid}", "ap@vendor.example", f"Invoice {mid}", None, name, pdf_bytes
    )


@pytest.fixture
def gov(session, ref):
    return GovernanceEngine(session, ref)


def test_sync_creates_processes_and_dedupes(session, gov, fixture_by_id):
    client = FakeGmailClient(
        {
            "m-low": inbox_msg("m-low", render_invoice_pdf(fixture_by_id("INV-1001")["upload"])),
            "m-high": inbox_msg(
                "m-high", render_invoice_pdf(fixture_by_id("INV-1002")["upload"]), "INVOICE.PDF"
            ),
            "m-other": None,  # no invoice.pdf on it
        }
    )
    svc = InboxService(session, gov, client)
    first = svc.sync()
    assert first.checked == 3 and first.created == ["INV-1001", "INV-1002"] and first.skipped == 1
    assert first.failed == []

    invoices = InvoiceService(session, gov)
    assert invoices.get("INV-1001").status.value == "COMPLETED"
    assert invoices.get("INV-1002").status.value == "PENDING_APPROVAL"
    assert "email from ap@vendor.example" in invoices.get("INV-1001").source_document

    rows = {r.message_id: r for r in session.query(InboxMessageRow)}
    assert rows["m-low"].status == "processed" and rows["m-low"].invoice_id == "INV-1001"
    assert rows["m-other"].status == "skipped" and rows["m-other"].invoice_id is None

    second = svc.sync()
    assert second.checked == 0 and second.created == [] and second.skipped == 3


def test_bad_messages_do_not_stop_the_batch(session, gov, fixture_by_id):
    client = FakeGmailClient(
        {
            "m-corrupt": inbox_msg("m-corrupt", b"not a pdf"),
            "m-down": InboxError("attachment fetch failed"),
            "m-ok": inbox_msg("m-ok", render_invoice_pdf(fixture_by_id("INV-1001")["upload"])),
        }
    )
    result = InboxService(session, gov, client).sync()
    assert result.created == ["INV-1001"]
    assert {m for m, _ in result.failed} == {"m-corrupt", "m-down"}
    rows = {r.message_id: r for r in session.query(InboxMessageRow)}
    assert rows["m-corrupt"].status == "failed" and "PDF" in rows["m-corrupt"].error
    assert rows["m-down"].status == "failed" and rows["m-down"].invoice_id is None
    assert rows["m-down"].error == "Couldn't download this email."


def test_processing_crash_shows_clean_message_and_logs_detail(
    session, gov, fixture_by_id, monkeypatch, caplog
):
    """The raw exception (e.g. a SQLAlchemy rollback error) goes to the dev log, not the UI."""

    def boom(self, invoice_id, **_kwargs):
        raise RuntimeError("This Session's transaction has been rolled back")

    monkeypatch.setattr(InvoiceService, "process", boom)
    pdf = render_invoice_pdf(fixture_by_id("INV-1001")["upload"])
    result = InboxService(session, gov, FakeGmailClient({"m-x": inbox_msg("m-x", pdf)})).sync()
    error = session.get(InboxMessageRow, "m-x").error
    assert error.startswith("Couldn't process this invoice (ERR-")
    assert "rolled back" not in error and "RuntimeError" not in error
    assert result.failed == [("m-x", error)]
    ref = error[error.index("ERR-") : -2]
    assert any(
        ref in r.getMessage() and "rolled back" in str(r.exc_info[1]) for r in caplog.records
    )


def test_emailed_suspicious_invoice_is_blocked_and_masked(session, gov, fixture_by_id):
    pdf = render_invoice_pdf(fixture_by_id("INV-1003")["upload"])
    result = InboxService(session, gov, FakeGmailClient({"m-sus": inbox_msg("m-sus", pdf)})).sync()
    inv = InvoiceService(session, gov).get(result.created[0])
    assert inv.status.value == "BLOCKED" and inv.bank_account == "****6789"
    events = [e.event_type.value for e in gov.audit.list_for_invoice(inv.invoice_id)]
    assert events[:2] == ["invoice_received", "sensitive_data_masked"]


def test_unreadable_pdf_text_still_creates_an_escalated_invoice(session, gov):
    """A PDF with no recognizable labels → invoice with missing fields, escalated, never paid."""
    from fpdf import FPDF

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=12)
    pdf.cell(0, 8, "Thanks for your business! Pay 500 dollars sometime.")
    result = InboxService(
        session, gov, FakeGmailClient({"m-blank": inbox_msg("m-blank", bytes(pdf.output()))})
    ).sync()
    inv = InvoiceService(session, gov).get(result.created[0])
    assert inv.vendor_invoice_number.startswith("EMAIL-")
    assert inv.status.value in ("PENDING_APPROVAL", "BLOCKED", "FAILED")
    assert gov.payments.get_payment(inv.invoice_id) is None


def test_gmail_down_raises_out_of_sync(session, gov):
    class Down(FakeGmailClient):
        def list_candidates(self, lookback_days):
            raise InboxError("offline")

    with pytest.raises(InboxError):
        InboxService(session, gov, Down({})).sync()


# --- API ------------------------------------------------------------------------------------


@pytest.fixture
def client(session):
    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[get_payment_service] = lambda: PaymentService()
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def test_status_and_sync_without_authorization(client):
    status = client.get("/inbox/status").json()
    assert status["authorized"] is False and status["enabled"] is False and status["recent"] == []
    r = client.post("/inbox/sync")
    assert r.status_code == 503 and r.json()["error"] == "INBOX_NOT_AUTHORIZED"
    assert "authorize" in r.json()["message"]


def test_sync_over_http_with_fake_client(client, fixture_by_id):
    fake = FakeGmailClient(
        {"m-low": inbox_msg("m-low", render_invoice_pdf(fixture_by_id("INV-1001")["upload"]))}
    )
    app.dependency_overrides[get_gmail_client] = lambda: fake
    r = client.post("/inbox/sync")
    assert r.status_code == 200 and r.json()["created"] == ["INV-1001"]
    status = client.get("/inbox/status").json()
    assert status["last_result"]["created"] == ["INV-1001"]
    assert (
        status["recent"][0]["invoice_id"] == "INV-1001"
        and status["recent"][0]["status"] == "processed"
    )
    assert client.get("/invoices/INV-1001").json()["status"] == "COMPLETED"
    # reset clears inbox rows too, so the same email can be re-ingested for a repeat demo
    assert client.post("/demo/reset").json()["removed"]["inbox_messages"] == 1
    assert client.post("/inbox/sync").json()["created"] == ["INV-1001"]


def test_concurrent_syncs_ingest_an_email_once(tmp_path, ref, fixture_by_id):
    """The background poll and a 'Check inbox now' click overlapping must not both ingest the
    same email (it duplicated the invoice and collided on IDs on Supabase)."""
    import threading
    import time

    from sqlalchemy import create_engine, func, select
    from sqlalchemy.orm import sessionmaker

    from backend.database.database import Base
    from backend.database.tables import InvoiceRow

    engine = create_engine(
        f"sqlite:///{tmp_path / 'race.db'}", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    pdf = render_invoice_pdf(fixture_by_id("INV-1001")["upload"])

    class SlowClient(FakeGmailClient):
        def fetch(self, message_id):
            time.sleep(0.3)  # long enough for the second sync to start mid-way
            return super().fetch(message_id)

    client = SlowClient({"m-once": inbox_msg("m-once", pdf)})
    payments = PaymentService()
    results, errors = [], []

    def run():
        session = Session()
        try:
            gov = GovernanceEngine(session, ref, payment_service=payments)
            results.append(InboxService(session, gov, client).sync())
        except Exception as exc:  # noqa: BLE001
            errors.append(exc)
        finally:
            session.close()

    threads = [threading.Thread(target=run) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert errors == []
    assert sorted(len(r.created) for r in results) == [0, 1]
    with Session() as s:
        assert s.scalar(select(func.count()).select_from(InvoiceRow)) == 1
        assert s.get(InboxMessageRow, "m-once").status == "processed"


def test_unexpected_error_returns_generic_500(client, monkeypatch):
    def boom(*_a, **_k):
        raise RuntimeError("secret internals")

    monkeypatch.setattr("backend.api.inbox_routes.recent_messages", boom)
    r = TestClient(app, raise_server_exceptions=False).get("/inbox/status")
    body = r.json()
    assert r.status_code == 500 and body["error"] == "INTERNAL_ERROR"
    assert "ERR-" in body["message"] and "secret" not in body["message"]
