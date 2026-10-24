import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { api, AWAITING_HUMAN, fmtMoney, fmtTime } from "../api/client.js";
import ApprovalQueue from "../components/ApprovalQueue.jsx";
import InboxCard from "../components/InboxCard.jsx";
import RiskBadge from "../components/RiskBadge.jsx";
import StatusBadge from "../components/StatusBadge.jsx";
import SummaryCharts from "../components/SummaryCharts.jsx";

const REFRESH_MS = 15_000;

function Tile({ label, value, className = "" }) {
  return (
    <div className={`tile ${className}`}>
      <div className="label">{label}</div>
      <div className="value">{value ?? "—"}</div>
    </div>
  );
}

// Read-only overview. Invoices arrive from the inbox and are processed automatically; the only
// action here is routing a reviewer to an invoice that needs a human decision.
export default function Dashboard() {
  const navigate = useNavigate();
  const [summary, setSummary] = useState(null);
  const [invoices, setInvoices] = useState([]);
  const [inbox, setInbox] = useState({ status: null, unavailable: false });
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    try {
      const [s, list] = await Promise.all([api.summary(), api.listInvoices({ limit: 100 })]);
      setSummary(s);
      setInvoices(list.items);
      setError(null);
    } catch (err) {
      setError(err.message);
    }
    try {
      setInbox({ status: await api.inboxStatus(), unavailable: false });
    } catch (err) {
      // 404 = the inbox feature is not on this backend; anything else is a transient error.
      if (err.status === 404) setInbox({ status: null, unavailable: true });
    }
  }, []);

  useEffect(() => {
    load();
    const timer = window.setInterval(load, REFRESH_MS);
    return () => window.clearInterval(timer);
  }, [load]);

  const awaiting = invoices.filter((inv) => AWAITING_HUMAN.includes(inv.status));
  const reasonCodes = Object.fromEntries(
    (summary?.recent_violations || []).map((v) => [v.invoice_id, v.reason_codes]),
  );
  const amounts = summary?.amounts;

  return (
    <>
      <h1>Invoice governance overview</h1>
      {error && <div className="alert danger">{error}</div>}

      <h2>
        Needs your approval{awaiting.length > 0 && <span className="muted"> · {awaiting.length}</span>}
      </h2>
      <ApprovalQueue items={awaiting} reasonCodes={reasonCodes} />

      <h2>At a glance</h2>
      <div className="tiles">
        <Tile label="Total invoices" value={summary?.total_invoices} />
        <Tile label="Low risk" value={summary?.by_risk.low} className="low" />
        <Tile label="Medium risk" value={summary?.by_risk.medium} className="medium" />
        <Tile label="High risk" value={summary?.by_risk.high} className="high" />
        <Tile label="Blocked actions" value={summary?.blocked_actions} className="blocked" />
        <Tile label="Pending approvals" value={summary?.pending_approvals} className="pending" />
        <Tile label="Sensitive-data detections" value={summary?.sensitive_data_detections} />
      </div>
      <div className="tiles" style={{ marginTop: 12 }}>
        <Tile label="Total amount" value={amounts && fmtMoney(amounts.total)} className="money" />
        <Tile label="Paid" value={amounts && fmtMoney(amounts.paid)} className="money low" />
        <Tile
          label="Withheld (pending + blocked)"
          value={amounts && fmtMoney(amounts.withheld)}
          className="money high"
        />
      </div>

      {summary && (
        <>
          <h2>Graphs</h2>
          <SummaryCharts summary={summary} />
        </>
      )}

      <h2>Inbox</h2>
      <InboxCard status={inbox.status} unavailable={inbox.unavailable} onSynced={load} />

      {summary?.recent_violations?.length > 0 && (
        <>
          <h2>Recent policy violations</h2>
          <div className="card">
            {summary.recent_violations.map((v, i) => (
              <div key={i} className="small" style={{ padding: "4px 0" }}>
                <a href={`/invoices/${v.invoice_id}`} onClick={(e) => { e.preventDefault(); navigate(`/invoices/${v.invoice_id}`); }}>
                  {v.invoice_id}
                </a>{" "}
                {v.reason_codes.map((c) => (
                  <code key={c}>{c}</code>
                ))}{" "}
                <span className="muted">{fmtTime(v.timestamp)}</span>
              </div>
            ))}
          </div>
        </>
      )}

      <h2>Invoices</h2>
      {invoices.length === 0 ? (
        <p className="muted">No invoices yet. They appear here as the inbox delivers them.</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Invoice</th>
              <th>Vendor</th>
              <th className="right">Amount</th>
              <th>Risk</th>
              <th>Status</th>
              <th>Recommendation</th>
              <th>Sensitive data</th>
              <th>Updated</th>
            </tr>
          </thead>
          <tbody>
            {invoices.map((inv) => (
              <tr key={inv.invoice_id} className="clickable" onClick={() => navigate(`/invoices/${inv.invoice_id}`)}>
                <td>
                  <a href={`/invoices/${inv.invoice_id}`} onClick={(e) => e.preventDefault()}>
                    {inv.invoice_id}
                  </a>
                </td>
                <td>{inv.vendor_name || "—"}</td>
                <td className="right">{fmtMoney(inv.amount, inv.currency)}</td>
                <td>
                  <RiskBadge level={inv.risk_level} />
                </td>
                <td>
                  <StatusBadge status={inv.status} />
                </td>
                <td style={{ textTransform: "capitalize" }}>{inv.recommendation || "—"}</td>
                <td>{inv.sensitive_data_detected ? <span className="badge risk-medium">masked</span> : "—"}</td>
                <td className="small muted">{fmtTime(inv.updated_at)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </>
  );
}
