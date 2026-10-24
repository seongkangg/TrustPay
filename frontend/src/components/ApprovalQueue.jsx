import { Link } from "react-router-dom";

import { fmtMoney, fmtTime } from "../api/client.js";
import ReasonTag from "./ReasonTag.jsx";
import RiskBadge from "./RiskBadge.jsx";
import StatusBadge from "./StatusBadge.jsx";

// Invoices waiting on a human (PENDING_APPROVAL / BLOCKED). The decision itself is taken on
// the invoice page (ApprovalPanel); this list only routes the reviewer there.
export default function ApprovalQueue({ items, reasonCodes = {} }) {
  if (items.length === 0) {
    return <p className="muted">Nothing is waiting for a decision.</p>;
  }
  return (
    <div className="queue">
      {items.map((inv) => {
        const codes = reasonCodes[inv.invoice_id] || [];
        return (
          <div key={inv.invoice_id} className={`item ${inv.status === "BLOCKED" ? "blocked" : ""}`}>
            <div className="head">
              <span className="vendor">{inv.vendor_name || "Unknown vendor"}</span>
              <span className="amount">{fmtMoney(inv.amount, inv.currency)}</span>
            </div>
            <div>
              <StatusBadge status={inv.status} /> <RiskBadge level={inv.risk_level} />
            </div>
            {codes.length > 0 && (
              <div className="codes small">
                {codes.map((c) => (
                  <ReasonTag key={c} code={c} />
                ))}
              </div>
            )}
            <div className="foot small">
              <span className="muted">
                {inv.invoice_id} · {fmtTime(inv.updated_at)}
              </span>
              <Link to={`/invoices/${inv.invoice_id}`}>Review &amp; decide →</Link>
            </div>
          </div>
        );
      })}
    </div>
  );
}
