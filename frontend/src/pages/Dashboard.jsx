import { useCallback, useEffect, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";

import { api, AWAITING_HUMAN, fmtMoney, fmtTime } from "../api/client.js";
import ApprovalQueue from "../components/ApprovalQueue.jsx";
import { ArrowUpIcon, CalendarIcon } from "../components/Icons.jsx";
import InboxCard from "../components/InboxCard.jsx";
import RiskBadge from "../components/RiskBadge.jsx";
import StatusBadge from "../components/StatusBadge.jsx";
import { dayLabel, DayCalendar, RiskBars, Sparkline, VolumeChart } from "../components/SummaryCharts.jsx";

const REFRESH_MS = 15_000;

const wholeDollars = (amount) =>
  new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 }).format(amount);

function Kpi({ label, value, values, tone, note }) {
  return (
    <div className="panel kpi">
      <div className="kpi-head">
        <span className="label">{label}</span>
        {note}
      </div>
      <div className="value">{value ?? "—"}</div>
      {values && <Sparkline values={values} tone={tone} />}
    </div>
  );
}

// Read-only overview. Invoices arrive from the inbox and are processed automatically; the only
// action here is routing a reviewer to an invoice that needs a human decision.
export default function Dashboard() {
  const { hash } = useLocation();
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

  // The top nav links to sections of this page; scroll there once the data has rendered.
  const loaded = summary !== null;
  useEffect(() => {
    if (!loaded) return;
    if (hash) document.getElementById(hash.slice(1))?.scrollIntoView({ behavior: "smooth", block: "start" });
    else window.scrollTo({ top: 0, behavior: "smooth" });
  }, [hash, loaded]);

  const awaiting = invoices.filter((inv) => AWAITING_HUMAN.includes(inv.status));
  const reasonCodes = Object.fromEntries(
    (summary?.recent_violations || []).map((v) => [v.invoice_id, v.reason_codes]),
  );
  const amounts = summary?.amounts;
  const days = summary?.by_day || [];
  const today = days[days.length - 1];
  const paidShare = amounts?.total ? Math.round((amounts.paid / amounts.total) * 100) : null;
  // by_day is bucketed by UTC calendar day on the backend; say so wherever a day is named.
  const range = days.length ? `${dayLabel(days[0].date)} – ${dayLabel(days[days.length - 1].date)} (UTC)` : "";

  return (
    <>
      <h1 className="sr-only">Invoice governance overview</h1>
      {error && <div className="alert danger">{error}</div>}

      <section id="approvals" className="approvals" aria-labelledby="approvals-h">
        <h2 id="approvals-h">
          Needs your approval
          <span className={`count-pill ${awaiting.length ? "" : "quiet"}`}>{awaiting.length}</span>
          {awaiting.length === 0 && <span className="h-note">Nothing waiting. New invoices are checked automatically.</span>}
        </h2>
        <ApprovalQueue items={awaiting} reasonCodes={reasonCodes} />
      </section>

      <section className="hero" aria-labelledby="volume-h">
        <div className="hero-head">
          <div>
            <h2 id="volume-h" className="label">
              Invoice volume
            </h2>
            <div className="figure-row">
              <span className="figure">{amounts ? wholeDollars(amounts.total) : "—"}</span>
              {paidShare !== null && <span className="delta up">{paidShare}% paid</span>}
            </div>
            {amounts && (
              <div className="split">
                <span>
                  <span className="key paid" /> Paid <strong>{fmtMoney(amounts.paid)}</strong>
                </span>
                <span>
                  <span className="key withheld" /> Withheld <strong>{fmtMoney(amounts.withheld)}</strong>
                </span>
              </div>
            )}
          </div>
          <div className="hero-side">
            <span className="range">
              <CalendarIcon size={15} /> Last 14 days
            </span>
            <span className="legend">
              <span>
                <span className="key received" /> Received
              </span>
              <span>
                <span className="key completed" /> Completed
              </span>
            </span>
          </div>
        </div>
        {summary ? <VolumeChart days={days} /> : <div className="volume-chart skeleton" />}
      </section>

      <section className="kpis" aria-label="Invoice counts">
        <Kpi
          label="Received"
          value={summary?.total_invoices}
          values={days.map((d) => d.received)}
          note={
            today?.received > 0 && (
              <span className="delta up">
                <ArrowUpIcon /> {today.received} on {dayLabel(today.date)}
              </span>
            )
          }
        />
        <Kpi label="Completed" value={summary?.by_status.COMPLETED ?? (summary && 0)} values={days.map((d) => d.completed)} />
        <Kpi
          label="Blocked"
          value={summary?.by_status.BLOCKED ?? (summary && 0)}
          values={days.map((d) => d.blocked)}
          tone={summary?.by_status.BLOCKED ? "danger" : "accent"}
        />
      </section>

      <section className="lower">
        <div className="panel" aria-labelledby="risk-h">
          <div className="panel-head">
            <h2 id="risk-h">Risk mix</h2>
            <span className="muted small">All invoices</span>
          </div>
          <RiskBars invoices={invoices} />
          {summary && (
            <p className="panel-foot small muted">
              {summary.blocked_actions} blocked tool call{summary.blocked_actions === 1 ? "" : "s"} ·{" "}
              {summary.sensitive_data_detections} invoice{summary.sensitive_data_detections === 1 ? "" : "s"} with
              masked bank or tax data
            </p>
          )}
        </div>
        <div className="panel" aria-labelledby="days-h">
          <div className="panel-head">
            <h2 id="days-h">Received per day</h2>
            <span className="muted small">{range}</span>
          </div>
          <DayCalendar days={days} />
        </div>
      </section>

      <section id="inbox" aria-labelledby="inbox-h">
        <h2 id="inbox-h">Inbox</h2>
        <InboxCard status={inbox.status} unavailable={inbox.unavailable} onSynced={load} />
      </section>

      {summary?.recent_violations?.length > 0 && (
        <section aria-labelledby="violations-h">
          <h2 id="violations-h">Recent policy violations</h2>
          <ul className="panel violations">
            {summary.recent_violations.map((v, i) => (
              <li key={i}>
                <Link to={`/invoices/${v.invoice_id}`}>{v.invoice_id}</Link>
                <span className="codes">
                  {v.reason_codes.map((c) => (
                    <code key={c}>{c}</code>
                  ))}
                </span>
                <span className="muted small">{fmtTime(v.timestamp)}</span>
              </li>
            ))}
          </ul>
        </section>
      )}

      <section id="invoices" aria-labelledby="invoices-h">
        <h2 id="invoices-h">
          Invoices{invoices.length > 0 && <span className="count-pill quiet">{invoices.length}</span>}
        </h2>
        {invoices.length === 0 ? (
          <p className="panel empty muted">No invoices yet. They appear here as the inbox delivers them.</p>
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Invoice</th>
                  <th>Vendor</th>
                  <th className="right">Amount</th>
                  <th className="hide-sm">Risk</th>
                  <th>Status</th>
                  <th className="hide-sm">Recommendation</th>
                  <th className="hide-sm">Sensitive data</th>
                  <th className="hide-sm">Updated</th>
                </tr>
              </thead>
              <tbody>
                {invoices.map((inv) => (
                  <tr key={inv.invoice_id} className="clickable" onClick={() => navigate(`/invoices/${inv.invoice_id}`)}>
                    <td>
                      <Link to={`/invoices/${inv.invoice_id}`} className="rowlink">
                        {inv.invoice_id}
                      </Link>
                    </td>
                    <td>{inv.vendor_name || "—"}</td>
                    <td className="right num">{fmtMoney(inv.amount, inv.currency)}</td>
                    <td className="hide-sm">
                      <RiskBadge level={inv.risk_level} />
                    </td>
                    <td>
                      <StatusBadge status={inv.status} />
                    </td>
                    <td className="cap hide-sm">{inv.recommendation || "—"}</td>
                    <td className="hide-sm">{inv.sensitive_data_detected ? <span className="badge">Masked</span> : "—"}</td>
                    <td className="small muted hide-sm">{fmtTime(inv.updated_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </>
  );
}
