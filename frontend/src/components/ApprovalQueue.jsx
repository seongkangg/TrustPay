import { useNavigate } from "react-router-dom";

import { fmtAgo, fmtMoney } from "../api/client.js";
import { ChevronRightIcon } from "./Icons.jsx";
import ReasonTag from "./ReasonTag.jsx";
import RiskBadge from "./RiskBadge.jsx";
import StatusBadge from "./StatusBadge.jsx";
import VendorAvatar from "./VendorAvatar.jsx";

const MAX_TAGS = 2;

// Invoices waiting on a human (PENDING_APPROVAL / BLOCKED), as rows in one card like the phone app:
// vendor avatar, vendor and amount, ID and how long it has waited, status / risk and up to two
// reason tags, and a Review button. The decision itself is taken on the invoice page.
export default function ApprovalQueue({ items, reasonCodes = {} }) {
  const navigate = useNavigate();
  return (
    <div className="queue panel">
      {items.map((inv) => {
        const codes = reasonCodes[inv.invoice_id] || [];
        const extra = codes.length - MAX_TAGS;
        const open = () => navigate(`/invoices/${inv.invoice_id}`);
        return (
          <div
            key={inv.invoice_id}
            className={`queue-row ${inv.status === "BLOCKED" ? "blocked" : ""}`}
            role="link"
            tabIndex={0}
            onClick={open}
            onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && (e.preventDefault(), open())}
            aria-label={`Review ${inv.vendor_name || "unknown vendor"}, ${fmtMoney(inv.amount, inv.currency)}`}
          >
            <VendorAvatar name={inv.vendor_name} />
            <span className="queue-who">
              <span className="inv-vendor">{inv.vendor_name || "Unknown vendor"}</span>
              <span className="muted small">
                {inv.invoice_id} · waiting {fmtAgo(inv.updated_at).replace(" ago", "")}
              </span>
            </span>
            <span className="queue-tags">
              <StatusBadge status={inv.status} />
              <RiskBadge level={inv.risk_level} />
              {codes.slice(0, MAX_TAGS).map((c) => (
                <ReasonTag key={c} code={c} />
              ))}
              {extra > 0 && <span className="badge">+{extra} more</span>}
            </span>
            <span className="inv-amount">{fmtMoney(inv.amount, inv.currency)}</span>
            <span className="button primary queue-review">
              Review <ChevronRightIcon />
            </span>
          </div>
        );
      })}
    </div>
  );
}
