import { useState } from "react";

import { AWAITING_HUMAN, api, fmtPct, human } from "../api/client.js";

// AI recommendation on the left, explicit human decision on the right — never conflated.
export default function ApprovalPanel({ invoice, decisions, events, onDecided }) {
  const [reviewer, setReviewer] = useState("finance.reviewer@example.com");
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  const recommendation = decisions?.find((d) => d.agent === "approval_agent");
  const why = recommendation?.explanation || {};
  const humanEvent = events?.find((e) => e.event_type === "human_decision_recorded");
  const awaiting = AWAITING_HUMAN.includes(invoice.status);

  async function decide(kind) {
    setBusy(true);
    setError(null);
    try {
      const result = await (kind === "approve"
        ? api.approve(invoice.invoice_id, reviewer, note || undefined)
        : api.reject(invoice.invoice_id, reviewer, note || undefined));
      onDecided?.(result);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="card approval">
      <section className="recommendation">
        <h3>AI recommendation</h3>
        {invoice.recommendation ? (
          <>
            <div className="big">{human(invoice.recommendation)}</div>
            <div className="muted small">
              Confidence {fmtPct(invoice.recommendation_confidence)} · how much of this invoice was read and confirmed · governance decides
            </div>
            {why.reasons?.length > 0 && (
              <>
                <div className="small" style={{ marginTop: 8 }}>
                  <strong>Why</strong>
                </div>
                <ul className="why small">
                  {why.reasons.map((r, i) => (
                    <li key={i}>{r}</li>
                  ))}
                </ul>
              </>
            )}
            {why.policy_rules_triggered?.length > 0 && (
              <div className="small muted">
                Rules:{" "}
                {why.policy_rules_triggered.map((r) => (
                  <code key={r}>{r}</code>
                ))}
              </div>
            )}
            {why.evidence?.length > 0 && (
              <div className="small muted evidence">
                Evidence:{" "}
                {why.evidence.map((r) => (
                  <code key={r}>{r}</code>
                ))}
              </div>
            )}
          </>
        ) : (
          <p className="muted">No recommendation yet — the agents have not run.</p>
        )}
      </section>

      <section>
        <h3>Human decision</h3>
        {humanEvent ? (
          <div className="alert info">
            <strong>{human(humanEvent.output_summary)}</strong>
            <div className="small">{humanEvent.input_summary}</div>
          </div>
        ) : awaiting ? (
          <>
            <div className="alert warn small">
              Payment is withheld. This invoice is <strong>{human(invoice.status)}</strong> and needs a
              human decision.
            </div>
            <input
              value={reviewer}
              onChange={(e) => setReviewer(e.target.value)}
              placeholder="reviewer email"
              aria-label="reviewer"
            />
            <textarea
              value={note}
              onChange={(e) => setNote(e.target.value)}
              placeholder="note (optional)"
              rows={2}
              aria-label="note"
            />
            <div className="actions">
              <button className="approve" disabled={busy || !reviewer} onClick={() => decide("approve")}>
                Approve payment
              </button>
              <button className="reject" disabled={busy || !reviewer} onClick={() => decide("reject")}>
                Reject
              </button>
            </div>
            {error && <div className="alert danger small">{error}</div>}
          </>
        ) : (
          <p className="muted">
            {invoice.status === "COMPLETED"
              ? "Processed automatically — policy permitted and governance authorized payment."
              : "No human decision required at this stage."}
          </p>
        )}
      </section>
    </div>
  );
}
