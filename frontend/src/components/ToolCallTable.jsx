import { fmtTime, human } from "../api/client.js";
import { AuthBadge } from "./StatusBadge.jsx";
import ReasonTag from "./ReasonTag.jsx";

// Every tool call made for an invoice — allowed or blocked — with its evidence ID.
export default function ToolCallTable({ calls }) {
  if (!calls || calls.length === 0) return <p className="muted">No tool calls recorded.</p>;
  return (
    <table>
      <thead>
        <tr>
          <th>Time</th>
          <th>Agent</th>
          <th>Tool</th>
          <th>Purpose</th>
          <th>Authorization</th>
          <th>Result</th>
          <th>Evidence</th>
        </tr>
      </thead>
      <tbody>
        {calls.map((c) => (
          <tr key={c.tool_call_id} className={c.authorization !== "allowed" ? "blocked" : ""}>
            <td className="small">{fmtTime(c.timestamp)}</td>
            <td>{human(c.agent)}</td>
            <td>
              {human(c.tool)}
              {c.is_write && <span className="small muted"> (write)</span>}
            </td>
            <td className="small">{c.purpose}</td>
            <td>
              <AuthBadge value={c.authorization} />
              {c.denial_reason && (
                <div className="small">
                  <ReasonTag code={c.denial_reason} />
                </div>
              )}
            </td>
            <td className="small">{c.result_summary || "—"}</td>
            <td>{c.evidence_id ? <code>{c.evidence_id}</code> : "—"}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
