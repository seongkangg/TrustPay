import { human } from "../api/client.js";

// Invoice state pill. BLOCKED / FAILED / REJECTED are deliberately loud.
export default function StatusBadge({ status }) {
  if (!status) return <span className="badge">—</span>;
  return <span className={`badge status-${status}`}>{human(status)}</span>;
}

// Allowed / blocked / escalated — used for tool calls, decisions, and policy results.
export function AuthBadge({ value }) {
  if (!value) return <span className="badge">—</span>;
  return <span className={`badge auth-${value}`}>{value}</span>;
}
