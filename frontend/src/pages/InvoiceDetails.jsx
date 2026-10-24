import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { api, AWAITING_HUMAN, fmtMoney, fmtTime, human } from "../api/client.js";
import AgentTimeline from "../components/AgentTimeline.jsx";
import ConfidenceChart from "../components/ConfidenceChart.jsx";
import { CheckIcon, ChevronDownIcon, XIcon } from "../components/Icons.jsx";
import ReasonTag from "../components/ReasonTag.jsx";
import RiskBadge from "../components/RiskBadge.jsx";
import StatusBadge from "../components/StatusBadge.jsx";
import ToolCallTable from "../components/ToolCallTable.jsx";
import { useDashboard } from "../data.jsx";

const ACTIVITY_PREVIEW = 8;

const VERDICT = { approve: "approve", escalate: "escalate", reject: "reject" };

// "2026-10-14" → "Oct 14, 2026", read as a calendar date (no time zone shift).
function fmtDate(iso) {
  if (!iso) return null;
  const [y, m, d] = iso.split("-").map(Number);
  return new Date(Date.UTC(y, m - 1, d)).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    timeZone: "UTC",
  });
}

// One invoice, laid out like the phone's review screen but in two columns: the case on the left
// (who and how much, where it stands, what the AI recommends and why, the source PDF, details,
// activity) and the decision pinned on the right. Approve / reject are the only write actions in
// the app. The AI recommendation and the human decision are never conflated.
export default function InvoiceDetails() {
  const { id } = useParams();
  const dashboard = useDashboard();
  const [invoice, setInvoice] = useState(null);
  const [timeline, setTimeline] = useState([]);
  const [threshold, setThreshold] = useState(null);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    try {
      const [inv, tl] = await Promise.all([api.getInvoice(id), api.timeline(id)]);
      setInvoice(inv);
      setTimeline(tl.entries);
      setError(null);
    } catch (err) {
      setError(err.message);
    }
  }, [id]);

  useEffect(() => {
    load();
  }, [load]);

  // The confidence threshold is a policy constant; without it the chart omits the marker.
  useEffect(() => {
    api
      .thresholds()
      .then((t) => setThreshold(t.confidence_threshold ?? null))
      .catch(() => setThreshold(null));
  }, []);

  if (error && !invoice) return <div className="alert danger">{error}</div>;
  if (!invoice) return <p className="muted">Loading…</p>;

  const decisions = timeline.filter((e) => e.kind === "decision").map((e) => e.data);
  const toolCalls = timeline.filter((e) => e.kind === "tool_call").map((e) => e.data);
  const events = timeline.filter((e) => e.kind === "event").map((e) => e.data);
  const blockedCalls = toolCalls.filter((c) => c.authorization !== "allowed").length;
  const recommendation = decisions.find((d) => d.agent === "approval_agent");
  const humanEvent = events.find((e) => e.event_type === "human_decision_recorded");
  const needsDecision = AWAITING_HUMAN.includes(invoice.status) && !humanEvent;
  const amount = fmtMoney(invoice.amount, invoice.currency);

  async function onDecided() {
    await load();
    // Keep the pages and the nav's waiting count in step with the decision.
    dashboard.load();
  }

  return (
    <>
      <nav className="crumbs small">
        <Link to="/invoices">← Invoices</Link>
        <span className="muted">·</span>
        <Link to={`/invoices/${id}/audit`}>Audit view</Link>
      </nav>
      {error && <div className="alert danger">{error}</div>}

      <div className="review">
        <div className="review-main">
          <Summary invoice={invoice} amount={amount} />
          <StateBanner invoice={invoice} humanEvent={humanEvent} needsDecision={needsDecision} />
          {blockedCalls > 0 && (
            <div className="alert danger small">
              {blockedCalls} unauthorized tool call{blockedCalls > 1 ? "s were" : " was"} blocked and recorded.
            </div>
          )}
          {invoice.sensitive_data_detected && (
            <div className="alert warn small">
              Bank or tax details were found and masked. Only the last four digits are shown, and they were never
              passed to a model or written to a log.
            </div>
          )}

          <section aria-labelledby="rec-h">
            <h2 id="rec-h">AI recommendation</h2>
            <Recommendation invoice={invoice} recommendation={recommendation} decisions={decisions} threshold={threshold} />
          </section>

          <section aria-labelledby="doc-h">
            <h2 id="doc-h">Source document</h2>
            <SourceDocument invoice={invoice} />
          </section>

          <section aria-labelledby="details-h">
            <h2 id="details-h">Invoice details</h2>
            <div className="card">
              <dl className="details">
                <Detail k="Vendor" v={invoice.vendor_name} sub={invoice.vendor_id || "Not in vendor master"} />
                <Detail k="Vendor invoice #" v={invoice.vendor_invoice_number} />
                <Detail k="Amount" v={amount} />
                <Detail k="Due date" v={fmtDate(invoice.due_date)} />
                <Detail k="Purchase order" v={invoice.purchase_order_id} />
                <Detail k="Received" v={fmtTime(invoice.created_at)} />
                <Detail k="Bank account" v={invoice.bank_account} masked />
                <Detail k="Routing number" v={invoice.routing_number} masked />
                <Detail k="Tax ID" v={invoice.tax_id} masked />
                <Detail k="Source" v={invoice.source_document || "Structured upload"} />
              </dl>
            </div>
          </section>

          <Activity timeline={timeline} />

          <Collapsible
            title="Tool calls"
            summary={`${toolCalls.length} call${toolCalls.length === 1 ? "" : "s"}${
              blockedCalls ? ` · ${blockedCalls} blocked` : " · all allowed"
            }`}
            alert={blockedCalls > 0}
          >
            <div className="card">
              <ToolCallTable calls={toolCalls} />
            </div>
          </Collapsible>
        </div>

        <aside className="review-side">
          <DecisionPanel
            invoice={invoice}
            amount={amount}
            humanEvent={humanEvent}
            needsDecision={needsDecision}
            onDecided={onDecided}
          />
        </aside>
      </div>
    </>
  );
}

// Who, how much, and when it is due: the first thing a reviewer needs.
function Summary({ invoice, amount }) {
  const due = fmtDate(invoice.due_date);
  const today = new Date().toISOString().slice(0, 10);
  const overdue = invoice.due_date && invoice.due_date < today && !["COMPLETED", "APPROVED"].includes(invoice.status);
  return (
    <header className="review-summary">
      <div className="badges-row">
        <StatusBadge status={invoice.status} />
        <RiskBadge level={invoice.risk_level} />
        {invoice.sensitive_data_detected && <span className="badge">Masked</span>}
      </div>
      <h1 className="review-vendor">{invoice.vendor_name || "Unknown vendor"}</h1>
      <div className="review-amount">{amount}</div>
      <div className="muted">
        {invoice.invoice_id}
        {invoice.vendor_invoice_number ? ` · ${invoice.vendor_invoice_number}` : ""}
        {due && (
          <>
            {" · Due "}
            <span className={overdue ? "overdue" : undefined}>
              {due}
              {overdue ? " (overdue)" : ""}
            </span>
          </>
        )}
      </div>
    </header>
  );
}

// One sentence on where this invoice stands and what, if anything, is expected of the reviewer.
function StateBanner({ invoice, humanEvent, needsDecision }) {
  let kind;
  let title;
  let body;
  if (humanEvent) {
    const rejected = invoice.status === "REJECTED";
    kind = rejected ? "danger" : "ok";
    title = rejected ? "Rejected" : "Approved";
    body = [human(humanEvent.output_summary), humanEvent.input_summary].filter(Boolean).join(" · ");
  } else if (needsDecision) {
    const blocked = invoice.status === "BLOCKED";
    kind = blocked ? "danger" : "info";
    title = blocked ? "Payment blocked — needs your decision" : "Payment on hold until you decide";
    body = blocked
      ? "Governance stopped automatic processing. Review the recommendation, then decide on the right."
      : "This invoice is over a limit or needs a check. Review the recommendation, then decide on the right.";
  } else if (invoice.status === "COMPLETED") {
    kind = "ok";
    title = "Paid automatically";
    body = "Policy permitted it and governance authorized the payment.";
  } else if (invoice.status === "FAILED") {
    kind = "danger";
    title = "Processing failed";
    body = "The automatic checks could not finish; nothing was paid.";
  } else {
    return null;
  }
  return (
    <div className={`banner ${kind}`}>
      <strong>{title}</strong>
      {body && <span>{body}</span>}
    </div>
  );
}

function Recommendation({ invoice, recommendation, decisions, threshold }) {
  const [showEvidence, setShowEvidence] = useState(false);
  if (!invoice.recommendation) {
    return <p className="card muted">No recommendation yet — the agents have not run.</p>;
  }
  const why = recommendation?.explanation || {};
  // Bare reason codes are already shown as tags; keep the sentences.
  const reasons = (why.reasons || []).filter((r) => !/^[A-Z_]+$/.test(r));
  const codes = recommendation?.reason_codes || [];
  const evidence = [...(why.policy_rules_triggered || []), ...(why.evidence || [])];
  return (
    <div className="card rec">
      <div className="rec-top">
        <span className={`verdict ${VERDICT[invoice.recommendation] || ""}`}>{human(invoice.recommendation)}</span>
        <span className="muted small">Advisory only. Governance rules decide what is allowed; you make the final call.</span>
      </div>
      <div className="rec-grid">
        <ConfidenceChart confidence={invoice.recommendation_confidence} decisions={decisions} threshold={threshold} />
        <div className="rec-why">
          {codes.length > 0 && (
            <div className="tags">
              {codes.map((c) => (
                <ReasonTag key={c} code={c} />
              ))}
            </div>
          )}
          {reasons.length > 0 && (
            <ul className="reasons">
              {reasons.map((r, i) => {
                // "New vendor: …" — the short heading before the colon is bold.
                const cut = r.indexOf(": ");
                return cut > 0 && cut < 40 ? (
                  <li key={i}>
                    <strong>{r.slice(0, cut)}.</strong> {r.slice(cut + 2)}
                  </li>
                ) : (
                  <li key={i}>{r}</li>
                );
              })}
            </ul>
          )}
          {why.recommended_next_step && (
            <div className="next-step">
              <strong>What to do</strong>
              <span>{why.recommended_next_step}</span>
            </div>
          )}
          {evidence.length > 0 && (
            <>
              <button className="linkish" onClick={() => setShowEvidence((v) => !v)} aria-expanded={showEvidence}>
                {showEvidence ? "Hide evidence" : `Show evidence (${evidence.length})`}
              </button>
              {showEvidence && (
                <div className="codes">
                  {evidence.map((e, i) => (
                    <code key={`${e}${i}`}>{e}</code>
                  ))}
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}

// The source invoice as a PDF download: the emailed PDF with bank, routing and tax numbers blacked
// out when a redacted copy was kept, else a masked copy rebuilt from its text.
function SourceDocument({ invoice }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const hasPdf = invoice.has_source_pdf;
  if (!hasPdf && !invoice.source_text) {
    return (
      <p className="card muted">
        {invoice.source_document
          ? `${invoice.source_document}: no readable text.`
          : "Entered as structured data; there is no source document."}
      </p>
    );
  }
  async function download() {
    setBusy(true);
    setError(null);
    try {
      await api.downloadDocument(invoice.invoice_id);
    } catch {
      setError("Couldn't download the PDF. Please try again.");
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="card doc">
      <span className="doc-icon" aria-hidden="true">
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
          <path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z" />
          <path d="M14 3v5h5M9 13h6M9 17h6" />
        </svg>
      </span>
      <div className="doc-text">
        <strong>{`${invoice.invoice_id}${hasPdf ? "" : "-masked"}.pdf`}</strong>
        {error && <span className="warn-text small">{error}</span>}
      </div>
      <button className="primary" onClick={download} disabled={busy}>
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
          <path d="M12 4v11M7 10l5 5 5-5M5 20h14" />
        </svg>
        {busy ? "Downloading…" : "Download PDF"}
      </button>
    </div>
  );
}

function Detail({ k, v, sub, masked }) {
  return (
    <div className="detail">
      <dt>{k}</dt>
      <dd>
        {v || "—"}
        {masked && v ? <span className="badge">Masked</span> : null}
        {sub ? <span className="muted small detail-sub">{sub}</span> : null}
      </dd>
    </div>
  );
}

// Agent decisions, tool calls and governance events in order; the latest steps first.
function Activity({ timeline }) {
  const [all, setAll] = useState(false);
  if (timeline.length === 0) return null;
  const items = all ? timeline : timeline.slice(-ACTIVITY_PREVIEW);
  return (
    <section aria-labelledby="activity-h">
      <h2 id="activity-h">
        Activity <span className="count-pill quiet">{timeline.length}</span>
      </h2>
      <div className="card">
        {!all && timeline.length > ACTIVITY_PREVIEW && (
          <button className="linkish show-all" onClick={() => setAll(true)}>
            Show all {timeline.length} steps
          </button>
        )}
        <AgentTimeline entries={items} />
      </div>
    </section>
  );
}

// A section whose body opens on demand, with a one-line summary in the header.
function Collapsible({ title, summary, alert, children }) {
  const [open, setOpen] = useState(false);
  return (
    <section>
      <button className="collapse-head" onClick={() => setOpen((v) => !v)} aria-expanded={open}>
        <span>
          <span className="collapse-title">{title}</span>
          <span className={`small ${alert ? "warn-text" : "muted"}`}>{summary}</span>
        </span>
        <ChevronDownIcon className={`chev ${open ? "open" : ""}`} />
      </button>
      {open && children}
    </section>
  );
}

// Pinned on the right: the reviewer's decision. Both actions ask first, because approving releases
// a payment and rejecting closes the invoice.
function DecisionPanel({ invoice, amount, humanEvent, needsDecision, onDecided }) {
  const [reviewer, setReviewer] = useState("finance.reviewer@example.com");
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  async function decide(kind) {
    const vendor = invoice.vendor_name || "this vendor";
    const ok = window.confirm(
      kind === "approve"
        ? `Approve ${amount}? Payment to ${vendor} will be released.`
        : `Reject this invoice? ${vendor} will not be paid for ${invoice.vendor_invoice_number || invoice.invoice_id}.`,
    );
    if (!ok) return;
    setBusy(true);
    setError(null);
    try {
      await (kind === "approve"
        ? api.approve(invoice.invoice_id, reviewer, note || undefined)
        : api.reject(invoice.invoice_id, reviewer, note || undefined));
      await onDecided();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  if (!needsDecision) {
    return (
      <div className="decision card">
        <h2>Decision</h2>
        {humanEvent ? (
          <p className="small">
            {human(humanEvent.output_summary)}
            {humanEvent.input_summary ? ` · ${humanEvent.input_summary}` : ""}
          </p>
        ) : (
          <p className="muted small">
            {invoice.status === "COMPLETED"
              ? "No decision needed: paid automatically after policy and governance checks passed."
              : "No human decision is required at this stage."}
          </p>
        )}
      </div>
    );
  }

  return (
    <div className="decision card">
      <h2>Your decision</h2>
      <div className="decision-amount">{amount}</div>
      <p className="muted small">{invoice.vendor_name || "Unknown vendor"}</p>
      <label className="field">
        <span>Reviewer</span>
        <input type="email" value={reviewer} onChange={(e) => setReviewer(e.target.value)} placeholder="Reviewer email" />
      </label>
      <label className="field">
        <span>Note (optional)</span>
        <textarea rows={3} value={note} onChange={(e) => setNote(e.target.value)} placeholder="Why you are approving or rejecting" />
      </label>
      <div className="decision-actions">
        <button className="reject-soft" disabled={busy || !reviewer} onClick={() => decide("reject")}>
          <XIcon /> Reject
        </button>
        <button className="primary" disabled={busy || !reviewer} onClick={() => decide("approve")}>
          {!busy && <CheckIcon />}
          {busy ? "Saving…" : `Approve ${amount}`}
        </button>
      </div>
      {error && <div className="alert danger small">{error}</div>}
    </div>
  );
}
