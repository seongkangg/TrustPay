import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import duplicate from "../../../data/invoices/duplicate_invoice.json";
import lowRisk from "../../../data/invoices/low_risk_invoice.json";
import policyViolation from "../../../data/invoices/policy_violation_invoice.json";
import suspicious from "../../../data/invoices/suspicious_invoice.json";
import { api, fmtMoney, fmtTime } from "../api/client.js";
import RiskBadge from "../components/RiskBadge.jsx";
import StatusBadge from "../components/StatusBadge.jsx";

// Same fixtures the tests use (data/invoices/*.json) — one source of truth for the demo.
const SCENARIOS = [lowRisk, policyViolation, suspicious, duplicate];

function Tile({ label, value, className = "" }) {
  return (
    <div className={`tile ${className}`}>
      <div className="label">{label}</div>
      <div className="value">{value ?? "—"}</div>
    </div>
  );
}

export default function Dashboard() {
  const navigate = useNavigate();
  const [summary, setSummary] = useState(null);
  const [invoices, setInvoices] = useState([]);
  const [busy, setBusy] = useState(null);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    try {
      const [s, list] = await Promise.all([api.summary(), api.listInvoices({ limit: 100 })]);
      setSummary(s);
      setInvoices(list.items);
    } catch (err) {
      setError(err.message);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function runScenario(fx) {
    setBusy(fx.scenario);
    setError(null);
    try {
      const created = await api.createInvoice(fx.upload);
      await api.processInvoice(created.invoice_id);
      navigate(`/invoices/${created.invoice_id}`);
    } catch (err) {
      setError(`${fx.scenario}: ${err.message}`);
      setBusy(null);
    }
  }

  return (
    <>
      <h1>Invoice governance overview</h1>
      {error && <div className="alert danger">{error}</div>}

      <div className="tiles">
        <Tile label="Total invoices" value={summary?.total_invoices} />
        <Tile label="Low risk" value={summary?.by_risk.low} className="low" />
        <Tile label="Medium risk" value={summary?.by_risk.medium} className="medium" />
        <Tile label="High risk" value={summary?.by_risk.high} className="high" />
        <Tile label="Blocked actions" value={summary?.blocked_actions} className="blocked" />
        <Tile label="Pending approvals" value={summary?.pending_approvals} className="pending" />
        <Tile label="Sensitive-data detections" value={summary?.sensitive_data_detections} />
      </div>

      <h2>Submit a demo invoice</h2>
      <div className="scenarios">
        {SCENARIOS.map((fx) => (
          <div className="scenario" key={fx.scenario}>
            <div className="name">{fx.scenario}</div>
            <div className="small muted" style={{ margin: "4px 0 8px" }}>
              {fx.upload.vendor_name} · {fmtMoney(fx.upload.amount, fx.upload.currency)}
            </div>
            <button className="primary" disabled={busy != null} onClick={() => runScenario(fx)}>
              {busy === fx.scenario ? "Running agents…" : "Submit & process"}
            </button>
          </div>
        ))}
      </div>

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
        <p className="muted">No invoices yet. Submit a demo scenario above.</p>
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
