---
name: TrustPay
description: Governance dashboard for AI invoice processing; one calm white window on a grey desk, money first.
colors:
  canvas: "#e9eaee"
  surface: "#ffffff"
  panel: "#f5f5f7"
  panel-2: "#ebebef"
  text: "#15161a"
  muted: "#6b6f7b"
  neutral-ink: "#565a65"
  border: "#ececf0"
  neutral-bg: "#f0f0f3"
  accent: "#5b5bf0"
  accent-ink: "#4040d6"
  accent-soft: "#c9c9fb"
  accent-bg: "#ececfe"
  ok: "#18794e"
  ok-bg: "#e3f5ea"
  blocked: "#d92d3a"
  blocked-bg: "#fde7e8"
  risk-low: "#18794e"
  risk-low-bg: "#e3f5ea"
  risk-medium: "#8f6100"
  risk-medium-bg: "#fdf1d6"
  risk-high: "#c4202d"
  risk-high-bg: "#fde7e8"
typography:
  display:
    fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI Variable Text', 'Segoe UI', Roboto, Helvetica, Arial, sans-serif"
    fontSize: "44px"
    fontWeight: 700
    lineHeight: 1.1
    letterSpacing: "-0.035em"
    fontFeature: "tnum"
  headline:
    fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI Variable Text', 'Segoe UI', Roboto, Helvetica, Arial, sans-serif"
    fontSize: "28px"
    fontWeight: 700
    lineHeight: 1.15
    letterSpacing: "-0.03em"
    fontFeature: "tnum"
  title:
    fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI Variable Text', 'Segoe UI', Roboto, Helvetica, Arial, sans-serif"
    fontSize: "16px"
    fontWeight: 700
    lineHeight: 1.5
    letterSpacing: "-0.01em"
  body:
    fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI Variable Text', 'Segoe UI', Roboto, Helvetica, Arial, sans-serif"
    fontSize: "14px"
    fontWeight: 400
    lineHeight: 1.5
    fontFeature: "tnum"
  label:
    fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI Variable Text', 'Segoe UI', Roboto, Helvetica, Arial, sans-serif"
    fontSize: "13px"
    fontWeight: 550
    lineHeight: 1.5
  caption:
    fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI Variable Text', 'Segoe UI', Roboto, Helvetica, Arial, sans-serif"
    fontSize: "12px"
    fontWeight: 600
    lineHeight: 1.5
  mono:
    fontFamily: "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace"
    fontSize: "12px"
    fontWeight: 400
    lineHeight: 1.4
rounded:
  code: "6px"
  field: "12px"
  alert: "14px"
  row: "16px"
  panel: "18px"
  window: "28px"
  control: "999px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "12px"
  lg: "16px"
  xl: "20px"
  gutter: "28px"
  section: "36px"
components:
  window:
    backgroundColor: "{colors.surface}"
    rounded: "{rounded.window}"
    width: "1240px"
  panel:
    backgroundColor: "{colors.panel}"
    textColor: "{colors.text}"
    rounded: "{rounded.panel}"
    padding: "18px 20px"
  button-primary:
    backgroundColor: "{colors.text}"
    textColor: "{colors.surface}"
    typography: "{typography.body}"
    rounded: "{rounded.control}"
    padding: "0 16px"
    height: "36px"
  button-primary-hover:
    backgroundColor: "#2c2e36"
  button-secondary:
    backgroundColor: "{colors.panel-2}"
    textColor: "{colors.text}"
    rounded: "{rounded.control}"
    padding: "0 16px"
    height: "36px"
  button-secondary-hover:
    backgroundColor: "#e2e2e8"
  button-approve:
    backgroundColor: "{colors.ok}"
    textColor: "{colors.surface}"
    rounded: "{rounded.control}"
    padding: "0 16px"
    height: "36px"
  button-reject:
    backgroundColor: "{colors.blocked}"
    textColor: "{colors.surface}"
    rounded: "{rounded.control}"
    padding: "0 16px"
    height: "36px"
  button-disabled:
    backgroundColor: "{colors.panel-2}"
    textColor: "{colors.neutral-ink}"
  nav-pill-track:
    backgroundColor: "{colors.panel}"
    rounded: "{rounded.control}"
    padding: "4px"
  nav-pill:
    textColor: "{colors.muted}"
    typography: "{typography.label}"
    rounded: "{rounded.control}"
    padding: "0 11px"
    height: "34px"
  nav-pill-active:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.text}"
  badge-neutral:
    backgroundColor: "{colors.neutral-bg}"
    textColor: "{colors.neutral-ink}"
    typography: "{typography.caption}"
    rounded: "{rounded.control}"
    padding: "0 9px"
    height: "22px"
  badge-risk-low:
    backgroundColor: "{colors.risk-low-bg}"
    textColor: "{colors.risk-low}"
  badge-risk-medium:
    backgroundColor: "{colors.risk-medium-bg}"
    textColor: "{colors.risk-medium}"
  badge-risk-high:
    backgroundColor: "{colors.risk-high-bg}"
    textColor: "{colors.risk-high}"
  badge-status-ok:
    backgroundColor: "{colors.ok-bg}"
    textColor: "{colors.ok}"
  badge-status-pending:
    backgroundColor: "{colors.accent-bg}"
    textColor: "{colors.accent-ink}"
  badge-status-blocked:
    backgroundColor: "{colors.blocked}"
    textColor: "{colors.surface}"
  count-pill:
    backgroundColor: "{colors.accent}"
    textColor: "{colors.surface}"
    rounded: "{rounded.control}"
    padding: "0 7px"
    height: "22px"
  count-pill-quiet:
    backgroundColor: "{colors.panel-2}"
    textColor: "{colors.muted}"
  queue-row:
    backgroundColor: "{colors.accent-bg}"
    rounded: "{rounded.row}"
    padding: "12px 12px 12px 18px"
  queue-row-blocked:
    backgroundColor: "{colors.blocked-bg}"
  input:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.text}"
    rounded: "{rounded.field}"
    padding: "9px 12px"
---

# Design System: TrustPay

## Overview

**Creative North Star: "The Window on the Desk"**

TrustPay is one calm white window resting on a grey desk. Inside it, money comes first, then its shape over time, then whatever needs a human. The page refuses the stacked-tiles-and-tables admin look it replaced: there are no bordered cards and no header bars, only a floating white window and one-step grey panels set into it, separated by space rather than lines.

The direction is pinned by a reference image the user supplied, and its distinctive devices are kept on purpose: a single indigo on data and on the active nav pill, sparklines on the KPI cards, a raised white active pill in a centred icon nav, the soft-shadowed window on the grey canvas, and a large hero figure in whole dollars. Density is moderate. An approver who visits a few times a day should be able to read the totals at a glance and reach the next decision in one click.

Colour carries meaning, not decoration. Indigo means "data" or "here". Green and red mean money polarity, risk or status, nothing else. Amber means medium risk only. Healthy states stay quiet; blocked and withheld money is loud.

**Key Characteristics:**
- Floating white window (28px corners) on a cool grey canvas; borderless grey panels (18px) inside.
- One indigo accent on data, the chart, sparklines, the highlighted risk bar, today's calendar cell and the active nav state.
- Pill-shaped controls everywhere: nav, buttons, badges, count pills, deltas.
- Tabular numerals throughout; the hero figure is 44px whole dollars.
- Sentence-case badges; missing values print as an em dash (—).
- Motion is brief and physical: a 0.97 press, bars that rise once, a chart that draws in once.

## Colors

A cool, near-neutral grey world with one saturated indigo and a strictly semantic green/red/amber set.

### Primary
- **Signal Indigo** (accent): the only decorative-strength colour. Used for the volume area chart line and its fade, KPI sparklines, the high-risk bar in the risk mix, today's calendar cell, count pills with work waiting, the brand mark tile, focus outlines and `accent-color`. The pending status reuses it (the CSS `--pending` token is an alias of the accent).
- **Deep Indigo Ink** (accent-ink): indigo as text, for links and pending badges where the base indigo is too light to read on a tint.
- **Pale Indigo Line** (accent-soft): the quiet "completed" line in the volume chart, its hover cursor and legend key.
- **Indigo Wash** (accent-bg): tint behind pending badges, info alerts, approval-queue rows, text selection and the input focus ring.

### Semantic
- **Settled Green** (ok, and risk-low at the same value) with **Mint Wash** (ok-bg): paid money, completed/approved status, allowed authorisations, the approve button, low risk.
- **Withheld Red** (blocked) with **Blush Wash** (blocked-bg): withheld money, blocked/failed/rejected status (solid fill, white text), the reject button, blocked queue rows and table rows, the danger sparkline.
- **Risk Red** (risk-high) with its wash (risk-high-bg): high-risk badges only.
- **Ochre** (risk-medium) with **Cream Wash** (risk-medium-bg): medium risk, and the warning alert background.

### Neutral
- **Grey Desk** (canvas): the page background behind the window.
- **Paper White** (surface): the window, the active nav pill, inputs, tooltips.
- **Panel Grey** (panel): every inner panel, KPI card, the nav track, skeletons, table-row hover.
- **Deeper Panel Grey** (panel-2): secondary buttons, disabled buttons, quiet count pills, empty risk bars, calendar cells, row rules inside panels.
- **Ink** (text): body text and the primary (black) button.
- **Slate** (muted): labels, captions, table headers, axis ticks.
- **Badge Slate** (neutral-ink): text in neutral badges and disabled buttons.
- **Hairline** (border): table row rules on white.
- **Fog** (neutral-bg): neutral badges, inline code chips, neutral delta pills.

### Named Rules
**The One Indigo Rule.** Indigo is the only accent. It marks data and "you are here"; it never decorates a heading, a border or an empty area.

**The Polarity Rule.** Green and red appear only for money polarity (paid / withheld), risk and status. Amber appears only for medium risk. A state that is neither risky nor a status (Disabled, Masked, "No risk yet", a missing value) takes the neutral badge.

**The Loud Block Rule.** Blocked, failed and rejected are the only solid-filled badges (white on red). Every other badge is a tint with coloured text.

## Typography

**Body Font:** the platform system stack (-apple-system, Segoe UI Variable Text, Segoe UI, Roboto, Helvetica, Arial)
**Label/Mono Font:** ui-monospace stack, for reason codes and IDs only

**Character:** One sans family at every size, tightened and heavier as it grows, with tabular numerals everywhere so figures line up in tables, KPIs and the chart tooltip.

The system stack is a pinned decision for this Operate surface: it matches the native-app feel of the reference and costs nothing to load. A self-hosted display grotesk was proposed at finish review and deferred, not rejected. This choice does not set the face for any future display or brand surface; such a surface should pick its own display face.

### Hierarchy
- **Display** (700, 44px, 1.1, -0.035em; 34px under 760px): the hero total, in whole dollars. One per page.
- **Headline** (700, 28px, 1.15, -0.03em): KPI card values.
- **Title** (700, 16px, -0.01em): section headings. Page h1 is 22px (-0.02em) where visible; panel heads drop to 14px.
- **Body** (400, 14px, 1.5): everything else, including table cells.
- **Label** (550, 13px): KPI and hero labels, nav items, range chip, in muted grey. Sentence case, no tracking, never uppercase.
- **Caption** (600, 12px): badges, deltas, count pills, table headers (550), timestamps (400, muted).
- **Mono** (400, 12px, 1.4): reason codes and IDs in a Fog chip with 6px corners.

### Named Rules
**The Tabular Rule.** Every number uses tabular figures. Amounts align right in tables.

**The Em Dash Rule.** A missing value prints as an em dash (—), never "N/A", "null", "0" or an empty cell.

**The UTC Day Rule.** Days in the 14-day history are UTC calendar days and any range that names them carries "(UTC)".

## Layout

A single centred window, max 1240px wide, 24px from the top of the canvas and 40px from the bottom. Inside, the top bar is a three-column grid (brand left, pill nav centred, backend status right) with 18px/28px padding; the page has a 28px side gutter. Sections are separated by 36px of space, not rules.

The overview reads top to bottom: the approval queue (only when something waits), the hero (label, figure with paid-share pill, paid/withheld split, "Last 14 days" chip and legend to the right), a full-width 240px volume chart, a row of three equal KPI cards (12px gap), then a lower row of risk bars and the day calendar (1fr / 1.2fr), then inbox, violations and the invoice table. Gaps inside grids are 12px; queue rows stack with 8px.

Responsive behaviour:
- **Under 900px:** the lower row stacks; queue rows reflow to two columns with reasons and amount on their own lines.
- **Under 760px:** the window goes full-bleed (no margin, no corners, no shadow); gutter drops to 16px; status text hides; the hero figure drops to 34px and the chart to 180px; KPIs stack; low-priority table columns hide; key/value lists and the approval panel go to one column.

## Elevation & Depth

Depth is mostly tonal: grey canvas, white window, grey panels one step darker than white. Shadows are reserved for the three things that float above their surroundings, and each is soft and low-contrast, never a hard offset.

### Shadow Vocabulary
- **Window float** (`box-shadow: 0 1px 2px rgba(20,22,30,0.04), 0 18px 48px -18px rgba(20,22,30,0.12)`): the app window on the canvas. Removed when the window goes full-bleed on small screens.
- **Raised pill** (`box-shadow: 0 1px 2px rgba(20,22,30,0.08), 0 2px 6px -2px rgba(20,22,30,0.08)`): the active nav pill lifting out of its grey track.
- **Tooltip float** (`box-shadow: 0 2px 4px rgba(20,22,30,0.06), 0 10px 24px -6px rgba(20,22,30,0.18)`): chart tooltips.
- **Focus halo** (`box-shadow: 0 0 0 3px` Indigo Wash): text fields on focus, with an indigo border.

### Named Rules
**The Tonal-First Rule.** Panels never carry a shadow or a border. A panel is distinguished from the window by one step of grey alone.

## Shapes

Everything is rounded and soft, and corners shrink as elements nest: window 28px, panel 18px, queue row 16px, alert and risk bar 14px, field, calendar cell and tooltip 12px, code chip 6px. Every interactive control (buttons, nav pills, badges, count pills, delta pills, range chip) is a full pill (999px). Dots (status, legend keys, timeline nodes) are circles. Hairlines appear only as row rules in tables and lists.

## Components

### Buttons
Soft, pill-shaped and tactile.
- **Shape:** full pill (999px), 36px tall, 16px side padding, 600 weight.
- **Primary:** Ink fill, white text; hover lifts to #2c2e36. Used for "Review" in the queue.
- **Secondary (default):** Deeper Panel Grey fill, Ink text; hover #e2e2e8.
- **Approve / Reject:** Settled Green and Withheld Red fills with white text, only on the human-decision panel.
- **Disabled:** Deeper Panel Grey with Badge Slate text, not-allowed cursor.
- **Press:** `scale(0.97)` over 160ms on `cubic-bezier(0.23, 1, 0.32, 1)`; colour changes take 150ms ease. Hover styles apply only on fine pointers.

### Chips (badges, count pills, deltas)
- **Badge:** 22px pill, 9px padding, 12px/600, sentence case. Tint background with coloured text per the Polarity Rule; solid red with white text for blocked/failed/rejected; neutral Fog with Badge Slate for non-risk states.
- **Count pill:** 22px circle-to-pill beside a heading; indigo with white text when work waits, quiet grey when zero.
- **Delta pill:** 22px, Mint Wash with green text for an upward or healthy change (the hero's "% paid", a KPI's up-arrow count for today); Fog with muted text otherwise.

### Cards / Containers
- **Corner Style:** 18px.
- **Background:** Panel Grey on the white window.
- **Shadow Strategy:** none (see the Tonal-First Rule).
- **Border:** none.
- **Internal Padding:** 18px vertical, 20px horizontal.

### Inputs / Fields
- **Style:** white fill, 1px #dcdde3 stroke, 12px corners, 9px/12px padding.
- **Focus:** border turns indigo and a 3px Indigo Wash halo appears; no outline.

### Navigation
A centred track of icon pills on Panel Grey (4px inset). Each item is a 34px pill with an 18px outline icon (24px grid, 1.75 stroke) in muted grey; hover darkens to Ink. The active item becomes a white raised pill and reveals its text label beside the icon; inactive items are icon-only with an accessible name. On small screens the nav sits to the right of the brand.

### Hero figure and volume chart
The total in Display type, followed by a paid-share delta pill, then a muted split line with green and red key dots for Paid and Withheld. Below, a full-width smooth area chart: received in Signal Indigo (2.5px) over a 16%-to-0 indigo fade, completed as a Pale Indigo line (2px), muted 11px axis ticks, no grid and no y-axis. It draws in once over 700ms ease-out.

### KPI card with sparkline
A panel with a muted label (and optional delta pill) on top, a Headline value, and a 32px smooth sparkline in indigo (2px, round caps). The Blocked card's sparkline turns red when anything is blocked.

### Risk bars
Three rounded blocks (14px) on a 150px track: low and medium in Deeper Panel Grey, high in Signal Indigo because it needs eyes. Count and amount sit centred below. Bars rise once from 60% scale over 600ms on the ease-out curve.

### Day calendar
A 7-column grid of 64px grey cells (12px corners) for the last 14 UTC days: date top-left, received count centred, "n blocked" or "n done" beneath. Zero days dim their count; today is a solid indigo cell with white text.

### Approval queue row
A 16px-cornered Indigo Wash row (Blush Wash when blocked): vendor and ID/time, then status, risk and reason-code chips, then the amount (16px/700), then a primary "Review" pill.

## Do's and Don'ts

### Do:
- **Do** keep indigo (#5b5bf0) to data, the active nav pill, today's cell, the high-risk bar and waiting-count pills.
- **Do** use green and red only for paid/withheld money, risk and status, and amber only for medium risk.
- **Do** give non-risk states (Disabled, Masked, "No risk yet") the neutral badge, in sentence case.
- **Do** print missing values as an em dash (—) and label UTC day ranges "(UTC)".
- **Do** set every number in tabular figures and show the hero total in whole dollars.
- **Do** separate sections with space (36px) and panels with one step of grey, not lines.
- **Do** use `scale(0.97)` at 160ms on `cubic-bezier(0.23, 1, 0.32, 1)` for button presses, and disable the risk-bar rise and the chart draw-in under `prefers-reduced-motion`.

### Don't:
- **Don't** add borders or shadows to inner panels; only the window, the active nav pill and tooltips float.
- **Don't** introduce a second accent hue, or use indigo for decoration.
- **Don't** use green, red or amber for anything that is not money polarity, risk or status.
- **Don't** fill a badge solid unless it is blocked, failed or rejected.
- **Don't** uppercase or track out labels and badges.
- **Don't** show a raw `bank_account`, `routing_number` or `tax_id` anywhere in the UI.
