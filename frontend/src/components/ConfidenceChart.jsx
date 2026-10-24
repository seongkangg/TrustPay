import { fmtPct } from "../api/client.js";

// Confidence by agent step as a bar chart (Intake → Verify → Risk → Approval), same as the phone
// app: bar height is that step's evidence-based confidence, value on top, step underneath. The
// dashed line is the policy threshold (GET /mock/thresholds, from data/approval_limits.json —
// never hard-coded here); bars under it are amber. Bars grow in once (CSS, off for reduced motion).
const STEPS = [
  { key: "intake_agent", label: "Intake" },
  { key: "verification_agent", label: "Verify" },
  { key: "policy_risk_agent", label: "Risk" },
  { key: "approval_agent", label: "Approval" },
];

const clamp01 = (v) => Math.min(1, Math.max(0, v));

// decisions: AgentDecision objects (oldest first; the latest per agent wins).
export default function ConfidenceChart({ confidence, decisions, threshold }) {
  const latest = {};
  for (const d of decisions) latest[d.agent] = d;
  const bars = STEPS.map((s) => {
    const c = latest[s.key]?.confidence;
    return { ...s, value: c == null ? null : clamp01(c) };
  });
  const value = confidence ?? 0;
  const below = (v) => threshold != null && v != null && v < threshold;
  const unsure = bars.filter((b) => below(b.value));

  return (
    <div className="confidence">
      <div className="conf-head">
        <strong>Confidence by step</strong>
        <span className={`small ${below(value) ? "warn-text" : "muted"}`}>
          Final {fmtPct(value)}
          {threshold != null ? ` · ${below(value) ? "below" : "above"} the ${fmtPct(threshold)} policy threshold` : ""}
        </span>
        <span className="small muted">
          {unsure.length === 0
            ? "Every step was confident."
            : `${unsure.map((b) => b.label).join(", ")} ${unsure.length === 1 ? "was" : "were"} unsure.`}
        </span>
      </div>
      <div className="conf-chart">
        <div className="conf-axis" aria-hidden="true">
          <span style={{ bottom: "100%" }}>100%</span>
          <span style={{ bottom: "50%" }}>50%</span>
          <span style={{ bottom: "0%" }}>0%</span>
        </div>
        <div className="conf-plot">
          {[0, 0.5, 1].map((g) => (
            <span key={g} className="conf-grid" style={{ bottom: `${g * 100}%` }} aria-hidden="true" />
          ))}
          {threshold != null && (
            <span className="conf-threshold" style={{ bottom: `${threshold * 100}%` }}>
              <span className="conf-threshold-label">{fmtPct(threshold)}</span>
            </span>
          )}
          {bars.map((b, i) => (
            <div key={b.key} className="conf-slot">
              {b.value != null && (
                <div
                  className={`conf-bar ${below(b.value) ? "below" : ""}`}
                  style={{ height: `${Math.max(2, b.value * 100)}%`, animationDelay: `${i * 70}ms` }}
                  title={`${b.label}: ${fmtPct(b.value)}`}
                >
                  <span className="conf-value">{fmtPct(b.value)}</span>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
      <div className="conf-labels">
        {bars.map((b) => (
          <span key={b.key}>
            {b.label}
            {b.value == null && <span className="muted small"> · did not run</span>}
          </span>
        ))}
      </div>
    </div>
  );
}
