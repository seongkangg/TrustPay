import { fmtPct, human } from "../api/client.js";
import { reasonLabel } from "./ReasonTag.jsx";

// Agent steps as a bar chart (Intake → Verify → Risk → Approval), same as the phone app. One
// reading for every bar: higher is better, and a bar under the dashed policy threshold
// (GET /mock/thresholds, from data/approval_limits.json — never hard-coded here) needs a person.
// Intake, Verify and Approval are the agents' own confidence. The Risk agent's confidence is
// always 100% (fixed rules), so its bar shows how clear the invoice is by policy instead: the risk
// level the rules assigned, minus a step for each extra issue. Each label has an info button whose
// tooltip says what the bar measures and why it reads what it does for this invoice. Bars grow in
// once (CSS, off for reduced motion).
const STEPS = [
  {
    key: "intake_agent",
    label: "Intake",
    about: "How reliably the invoice was read: the lowest confidence among the required fields.",
  },
  {
    key: "verification_agent",
    label: "Verify",
    about: "Share of the vendor, purchase-order and duplicate checks that came back confirmed.",
  },
  {
    key: "policy_risk_agent",
    label: "Risk",
    about:
      "How safe this invoice is to accept under the policy rules. Low risk 100%, medium 60%, high 30%; each extra issue takes off 10 points.",
  },
  {
    key: "approval_agent",
    label: "Approval",
    about: "How often the AI gave the same recommendation when asked 5 times.",
  },
];

// Display scale for the Risk bar (not policy: the rules have already decided the level).
const RISK_CLEARANCE = { low: 1, medium: 0.6, high: 0.3 };
const PER_EXTRA_ISSUE = 0.1;

const clamp01 = (v) => Math.min(1, Math.max(0, v));

// Low risk counts no issues (its codes are the "passed" kind).
function riskIssues(d) {
  return d.risk_level === "low" ? [] : (d.reason_codes || []).filter((c) => c !== "POLICY_PASSED");
}

function riskClearance(d) {
  const base = RISK_CLEARANCE[d.risk_level];
  if (base == null) return null;
  return clamp01(base - PER_EXTRA_ISSUE * Math.max(0, riskIssues(d).length - 1));
}

// The invoice-specific line under the general description.
function detail(key, d) {
  if (!d) return "This step did not run for this invoice.";
  if (key === "policy_risk_agent") {
    const issues = riskIssues(d);
    return `${human(d.risk_level)} risk${issues.length ? `: ${issues.map(reasonLabel).join(", ")}` : ", every rule passed"}.`;
  }
  const missing = d.explanation?.missing_information || [];
  if (key === "intake_agent" && missing.length) return `Missing: ${missing.map(human).join(", ")}.`;
  const codes = (d.reason_codes || []).filter((c) => c !== "POLICY_PASSED");
  if (codes.length) return `Flagged: ${codes.map(reasonLabel).join(", ")}.`;
  return "Nothing flagged at this step.";
}

// decisions: AgentDecision objects (oldest first; the latest per agent wins).
export default function ConfidenceChart({ confidence, decisions, threshold }) {
  const latest = {};
  for (const d of decisions) latest[d.agent] = d;
  const bars = STEPS.map((s) => {
    const d = latest[s.key];
    const raw = d == null ? null : s.key === "policy_risk_agent" ? riskClearance(d) : d.confidence;
    return {
      ...s,
      value: raw == null ? null : clamp01(raw),
      high: s.key === "policy_risk_agent" && d?.risk_level === "high",
      detail: detail(s.key, d),
    };
  });
  const value = confidence ?? 0;
  const below = (v) => threshold != null && v != null && v < threshold;
  const flagged = bars.filter((b) => below(b.value));

  return (
    <div className="confidence">
      <div className="conf-head">
        <strong>Confidence by step</strong>
        <span className={`small ${below(value) ? "warn-text" : "muted"}`}>
          Final {fmtPct(value)}
          {threshold != null ? ` · ${below(value) ? "below" : "above"} the ${fmtPct(threshold)} policy threshold` : ""}
        </span>
        <span className="small muted">
          {flagged.length === 0
            ? "Higher is better. Every step clears the dashed line."
            : `Higher is better. Needs a person: ${flagged.map((b) => b.label).join(", ")}.`}
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
                  className={`conf-bar ${b.high ? "high" : below(b.value) ? "below" : ""}`}
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
            <span className="conf-info" tabIndex={0} role="button" aria-label={`About ${b.label}`}>
              i
              <span className="conf-tip" role="tooltip">
                {b.about}
                <span className="conf-tip-detail">{b.detail}</span>
              </span>
            </span>
            {b.value == null && <span className="muted small"> · did not run</span>}
          </span>
        ))}
      </div>
    </div>
  );
}
