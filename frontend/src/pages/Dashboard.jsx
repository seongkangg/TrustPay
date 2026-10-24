import { useState } from "react";
import { Link } from "react-router-dom";

import { fmtMoney, fmtTime } from "../api/client.js";
import { ArrowUpIcon, CalendarIcon } from "../components/Icons.jsx";
import ReasonTag from "../components/ReasonTag.jsx";
import RollingNumber, { useRolling } from "../components/RollingNumber.jsx";
import { dayLabel, DayCalendar, RiskBars, Sparkline, VolumeChart } from "../components/SummaryCharts.jsx";
import { useDashboard } from "../data.jsx";

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

// The "% paid" pill rolls with the hero figures; its own component so only the pill re-renders.
function PaidPill({ share }) {
  const shown = useRolling(share);
  return <span className="delta up">{Math.round(shown)}% paid</span>;
}

// Overview: invoice volume (hover the chart to read any day), counts, risk mix, days and recent
// violations. Approving happens from the Inbox page; every invoice is on the Invoices page.
export default function Dashboard() {
  const { summary, invoices, error } = useDashboard();
  const [hover, setHover] = useState(null); // index of the day under the pointer, or null

  const days = summary?.by_day || [];
  const today = days[days.length - 1];
  // While a day is hovered the hero shows that day's money (from by_day); otherwise the totals.
  const hoverDay = hover !== null && days[hover]?.amount !== undefined ? days[hover] : null;
  const amounts = hoverDay
    ? { total: hoverDay.amount, paid: hoverDay.paid, withheld: hoverDay.withheld }
    : summary?.amounts;
  const paidShare = amounts?.total ? Math.round((amounts.paid / amounts.total) * 100) : null;
  // by_day is bucketed by UTC calendar day on the backend; say so wherever a day is named.
  const range = days.length ? `${dayLabel(days[0].date)} – ${dayLabel(days[days.length - 1].date)} (UTC)` : "";

  return (
    <>
      <h1 className="sr-only">Invoice governance overview</h1>
      {error && <div className="alert danger">{error}</div>}

      <section className="hero panel-plain" aria-labelledby="volume-h">
        <div className="hero-head">
          <div>
            <h2 id="volume-h" className="label">
              Invoice volume{hoverDay ? ` · ${dayLabel(hoverDay.date)} (UTC)` : ""}
            </h2>
            <div className="figure-row">
              <RollingNumber className="figure" value={amounts?.total} format={wholeDollars} />
              {paidShare !== null && <PaidPill share={paidShare} />}
            </div>
            {amounts && (
              <div className="split">
                <span>
                  <span className="key paid" /> Paid <RollingNumber className="strong" value={amounts.paid} format={fmtMoney} />
                </span>
                <span>
                  <span className="key withheld" /> Withheld{" "}
                  <RollingNumber className="strong" value={amounts.withheld} format={fmtMoney} />
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
            <span className="hint">Hover the chart to see any day</span>
          </div>
        </div>
        {summary ? <VolumeChart days={days} onHover={setHover} /> : <div className="volume-chart skeleton" />}
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
              {summary.sensitive_data_detections} with masked bank or tax data
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
        <div className="panel" aria-labelledby="violations-h">
          <div className="panel-head">
            <h2 id="violations-h">Recent policy violations</h2>
            <Link to="/invoices" className="small">
              All invoices
            </Link>
          </div>
          {summary?.recent_violations?.length ? (
            <ul className="violations">
              {summary.recent_violations.map((v, i) => (
                <li key={i}>
                  <div className="violation-head">
                    <Link to={`/invoices/${v.invoice_id}`} className="rowlink">
                      {v.invoice_id}
                    </Link>
                    <span className="muted small">{fmtTime(v.timestamp)}</span>
                  </div>
                  <span className="codes">
                    {v.reason_codes.map((c) => (
                      <ReasonTag key={c} code={c} />
                    ))}
                  </span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="muted small empty">{summary ? "No policy violations." : "Loading…"}</p>
          )}
        </div>
      </section>
    </>
  );
}
