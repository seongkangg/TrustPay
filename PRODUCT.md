# Product

<!-- impeccable:product-schema 1 -->

## Platform

mobile phone

## Users

Primary: an entity or finance approver who opens the dashboard a few times a day to clear invoices waiting
for a human decision (PENDING_APPROVAL / BLOCKED), then checks totals. The same screens are also
shown live in demos.

## Product Purpose

TrustPay is a governance layer for AI agents that process invoices. Four agents (Intake →
Verification → Policy/Risk → Approval) recommend; deterministic governance decides, masks sensitive
data, logs every tool call, and stops high-risk payments for a human. The dashboard shows what came
in, what was paid, what was withheld, and what needs the approver now.

## Positioning

AI recommends; deterministic governance decides. Every decision cites evidence, and every blocked
action is visible and auditable.

## Capabilities and Constraints

- React + Vite, plain CSS in `frontend/src/styles/dashboard.css`, no UI framework; recharts is the
  only chart dependency.
- Data comes from `GET /dashboard/summary`, `GET /invoices`, and `GET /inbox/status`. The summary's
  daily history is the last 14 days of counts (received / completed / blocked), not amounts.
- Sensitive fields (`bank_account`, `routing_number`, `tax_id`) never appear raw in the UI.
- Out of scope: real payments, real banking/ERP integrations, production auth.

## Brand Commitments

- The overview follows a user-supplied reference: soft grey canvas, one large white rounded app
  window, centred pill icon nav, hero figure with a delta pill, a large smooth line chart, KPI
  cards with sparklines, a bar block with one highlighted bar, and a calendar grid. The user chose
  to keep the sparklines and pill nav from the reference.
- The TrustPay logo (`frontend/public/trustpay-logo.svg`: teal-to-navy shield with a tick, "Trust"
  in navy #0F3D5E and "Pay" in teal #14B8A6) is used as-is in both apps, and its teal and navy set
  the UI colours. It replaced the reference's indigo.

## Evidence on Hand

Demo fixtures in `data/invoices/*.json`. Customers business statistics exist for purposes of prototyping.

## Product Principles

1. The approver's next decision is one click from the first screen.
2. Every figure on screen comes from the backend; nothing is typed in or invented.
3. Blocked and withheld money is loud; healthy states are quiet.
