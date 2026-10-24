import { Link } from "react-router-dom";

import { fmtMoney, fmtTime } from "../api/client.js";
import { ChevronRightIcon } from "./Icons.jsx";
import RiskBadge from "./RiskBadge.jsx";
import StatusBadge from "./StatusBadge.jsx";

// Invoices waiting on a human (PENDING_APPROVAL / BLOCKED). The decision itself is taken on
// the invoice page (ApprovalPanel); this list only routes the reviewer there.
export default function ApprovalQueue({ items, reasonCodes = {} }) {
  if (items.length === 0) {
    return <p className="queue-empty muted">Nothing is waiting for a decision. New invoices are checked automatically.</p>;
  }
  return (
    <ul className="queue">
      {items.map((inv) => {
        const codes = reasonCodes[inv.invoice_id] || [];
        return (
          <li key={inv.invoice_id} className={inv.status === "BLOCKED" ? "blocked" : ""}>
            <div className="who">
              <span className="vendor">{inv.vendor_name || "Unknown vendor"}</span>
              <span className="small muted">
                {inv.invoice_id} · {fmtTime(inv.updated_at)}
              </span>
            </div>
            <div className="why">
              <StatusBadge status={inv.status} />
              <RiskBadge level={inv.risk_level} />
              {codes.map((c) => (
                <code key={c}>{c}</code>
              ))}
            </div>
            <span className="amount">{fmtMoney(inv.amount, inv.currency)}</span>
            <Link to={`/invoices/${inv.invoice_id}`} className="button primary">
              Review <ChevronRightIcon />
            </Link>
          </li>
        );
      })}
    </ul>
  );
}
