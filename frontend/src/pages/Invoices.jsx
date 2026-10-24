import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { fmtMoney, human } from "../api/client.js";
import RiskBadge from "../components/RiskBadge.jsx";
import StatusBadge from "../components/StatusBadge.jsx";
import VendorAvatar from "../components/VendorAvatar.jsx";
import { useDashboard } from "../data.jsx";

// Outcome filters over InvoiceStatus (same as the phone app). FAILED belongs to none of the three,
// so it shows under All only.
const FILTERS = [
  { key: "all", label: "All", statuses: null },
  {
    key: "pending",
    label: "Pending",
    statuses: ["RECEIVED", "EXTRACTED", "VERIFYING", "VERIFIED", "RISK_REVIEW", "PENDING_APPROVAL", "BLOCKED"],
  },
  { key: "accepted", label: "Accepted", statuses: ["APPROVED", "COMPLETED"] },
  { key: "rejected", label: "Rejected", statuses: ["REJECTED"] },
];

const EMPTY = {
  pending: "Nothing pending. Every invoice has been decided.",
  accepted: "No accepted invoices yet.",
  rejected: "No rejected invoices.",
};

const matches = (filter, inv) => !filter.statuses || filter.statuses.includes(inv.status);

const PAGE = 12;

const wholeDollars = (amount) =>
  new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 }).format(amount);

// "Today", "Yesterday", or "Oct 22" (adds the year when it is not this year), by the browser's date.
function dayHeading(date) {
  const today = new Date();
  const startOf = (d) => new Date(d.getFullYear(), d.getMonth(), d.getDate()).getTime();
  const diff = Math.round((startOf(today) - startOf(date)) / 86400000);
  if (diff === 0) return "Today";
  if (diff === 1) return "Yesterday";
  return date.toLocaleDateString("en-US", {
    weekday: "short",
    month: "short",
    day: "numeric",
    ...(date.getFullYear() !== today.getFullYear() && { year: "numeric" }),
  });
}

// Consecutive invoices (already newest first) grouped under their day's heading.
function groupByDay(items) {
  const groups = [];
  for (const inv of items) {
    const heading = inv.updated_at ? dayHeading(new Date(inv.updated_at)) : "Undated";
    const last = groups[groups.length - 1];
    if (last && last.heading === heading) last.items.push(inv);
    else groups.push({ heading, items: [inv] });
  }
  return groups;
}

// Invoices: a summary strip, outcome filters, and every invoice grouped by day, a page at a time.
export default function Invoices() {
  const { invoices, summary, error } = useDashboard();
  const navigate = useNavigate();
  const [filterKey, setFilterKey] = useState("all");
  const [limit, setLimit] = useState(PAGE);
  const filter = FILTERS.find((f) => f.key === filterKey);
  const options = FILTERS.map((f) => ({ ...f, count: invoices.filter((inv) => matches(f, inv)).length }));
  const shown = invoices.filter((inv) => matches(filter, inv));
  const visible = shown.slice(0, limit);
  const remaining = shown.length - visible.length;
  const total = shown.reduce((sum, inv) => sum + (inv.amount || 0), 0);
  const split = options.filter((o) => o.key !== "all" && o.count > 0);

  return (
    <>
      <h1 className="sr-only">Invoices</h1>
      {error && <div className="alert danger">{error}</div>}

      <section className="inv-summary panel" aria-label="Summary">
        <div>
          <div className="label">Total amount{filter.key === "all" ? "" : ` · ${filter.label}`}</div>
          <div className="inv-total">{wholeDollars(total)}</div>
          <div className="muted small">
            {shown.length} invoice{shown.length === 1 ? "" : "s"}
          </div>
        </div>
        {filter.key === "all" && split.length > 0 && (
          <div className="inv-split">
            <div className="split-bar">
              {split.map((o) => (
                <span key={o.key} className={`seg ${o.key}`} style={{ flex: o.count }} />
              ))}
            </div>
            <div className="split-legend">
              {split.map((o) => (
                <span key={o.key}>
                  <span className={`key ${o.key}`} /> {o.label} <strong>{o.count}</strong>
                </span>
              ))}
            </div>
          </div>
        )}
      </section>

      <div className="inv-toolbar">
        <h2>{filter.key === "all" ? "All invoices" : `${filter.label} invoices`}</h2>
        <div className="segmented" role="tablist" aria-label="Filter invoices">
          {options.map((o) => (
            <button
              key={o.key}
              role="tab"
              aria-selected={o.key === filterKey}
              className={o.key === filterKey ? "on" : undefined}
              onClick={() => {
                setFilterKey(o.key);
                setLimit(PAGE); // a new filter starts back at the first page
              }}
            >
              {o.label} <span className="seg-count">{o.count}</span>
            </button>
          ))}
        </div>
      </div>

      {invoices.length === 0 ? (
        <p className="panel empty muted">
          {summary ? "No invoices yet. They appear here as the inbox delivers them." : "Loading…"}
        </p>
      ) : shown.length === 0 ? (
        <p className="panel empty muted">{EMPTY[filter.key]}</p>
      ) : (
        <>
          {groupByDay(visible).map((g) => (
            <section key={g.heading} className="inv-group" aria-label={g.heading}>
              <h3 className="day-heading">{g.heading}</h3>
              <div className="inv-list panel">
                {g.items.map((inv) => (
                  <InvoiceRow key={inv.invoice_id} inv={inv} onOpen={() => navigate(`/invoices/${inv.invoice_id}`)} />
                ))}
              </div>
            </section>
          ))}
          {remaining > 0 ? (
            <button className="more" onClick={() => setLimit((n) => n + PAGE)}>
              Show {Math.min(PAGE, remaining)} more <span className="muted">· {remaining} left</span>
            </button>
          ) : (
            shown.length > PAGE && (
              <button className="more" onClick={() => setLimit(PAGE)}>
                Show less
              </button>
            )
          )}
        </>
      )}
    </>
  );
}

function InvoiceRow({ inv, onOpen }) {
  const time = inv.updated_at
    ? new Date(inv.updated_at).toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" })
    : "";
  return (
    <div
      className="inv-row"
      role="link"
      tabIndex={0}
      onClick={onOpen}
      onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && (e.preventDefault(), onOpen())}
      aria-label={`${inv.vendor_name || "Unknown vendor"}, ${fmtMoney(inv.amount, inv.currency)}`}
    >
      <VendorAvatar name={inv.vendor_name} />
      <span className="inv-who">
        <span className="inv-vendor">{inv.vendor_name || "Unknown vendor"}</span>
        <span className="muted small">
          {inv.invoice_id}
          {time ? ` · ${time}` : ""}
        </span>
      </span>
      <span className="inv-badges">
        <StatusBadge status={inv.status} />
        <RiskBadge level={inv.risk_level} />
        {inv.sensitive_data_detected && <span className="badge">Masked</span>}
      </span>
      <span className="inv-rec muted small">{inv.recommendation ? `AI: ${human(inv.recommendation)}` : "—"}</span>
      <span className="inv-amount">{fmtMoney(inv.amount, inv.currency)}</span>
    </div>
  );
}
