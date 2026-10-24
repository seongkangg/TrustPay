---
version: 1
slug: "frontend-src-pages-dashboard-jsx"
primary_target: "frontend/src/pages/Dashboard.jsx"
related_targets: ["frontend/src/App.jsx"]
---

# Overview (frontend/src/pages/Dashboard.jsx)

Mode: Operate. Code-led. Direction pinned by the user's reference image (no roll).

Audience: finance approver, a few visits a day. Task: clear invoices awaiting a human, then read totals.

## Direction contract

THESIS: The overview is one calm white window on a grey desk: money first, then its shape over time, then what needs a human. Refuses the stacked-tiles-and-tables admin page.

OWN-WORLD: Canvas #e9eaee; window white, 28px radius, soft offset shadow; inner panels are a one-step grey (#f5f5f7) with no border, 18px radius. Ink near-black, muted grey labels. One indigo (#5b5bf0) on data and the active nav pill; green/red only on money polarity and risk.

STORY: The approver sees total volume and how much was paid vs withheld, sees anything waiting on them with a Review link, then scans the 14-day calendar, risk mix, inbox and invoice list.

FIRST VIEWPORT: Top bar with mark left, centred pill icon nav, backend status right. Awaiting-approval strip if any. Hero: "Invoice volume" label, total at ~44px with a green "% paid" pill, paid/withheld beneath; "Last 14 days" right. Full-width smooth indigo line chart ~240px. Three KPI cards with sparklines. Bottom row: risk bars (high highlighted) and 14-day calendar grid.

FORM: Reference dashboard, pinned by user. seed: none (unavailable)

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance
