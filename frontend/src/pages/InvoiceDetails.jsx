import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { api, fmtMoney, fmtPct, fmtTime } from "../api/client.js";
import AgentTimeline from "../components/AgentTimeline.jsx";
import ApprovalPanel from "../components/ApprovalPanel.jsx";
import RiskBadge from "../components/RiskBadge.jsx";
import StatusBadge from "../components/StatusBadge.jsx";
import ToolCallTable from "../components/ToolCallTable.jsx";

export default function InvoiceDetails() {
  const { id } = useParams();
  const [invoice, setInvoice] = useState(null);
  const [timeline, setTimeline] = useState([]);
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

  if (error && !invoice) return <div className="alert danger">{error}</div>;
  if (!invoice) return <p className="muted">Loading…</p>;

  const decisions = timeline.filter((e) => e.kind === "decision").map((e) => e.data);
  const toolCalls = timeline.filter((e) => e.kind === "tool_call").map((e) => e.data);
  const events = timeline.filter((e) => e.kind === "event").map((e) => e.data);
  const blockedCalls = toolCalls.filter((c) => c.authorization !== "allowed").length;

  return (
    <>
      <p className="small">
        <Link to="/">← Overview</Link> · <Link to={`/invoices/${id}/audit`}>Audit view</Link>
      </p>
      <h1 style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap" }}>
        {invoice.invoice_id}
        <StatusBadge status={invoice.status} />
        <RiskBadge level={invoice.risk_level} />
      </h1>
      {error && <div className="alert danger">{error}</div>}

      {invoice.sensitive_data_detected && (
        <div className="alert warn">
          <strong>Sensitive data detected and masked.</strong> Banking / tax identifiers on this invoice are
          shown as last-four only and were never passed to a model or written to a log.
        </div>
      )}
      {["BLOCKED", "FAILED"].includes(invoice.status) && (
        <div className="alert danger">
          <strong>Payment blocked.</strong> Governance stopped automatic processing for this invoice.
        </div>
      )}
      {blockedCalls > 0 && (
        <div className="alert danger small">
          {blockedCalls} unauthorized tool call{blockedCalls > 1 ? "s were" : " was"} blocked and recorded.
        </div>
      )}

      <div className="row">
        <div className="card grow">
          <h2 style={{ marginTop: 0 }}>Invoice</h2>
          <dl className="kv">
            <dt>Vendor</dt>
            <dd>
              {invoice.vendor_name || "—"} {invoice.vendor_id && <code>{invoice.vendor_id}</code>}
            </dd>
            <dt>Vendor invoice #</dt>
            <dd>{invoice.vendor_invoice_number}</dd>
            <dt>Amount</dt>
            <dd>{fmtMoney(invoice.amount, invoice.currency)}</dd>
            <dt>Due date</dt>
            <dd>{invoice.due_date || "—"}</dd>
            <dt>Purchase order</dt>
            <dd>{invoice.purchase_order_id ? <code>{invoice.purchase_order_id}</code> : "—"}</dd>
            <dt>Bank account</dt>
            <dd>{invoice.bank_account || "—"}</dd>
            <dt>Routing number</dt>
            <dd>{invoice.routing_number || "—"}</dd>
            <dt>Tax ID</dt>
            <dd>{invoice.tax_id || "—"}</dd>
            <dt>Source</dt>
            <dd>{invoice.source_document || "structured upload"}</dd>
            <dt>Received</dt>
            <dd>{fmtTime(invoice.created_at)}</dd>
          </dl>
        </div>

        <div className="card grow">
          <h2 style={{ marginTop: 0 }}>Extraction</h2>
          {invoice.extraction?.length ? (
            <table>
              <thead>
                <tr>
                  <th>Field</th>
                  <th>Value</th>
                  <th>Confidence</th>
                </tr>
              </thead>
              <tbody>
                {invoice.extraction.map((f) => (
                  <tr key={f.field}>
                    <td>{f.field}</td>
                    <td>{f.missing ? <span className="muted">missing</span> : f.value}</td>
                    <td>
                      {fmtPct(f.confidence)}
                      {f.malformed && <span className="badge risk-medium"> malformed</span>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <p className="muted">Not extracted yet.</p>
          )}
        </div>
      </div>

      <h2>Recommendation &amp; approval</h2>
      <ApprovalPanel invoice={invoice} decisions={decisions} events={events} onDecided={load} />

      <h2>Agent timeline</h2>
      <div className="card">
        <AgentTimeline entries={timeline} />
      </div>

      <h2>Tool calls</h2>
      <ToolCallTable calls={toolCalls} />
    </>
  );
}
