import { fmtPct, fmtTime, human, readable } from "../api/client.js";
import { AuthBadge } from "./StatusBadge.jsx";
import ReasonTag from "./ReasonTag.jsx";

const BLOCKING_EVENTS = new Set(["payment_blocked", "tool_call_denied", "agent_failed"]);

function Evidence({ ids }) {
  if (!ids || ids.length === 0) return null;
  return (
    <div className="evidence small muted">
      Evidence:{" "}
      {ids.map((id) => (
        <code key={id}>{id}</code>
      ))}
    </div>
  );
}

function EventItem({ data }) {
  const blocked = BLOCKING_EVENTS.has(data.event_type) || data.policy_result === "blocked";
  return (
    <li className={blocked ? "blocked" : ""}>
      <div className="title">{human(data.event_type)}</div>
      <div className="meta">
        {human(data.actor)} · {fmtTime(data.timestamp)} · {human(data.severity)} severity
        {data.policy_result && (
          <>
            {" "}
            · <AuthBadge value={data.policy_result} />
          </>
        )}
      </div>
      {data.reason_codes?.length > 0 && (
        <div className="small">
          {data.reason_codes.map((c) => (
            <ReasonTag key={c} code={c} />
          ))}
        </div>
      )}
      {data.output_summary && <div className="small">{readable(data.output_summary)}</div>}
      <Evidence ids={data.evidence_refs} />
    </li>
  );
}

function ToolCallItem({ data }) {
  const blocked = data.authorization !== "allowed";
  return (
    <li className={blocked ? "blocked" : ""}>
      <div className="title">
        {human(data.agent)} → {human(data.tool)} <AuthBadge value={data.authorization} />
      </div>
      <div className="meta">
        {fmtTime(data.timestamp)} · {readable(data.purpose)}
        {data.denial_reason && (
          <>
            {" "}
            · <ReasonTag code={data.denial_reason} />
          </>
        )}
      </div>
      {data.result_summary && <div className="small muted">{readable(data.result_summary)}</div>}
      <Evidence ids={data.evidence_id ? [data.evidence_id] : []} />
    </li>
  );
}

function DecisionItem({ data }) {
  const blocked = data.governance_result === "blocked";
  const why = data.explanation || {};
  return (
    <li className={`decision ${blocked ? "blocked" : ""}`}>
      <div className="title">
        {human(data.agent)}: {human(data.decision)} <AuthBadge value={data.governance_result} />
      </div>
      <div className="meta">
        {fmtTime(data.timestamp)} · confidence {fmtPct(data.confidence)}
        {data.risk_level && <> · {human(data.risk_level)} risk</>}
        {data.recommendation && <> · Recommends {human(data.recommendation).toLowerCase()}</>}
      </div>
      {why.reasons?.length > 0 && (
        <ul className="why small">
          {why.reasons.map((r, i) => (
            <li key={i}>{readable(r)}</li>
          ))}
        </ul>
      )}
      {why.policy_rules_triggered?.length > 0 && (
        <div className="small muted">
          Rules:{" "}
          {why.policy_rules_triggered.map((r) => (
            <code key={r}>{r}</code>
          ))}
        </div>
      )}
      <Evidence ids={data.evidence_ids} />
    </li>
  );
}

// Chronological merge of audit events, tool calls, and agent decisions (GET /invoices/{id}/timeline).
export default function AgentTimeline({ entries }) {
  if (!entries || entries.length === 0) return <p className="muted">No activity yet.</p>;
  return (
    <ul className="timeline">
      {entries.map((e, i) => {
        if (e.kind === "decision") return <DecisionItem key={i} data={e.data} />;
        if (e.kind === "tool_call") return <ToolCallItem key={i} data={e.data} />;
        return <EventItem key={i} data={e.data} />;
      })}
    </ul>
  );
}
