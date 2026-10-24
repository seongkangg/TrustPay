import { fmtMoney } from "../api/client.js";
import ApprovalQueue from "../components/ApprovalQueue.jsx";
import { CheckIcon } from "../components/Icons.jsx";
import InboxCard from "../components/InboxCard.jsx";
import PageHeader from "../components/PageHeader.jsx";
import { useDashboard } from "../data.jsx";

// Inbox, as on the phone: what is waiting on you (count and money on hold, then the invoices behind
// the count on this nav item), beside the email intake that feeds invoices in.
export default function Inbox() {
  const { summary, inbox, awaiting, error, load } = useDashboard();
  const reasonCodes = Object.fromEntries(
    (summary?.recent_violations || []).map((v) => [v.invoice_id, v.reason_codes]),
  );
  const onHold = awaiting.reduce((sum, inv) => sum + (inv.amount || 0), 0);
  const blocked = awaiting.filter((inv) => inv.status === "BLOCKED").length;

  return (
    <>
      <PageHeader title="Inbox">Invoices waiting on your decision, and the email intake that feeds them in.</PageHeader>
      {error && <div className="alert danger">{error}</div>}
      <div className="split-page">
        <section aria-labelledby="approvals-h">
          <h2 id="approvals-h">Needs your approval</h2>
          {awaiting.length === 0 ? (
            <div className="panel all-clear">
              <span className="all-clear-icon" aria-hidden="true">
                <CheckIcon size={22} />
              </span>
              <span>
                <strong>All caught up</strong>
                <span className="muted small">
                  {summary ? "Nothing needs your approval. New invoices are checked automatically." : "Loading…"}
                </span>
              </span>
            </div>
          ) : (
            <>
              <div className="panel waiting-summary">
                <span className="waiting-count">{awaiting.length}</span>
                <span>
                  <strong>
                    invoice{awaiting.length === 1 ? "" : "s"} waiting for you
                  </strong>
                  <span className="muted small">
                    {fmtMoney(onHold)} on hold{blocked ? ` · ${blocked} blocked` : ""}
                  </span>
                </span>
              </div>
              <ApprovalQueue items={awaiting} reasonCodes={reasonCodes} />
            </>
          )}
        </section>
        <section aria-labelledby="email-h">
          <h2 id="email-h">Email inbox</h2>
          <InboxCard status={inbox.status} unavailable={inbox.unavailable} onSynced={load} />
        </section>
      </div>
    </>
  );
}
