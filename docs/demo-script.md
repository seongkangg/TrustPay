# Demo Script

**Length:** ~6 minutes. **Audience:** judges / finance reviewers.
**Thesis:** *AI may recommend; deterministic governance decides.*

## Before you start

```bash
docker compose up --build        # or: npm run dev  (backend :8000, frontend :5173)
```

Open <http://localhost:5173>. If the Overview shows invoices from a previous run:

```bash
npm run reset                    # POST /demo/reset — wipes invoice state, keeps reference data
```

Keep <http://localhost:8000/docs> in a second tab for the "look, it's a real API" moment.
Record a backup video of this script before the session.

---

## 0. Frame it (30 s) — Overview page

> "Four AI agents process invoices: intake, verification, policy/risk, approval. None of them
> can touch an enterprise system directly — every tool call goes through a governance layer that
> checks an allowlist, masks sensitive data, applies deterministic policy, and writes a
> hash-chained audit trail. The model never decides whether money moves."

Point at the empty tiles: *Total 0 · Blocked actions 0 · Pending approvals 0.*

## 1. Low-risk invoice — automatic processing (1 min)

Click **1 - Low-risk invoice → Submit & process**.

On the detail page:
- Badges: **COMPLETED · low risk**.
- Recommendation panel: *Approve, 94% — advisory only, governance decides*; "Why" lists POLICY-001 / POLICY-002.
- Human decision: *Processed automatically — policy permitted and governance authorized payment.*
- Scroll the **Agent timeline**: every tool call has an evidence ID (`PARSE-001`, `VENDOR-LOOKUP-001`…). The payment call is made by **governance layer**, not by any agent.

> "Verified vendor, matching PO, under the $10k threshold. Policy says low risk, the agent
> recommends approve, governance executes the simulated payment. Every step is evidenced."

## 2. Policy violation — blocked, human approves (1.5 min)

Back to **Overview**. Tiles: *1 total, 1 low.* Click **2 - Policy violation → Submit & process**.

- Badges: **PENDING APPROVAL · high risk**.
- "Why": *amount 25000.0 > approval_agent limit 10000.0* — rule **POLICY-003**.
- Human decision panel: *Payment is withheld… needs a human decision.*

> "Same verified vendor, matching PO — but $25k exceeds the agent's authority. The agent can only
> recommend *escalate*. Nothing it says can unlock payment."

Enter a reviewer email, click **Approve payment**.

- Status flips to **COMPLETED**; the panel shows *human decision: approved — reviewer … on APR-001*.
- The AI recommendation **still says Escalate** next to it — the two are never merged.
- Timeline ends: `human decision recorded → payment authorized (actor: human reviewer) → audit record created`.

## 3. Suspicious invoice — masked, blocked, escalated (1.5 min)

Overview → **3 - Suspicious / sensitive invoice → Submit & process**.

- Badges: **BLOCKED · high risk**. Two banners: *Sensitive data detected and masked* and *Payment blocked*.
- Invoice card: Bank account `****6789`, Routing `****0021`, Tax ID `****4321`.
- "Why": four rules — POLICY-003 (amount), **POLICY-004 unknown vendor**, **POLICY-007 PO not found**, POLICY-009 sensitive data.
- Timeline: the very first governance event is `sensitive data masked` with evidence `SCAN-…` — before any agent ran.

> "This is the spec's worked example: $25k, new vendor, banking details in the document.
> The raw account number never reached a model, a log line, or this screen — the masking
> happens at ingestion. Vendor lookup returned *not found*, the PO doesn't exist, and the
> platform blocked payment and escalated."

Click **Reject** with a note → status **REJECTED**, decision recorded.

## 4. Duplicate — the quiet one (30 s)

Overview → **3b - Duplicate invoice → Submit & process**.

- **BLOCKED · high risk**, recommendation **Reject**, rule POLICY-006, evidence `DUP-CHECK-…`.

> "Same vendor, same invoice number as scenario 1, which was already paid. Caught before any
> money moved a second time."

## 5. The audit trail (45 s)

On any invoice click **Audit view**.

- *Integrity verified: N events, every hash links to the previous event.*
- Columns: actor, action, severity, policy result, reason codes, evidence, hash.
- Blocked rows are red.

> "Append-only. Each event carries the SHA-256 of the previous one. Duplicates are ignored,
> out-of-order arrivals are flagged rather than reordered, and a tampered record breaks the chain."

## 6. Prove the guardrail (30 s) — Swagger tab

`POST /governance/evaluate-tool-call` with:

```json
{ "agent": "approval_agent", "tool": "payment_authorize", "purpose": "pay the invoice now",
  "parameters": {}, "invoice_id": "INV-1002", "correlation_id": "demo" }
```

Response: `"authorization": "blocked"`, `"denial_reason": "UNAUTHORIZED_TOOL_CALL"`, rule **POLICY-014**.
Refresh that invoice's audit view: a `tool call denied` event was appended — even a dry run is logged.

> "No agent can ever call the payment tool. Not with a clever prompt, not with high confidence."

## Close (15 s)

Overview tiles now read: *4 total · 1 low · 3 high · blocked actions · pending approvals*.

> "Simulated enterprise systems, real governance. Swap `LLM_MODE=mock` for watsonx.ai and the
> agents use Granite — the governance layer doesn't change, because it never trusted the model
> in the first place."

---

## If something goes wrong

| Symptom | Do |
|---------|----|
| Overview shows old invoices | `npm run reset`, reload |
| "backend: unreachable" in the top bar | `docker compose ps` / restart backend; the page recovers on reload |
| A scenario button errors with 409 | that invoice already exists — reset |
| Need to show a failure path live | `MOCK_FAILURES=vendor` in `.env`, restart backend, run scenario 1 → `PENDING APPROVAL` with `MOCK_SYSTEM_UNAVAILABLE` |
| Anything else | play the backup video |
