import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { api, fmtMoney, fmtPct, human } from "../api/client.js";
import { ChevronRightIcon } from "../components/Icons.jsx";
import PageHeader from "../components/PageHeader.jsx";
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

// Invoices: a summary strip, outcome filters, and every invoice as a table row, a page at a time.
export default function Invoices() {
  const { invoices, summary, error } = useDashboard();
  const navigate = useNavigate();
  const [filterKey, setFilterKey] = useState("all");
  const [limit, setLimit] = useState(PAGE);
  const [threshold, setThreshold] = useState(null);
  // Policy constant; without it the confidence is shown uncoloured.
  useEffect(() => {
    api
      .thresholds()
      .then((t) => setThreshold(t.confidence_threshold ?? null))
      .catch(() => {});
  }, []);
  const filter = FILTERS.find((f) => f.key === filterKey);
  const options = FILTERS.map((f) => ({ ...f, count: invoices.filter((inv) => matches(f, inv)).length }));
  const shown = invoices.filter((inv) => matches(filter, inv));
  const visible = shown.slice(0, limit);
  const remaining = shown.length - visible.length;
  const total = shown.reduce((sum, inv) => sum + (inv.amount || 0), 0);
  const split = options.filter((o) => o.key !== "all" && o.count > 0);

  return (
    <>
      <PageHeader title="Invoices">Every invoice the inbox has delivered, newest first. Open one to see its review.</PageHeader>
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
          <div className="panel table-panel">
            <table className="inv-table">
              <thead>
                <tr>
                  <th>Vendor</th>
                  <th className="hide-sm">Received</th>
                  <th>Status</th>
                  <th className="hide-sm">Risk</th>
                  <th className="hide-md">AI recommendation</th>
                  <th>AI confidence</th>
                  <th className="right">Amount</th>
                  <th aria-label="Open" />
                </tr>
              </thead>
              <tbody>
                {visible.map((inv) => (
                  <InvoiceRow key={inv.invoice_id} inv={inv} threshold={threshold} onOpen={() => navigate(`/invoices/${inv.invoice_id}`)} />
                ))}
              </tbody>
            </table>
          </div>
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

// "Oct 22, 3:04 PM" (adds the year when it is not this year), by the browser's clock.
function received(iso) {
  if (!iso) return "—";
  const d = new Date(iso);
  const sameYear = d.getFullYear() === new Date().getFullYear();
  return d.toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    ...(!sameYear && { year: "numeric" }),
    hour: "numeric",
    minute: "2-digit",
  });
}

// AI confidence: how sure the AI is of its recommendation (same number as the review page),
// amber under the policy threshold.
function InvoiceRow({ inv, threshold, onOpen }) {
  const conf = inv.recommendation_confidence;
  const unsure = threshold != null && conf != null && conf < threshold;
  return (
    <tr
      className="clickable"
      tabIndex={0}
      onClick={onOpen}
      onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && (e.preventDefault(), onOpen())}
      aria-label={`${inv.vendor_name || "Unknown vendor"}, ${fmtMoney(inv.amount, inv.currency)}`}
    >
      <td>
        <span className="cell-vendor">
          <VendorAvatar name={inv.vendor_name} />
          <span className="inv-who">
            <span className="inv-vendor">{inv.vendor_name || "Unknown vendor"}</span>
            <span className="muted small">{inv.invoice_id}</span>
          </span>
        </span>
      </td>
      <td className="muted nowrap hide-sm">{received(inv.updated_at)}</td>
      <td>
        <span className="inv-badges">
          <StatusBadge status={inv.status} />
          {inv.sensitive_data_detected && <span className="badge">Masked</span>}
        </span>
      </td>
      <td className="hide-sm">
        <RiskBadge level={inv.risk_level} />
      </td>
      <td className="muted hide-md">{inv.recommendation ? human(inv.recommendation) : "—"}</td>
      <td>
        <span
          className={`inv-conf ${unsure ? "below" : ""}`}
          title={conf == null ? "The AI has not recommended yet" : `The AI is ${fmtPct(conf)} sure of its recommendation`}
        >
          {fmtPct(conf)}
        </span>
      </td>
      <td className="right inv-amount">{fmtMoney(inv.amount, inv.currency)}</td>
      <td className="row-go" aria-hidden="true">
        <ChevronRightIcon />
      </td>
    </tr>
  );
}
