import { useState } from "react";
import { Link } from "react-router-dom";

import { api, fmtTime } from "../api/client.js";

// Gmail inbox that feeds invoices in automatically. `status` is GET /inbox/status (or null while
// loading); `unavailable` means the backend answered 404 — the inbox feature is not deployed.
export default function InboxCard({ status, unavailable, onSynced }) {
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  if (unavailable) {
    return (
      <div className="card inbox">
        <p className="muted" style={{ margin: 0 }}>
          Inbox not available on this backend.
        </p>
      </div>
    );
  }
  if (!status) {
    return (
      <div className="card inbox">
        <p className="muted" style={{ margin: 0 }}>
          Loading…
        </p>
      </div>
    );
  }

  async function sync() {
    setBusy(true);
    setError(null);
    try {
      setResult(await api.inboxSync());
      onSynced?.();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  const last = result || status.last_result;
  const authorized = status.enabled && status.authorized;

  return (
    <div className="card inbox">
      <div className="head">
        <span className={`badge ${authorized ? "auth-allowed" : status.enabled ? "auth-blocked" : ""}`}>
          {!status.enabled ? "Disabled" : status.authorized ? "Authorized" : "Not authorized"}
        </span>
        <span className="small muted">
          Last sync: {fmtTime(status.last_sync_at)}
          {status.poll_seconds ? ` · polls every ${status.poll_seconds}s` : ""}
        </span>
        <span className="spacer" />
        <button className="primary" disabled={busy || !status.enabled} onClick={sync}>
          {busy ? "Checking…" : "Check inbox now"}
        </button>
      </div>

      {error && <div className="alert danger small">{error}</div>}
      {!error && status.last_error && <div className="alert warn small">{status.last_error}</div>}

      {last && (
        <p className="result small muted">
          {result ? "Just now: " : "Last result: "}
          {last.checked} message{last.checked === 1 ? "" : "s"} checked · {last.created?.length ?? 0} invoice
          {last.created?.length === 1 ? "" : "s"} created · {last.skipped} skipped · {last.failed?.length ?? 0} failed
        </p>
      )}

      {status.recent?.length > 0 && (
        <table>
          <thead>
            <tr>
              <th>Received</th>
              <th>From</th>
              <th>Subject</th>
              <th>Attachment</th>
              <th>Invoice</th>
            </tr>
          </thead>
          <tbody>
            {status.recent.map((m) => (
              <tr key={m.message_id} className={m.status === "failed" ? "blocked" : ""}>
                <td className="small muted">{fmtTime(m.received_at)}</td>
                <td>{m.sender || "—"}</td>
                <td>{m.subject || "—"}</td>
                <td className="small">{m.attachment_name || "—"}</td>
                <td>
                  {m.invoice_id ? (
                    <Link to={`/invoices/${m.invoice_id}`}>{m.invoice_id}</Link>
                  ) : (
                    <span className="small muted">{m.error || m.status}</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
