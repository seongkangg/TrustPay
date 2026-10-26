import { fmtTime, human, readable } from "../api/client.js";
import { AuthBadge } from "./StatusBadge.jsx";
import ReasonTag from "./ReasonTag.jsx";

// Immutable, hash-chained event list (GET /invoices/{id}/audit).
export default function AuditLog({ trail }) {
  if (!trail) return <p className="muted">Loading…</p>;
  const { events, chain_valid } = trail;
  return (
    <>
      <div className={`alert ${chain_valid ? "ok" : "danger"}`}>
        {chain_valid
          ? `Integrity verified: ${events.length} events, every hash links to the previous event.`
          : "Integrity check FAILED: the hash chain does not verify."}
      </div>
      <table>
        <thead>
          <tr>
            <th>#</th>
            <th>Time</th>
            <th>Actor</th>
            <th>Action</th>
            <th>Severity</th>
            <th>Policy result</th>
            <th>Reason codes</th>
            <th>Evidence</th>
            <th>Integrity</th>
          </tr>
        </thead>
        <tbody>
          {events.map((e) => (
            <tr key={e.event_id} className={e.policy_result === "blocked" ? "blocked" : ""}>
              <td>{e.sequence}</td>
              <td className="small">{fmtTime(e.timestamp)}</td>
              <td>{human(e.actor)}</td>
              <td>
                <strong>{human(e.event_type)}</strong>
                {e.output_summary && <div className="small muted">{readable(e.output_summary)}</div>}
              </td>
              <td>{human(e.severity)}</td>
              <td>
                <AuthBadge value={e.policy_result} />
              </td>
              <td>
                {e.reason_codes?.map((c) => (
                  <div key={c}>
                    <ReasonTag code={c} />
                  </div>
                ))}
              </td>
              <td>
                {e.evidence_refs?.map((r) => (
                  <div key={r}>
                    <code>{r}</code>
                  </div>
                ))}
              </td>
              <td className="small">
                <code title={e.event_hash}>{e.event_hash.slice(0, 10)}…</code>
                {e.out_of_order && <div className="badge auth-escalated">out of order</div>}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </>
  );
}
