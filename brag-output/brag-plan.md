# TrustPay — brag plan

**What:** A governance layer that lets four AI agents process invoices but never lets them move money on their own.
**For:** Finance approvers who want AI to do invoice grunt work without the AI holding the chequebook.
**Sets it apart:** "AI recommends; deterministic governance decides." Every tool call is logged, sensitive data is masked at ingestion, and anything over $10,000 waits for a human.
**Most impressive claim:** An agent's `payment.execute` is blocked deterministically, with no LLM in the decision path.
**Visual hook:** A live tool call typing out `payment.execute($25,000)` and getting stamped BLOCKED.
**Real UI:** The TrustPay logo, DESIGN.md tokens (canvas #e9eaee, white window, teal/navy, pill badges), ReasonTag copy, and the mobile invoice screen with Approve.
**Tone:** Polished (user's choice). Calm, elegant, long holds, soft dips through the canvas.
**Share caption:** AI agents can read, check and recommend invoices. They can't pay them.

## Data hygiene
- All invoice data comes from `data/invoices/` fixtures: Northwind Logistics, Example Supplies, and the fixture's explicitly FAKE bank/routing/tax values.
- The media/ screenshots are not used. They show a vendor name from real usage and a device status bar.

## Format
1920×1080, 30fps, 22.0s. Music at 120 BPM (beat 0.5s, bar 2s). The music is in A minor, built from soft pads, a sub bass, a soft kick, quiet hats and a plucked arp. Every cut lands on a beat.

## Storyboard
| # | Time | Beat | Scene | On-screen text |
|---|------|------|-------|----------------|
| 1 Hook | 0.0–3.0 | 0–6 | A console types `approval_agent → payment.execute(...)` for $25,000 to an unknown vendor. On beat 3 (1.5s) a red BLOCKED stamp lands with a low thud. | "An AI agent tried to pay $25,000." |
| 2 Reveal | 3.0–6.5 | 6–13 | Dip to canvas, then the logo shield and tick draw in and the wordmark slides up. | "AI recommends. Governance decides." |
| 3 Agents | 6.5–10.5 | 13–21 | Four agent cards light up one per beat (Intake, Verification, Policy/Risk, Approval). Below them, a governance rail logs tool calls: two ✓ logged, one ✕ blocked. | "Four agents. Every tool call logged." |
| 4 Masking | 10.5–14.5 | 21–29 | Invoice text with raw bank, routing and tax numbers. A scan line passes and the numbers flip to ****6789 / ****0021 / ****4321. Reason tags pop in. | "Bank and tax details masked at ingestion." |
| 5 Human | 14.5–18.5 | 29–37 | Phone with Northwind Logistics, $25,000.00, Pending approval, Over approval limit. A simulated tap on Approve turns the card green ("Approved"). | "Over $10,000? A human makes the call." |
| 6 Outro | 18.5–22.0 | 37–44 | Logo, tagline, and "Every decision cites evidence." Platforms: Web dashboard · Phone app. | "Every decision cites evidence." |

SFX in key: a soft filtered-noise swell into each cut, a low A thud on BLOCKED, mask "ticks" as quiet hat-like clicks, and an A-major-ish chime (A–C#–E) on Approve.
