// Low / Medium / High pill. One place for risk colors (see --risk-* tokens in dashboard.css).
export default function RiskBadge({ level }) {
  if (!level) return <span className="badge">No risk yet</span>;
  return <span className={`badge risk-${level}`}>{level.charAt(0).toUpperCase() + level.slice(1)} risk</span>;
}
