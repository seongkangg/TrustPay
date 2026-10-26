import { useNavigate } from "react-router-dom";

import { fmtAgo, fmtMoney } from "../api/client.js";
import { ChevronRightIcon } from "./Icons.jsx";
import ReasonTag from "./ReasonTag.jsx";
import RiskBadge from "./RiskBadge.jsx";
import StatusBadge from "./StatusBadge.jsx";
import VendorAvatar from "./VendorAvatar.jsx";

const MAX_TAGS = 2;

// Invoices waiting on a human (PENDING_APPROVAL / BLOCKED), as a table: vendor and ID, how long it
// has waited, status / risk and up to two reason tags, the amount, and a Review button. The
// decision itself is taken on the invoice page.
export default function ApprovalQueue({ items, reasonCodes = {} }) {
  const navigate = useNavigate();
  return (
    <div className="panel table-panel">
      <table className="queue-table">
        <thead>
          <tr>
            <th>Vendor</th>
            <th className="hide-sm">Waiting</th>
            <th>Why it stopped</th>
            <th className="right">Amount</th>
            <th aria-label="Review" />
          </tr>
        </thead>
        <tbody>
          {items.map((inv) => {
            const codes = reasonCodes[inv.invoice_id] || [];
            const extra = codes.length - MAX_TAGS;
            const open = () => navigate(`/invoices/${inv.invoice_id}`);
            return (
              <tr
                key={inv.invoice_id}
                className={`clickable ${inv.status === "BLOCKED" ? "blocked" : ""}`}
                tabIndex={0}
                onClick={open}
                onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && (e.preventDefault(), open())}
                aria-label={`Review ${inv.vendor_name || "unknown vendor"}, ${fmtMoney(inv.amount, inv.currency)}`}
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
                <td className="muted nowrap hide-sm">{fmtAgo(inv.updated_at).replace(" ago", "")}</td>
                <td>
                  <span className="queue-tags">
                    <StatusBadge status={inv.status} />
                    <RiskBadge level={inv.risk_level} />
                    {codes.slice(0, MAX_TAGS).map((c) => (
                      <ReasonTag key={c} code={c} />
                    ))}
                    {extra > 0 && <span className="badge">+{extra} more</span>}
                  </span>
                </td>
                <td className="right inv-amount">{fmtMoney(inv.amount, inv.currency)}</td>
                <td className="right">
                  <span className="button primary queue-review">
                    Review <ChevronRightIcon />
                  </span>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
