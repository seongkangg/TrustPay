import { useState } from "react";

import { api, fmtTime } from "../api/client.js";

// Gmail inbox that feeds invoices in automatically: authorization, last sync, "Check inbox now" and
// the last sync result (same as the phone app). `status` is GET /inbox/status (or null while
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
      </div>
      <button className="primary wide" disabled={busy || !status.enabled} onClick={sync}>
        {busy ? "Checking…" : "Check inbox now"}
      </button>

      {error && <div className="alert danger small">{error}</div>}
      {!error && status.last_error && <div className="alert warn small">{status.last_error}</div>}

      {last && (
        <p className="result small muted">
          {result ? "Just now: " : "Last result: "}
          {last.checked} checked · {last.created?.length ?? 0} created ·{" "}
          {last.failed?.length ?? 0} failed
        </p>
      )}
    </div>
  );
}
