# CLAUDE.md

Working rules for AI assistance on TrustPay. Read before touching code.

## Ground rules

1. **No scope creep.** Build only what the task asks for. The MVP is the invoice-processing
   lifecycle described in `README.md` and nothing else. If a request drifts toward something
   in the "Out of scope" list (real payments, real banking/ERP integrations, production auth,
   multiple domains, regulatory certification, unlimited agents), stop and say so instead of
   building it.
2. **No over-engineering.** Prefer the simplest thing that satisfies the spec and the tests.
   No abstractions for hypothetical future needs, no plugin systems, no extra config layers,
   no new dependencies unless a sprint task requires one. In-process orchestration and
   JSON-backed mocks are deliberate choices — do not "upgrade" them. Database: Supabase
   Postgres is the shared team database (team decision, 2026-10-24); SQLite stays for local
   solo dev and the test suite. Same SQLAlchemy tables for both — no Supabase client SDK,
   no second data layer.
3. **Stay on task.** Work the current sprint item from `docs/sprint-plan.md`. Do not refactor
   neighbouring code, rename things, or fix unrelated issues in passing. If you notice
   something, mention it; do not act on it.

## Non-negotiables from the spec

- AI recommends; deterministic governance decides. No LLM call inside `backend/governance/`.
- Agents never call `mock_systems/` directly — only through `tool_call_interceptor`.
- Every tool call is logged. Every decision cites evidence IDs.
- High-risk actions never execute automatically.
- Sensitive fields (`bank_account`, `routing_number`, `tax_id`) are masked at ingestion and
  never appear raw in a response, log, prompt, or explanation.
- Enums and reason codes come from `backend/models/enums.py`. Do not add free-text variants.
- Policy constants come from `data/approval_limits.json`. Do not hard-code thresholds elsewhere.

## Where things are decided

| Question | Answer lives in |
|----------|-----------------|
| What does each folder/file do? | `README.md` in that folder |
| Data shapes | `backend/models/` |
| Policy rules, thresholds, masking | `docs/policy-matrix.md` |
| Who may call which tool | `docs/agent-permissions.md` |
| Endpoint shapes | `docs/api-contracts.md` |
| Expected demo outcomes | `data/invoices/*.json → expected` |
| What to work on next | `docs/sprint-plan.md` |

If code and these docs disagree, the docs win until the team changes the doc.

## Conventions

- Python 3.11+, FastAPI, Pydantic v2, pytest. Format/lint with `ruff` (config in `pyproject.toml`).
- Frontend: React + Vite, plain CSS in `dashboard.css`. No UI framework.
- Timestamps ISO-8601 UTC. IDs use the prefixes in `backend/models/README.md`.
- Tests go next to the sprint item that introduces the behaviour; the four fixtures in
  `data/invoices/` are the source of truth for end-to-end expectations.
- Commit per sprint item with a short imperative message.

## Before finishing any task

- [ ] Does it do only what was asked?
- [ ] Did I add anything the spec does not call for?
- [ ] Do the relevant tests pass (`pytest tests/`)?
- [ ] Did I update the folder `README.md` if a file's purpose changed?
- [ ] Did I check `.claude/agents.md` and confirm the acceptance checks for the deliverables this task touches pass?

## Progress tracking (required after every commit or push)
After making a commit or push in this repo, invoke the global
`progress-tracker` skill before touching `current_progress.md` — it is
the authoritative, strict spec for how that file is created (if
missing) and updated (Completed appends, What's Next replacement,
formatting, attribution). Do not improvise the update from memory or
from this summary; invoke the skill every time this rule fires.
