# backend/services/

Business-logic layer. API routes call services; services call the database and governance.
Keeps route handlers thin and logic unit-testable without HTTP.

| File | What it does |
|------|--------------|
| `invoice_service.py` | Create/list/get invoices, kick off `orchestration/invoice_workflow`, build the timeline view (decisions + tool calls + governance events in order). |
| `approval_service.py` | Create approval requests, record human approve/reject with reviewer + timestamp, transition invoice state, emit audit events. Enforces that a high-risk invoice can never be completed without a recorded human decision. |
| `audit_service.py` | Append-only writer/reader for `AuditEvent`. Assigns event IDs, computes `previous_event_hash`, rejects duplicate event IDs, flags out-of-order events instead of corrupting the chain. |
| `errors.py` | `ServiceError` hierarchy with HTTP status + code: `NotFoundError` 404, `InvalidStateError` 409, `ForbiddenError` 403, `UpstreamUnavailableError` 503. |
| `masking_service.py` | Applies display/log masking rules: bank accounts and tax IDs → last 4 digits, names/addresses redacted in logs. Called before any response or log line leaves the backend. |
| `source_pdf.py` | `redact_pdf(bytes)`: the emailed PDF with every sensitive value removed under black boxes (PyMuPDF), refusing scans and verifying the result, stored at ingestion; `render_masked_pdf(invoice)`: the fallback PDF rebuilt from masked `source_text` (fpdf2). Served by `GET /invoices/{id}/document.pdf`. |
