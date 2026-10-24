import { human } from "../api/client.js";

// Plain-English wording for ReasonCode (backend/models/enums.py). Keys must match the enum.
const REASONS = {
  AMOUNT_ABOVE_LIMIT: ["Over approval limit", "Amount exceeds this approver's limit."],
  UNKNOWN_VENDOR: ["Unknown vendor", "Vendor isn't on the approved list."],
  VENDOR_UNVERIFIED: ["Vendor not verified", "Vendor hasn't been verified yet."],
  DUPLICATE_INVOICE: ["Possible duplicate", "Looks like an invoice already received."],
  PO_AMOUNT_MISMATCH: ["Doesn't match PO", "Amount differs from the purchase order."],
  INVALID_PURCHASE_ORDER: ["PO not found", "Purchase order is missing or closed."],
  SENSITIVE_DATA_DETECTED: ["Sensitive info found", "Bank or tax details found and hidden."],
  UNAUTHORIZED_TOOL_CALL: ["Action not permitted", "An automated step was blocked."],
  LOW_CONFIDENCE: ["Unclear details", "Some details couldn't be read reliably."],
  MISSING_REQUIRED_FIELD: ["Missing information", "Required details are missing."],
  MALFORMED_FIELD: ["Invalid format", "A date or amount is in the wrong format."],
  AGENT_FAILURE: ["Processing error", "Automatic check failed; needs a person."],
  MOCK_SYSTEM_UNAVAILABLE: ["System unavailable", "A connected system didn't respond."],
  INSUFFICIENT_EVIDENCE: ["Not enough information", "Too little information to decide safely."],
  POLICY_PASSED: ["All checks passed", "Every policy check passed."],
};

// Pill colour: red = violation (default), yellow = uncertain / needs a check, green = passed.
const UNCERTAIN = new Set([
  "VENDOR_UNVERIFIED", "SENSITIVE_DATA_DETECTED", "LOW_CONFIDENCE", "MISSING_REQUIRED_FIELD",
  "MALFORMED_FIELD", "AGENT_FAILURE", "MOCK_SYSTEM_UNAVAILABLE", "INSUFFICIENT_EVIDENCE",
]);
const PASSED = new Set(["POLICY_PASSED"]);

// Readable violation pill; hover or keyboard focus shows a one-line summary.
export default function ReasonTag({ code }) {
  const [label, summary] = REASONS[code] || [human(code), null];
  const tone = PASSED.has(code) ? "pass" : UNCERTAIN.has(code) ? "warn" : "fail";
  return (
    <span className={`reason reason-${tone}`} tabIndex={summary ? 0 : undefined}>
      {label}
      {summary && <span className="reason-tip" role="tooltip">{summary}</span>}
    </span>
  );
}
