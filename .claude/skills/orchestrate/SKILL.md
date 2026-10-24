---
name: orchestrate
description: Run a task through the isolated multi-agent workflow (analysis, spec, implement, independent test design, test run, security/performance/quality review, report) with an audit trail. Use when the user asks to orchestrate a task, run the agent workflow, or wants independently tested and reviewed changes.
---

# Orchestrate

You (the main session) are the orchestrator. Subagents cannot spawn subagents, so every stage
is an `Agent` call from you. Each call starts a fresh context window: an agent knows only the
packet you write. Isolation therefore depends on you — never paste one stage's reasoning into
another stage's packet unless the table below allows it.

`R=.claude/skills/orchestrate/run.py`. Output envelope and validator rules: `schema.md`.

## Stages and context packets

| Stage | Agent | Gets | Never gets |
|-------|-------|------|------------|
| `analysis` | `wf-analyst` | task, entry points | — |
| `spec` | `wf-spec-reader` | task | analysis |
| `implement` | `wf-implementer`, `isolation: "worktree"` | task, REQ list, analysis claims | test design, tests |
| `test-design` | `wf-test-designer` | task, REQ list, output dir `.claude/runs/<run>/test-design/tests/` | analysis, implement output, diff |
| `test-run` | `wf-test-runner` | worktree path, tests dir | implement or test-design reasoning |
| `review-<lens>` (×3) | `wf-reviewer` | lens, REQ list, worktree path | implement reasoning, test output, other reviews |

The REQ list is the `claims` array of the `spec` output, verbatim. Nothing else crosses over.

## Procedure

1. `python $R init "<task>"` → run id. Read `CLAUDE.md` and `docs/sprint-plan.md`. If the task is
   out of scope, stop and tell the user (`CLAUDE.md` ground rule 1).
2. For each stage: write the packet to `.claude/runs/<run>/<stage>.packet.md`, then
   `python $R prompt <run> <stage> <packet>`.
   - `SKIP` → reuse the stored output; do not re-run (no duplicated work).
   - `ESCALATE` → stop that branch and ask the user.
   - Otherwise call the agent with the packet as its prompt, save its JSON block to
     `.claude/runs/<run>/<stage>.out.json`, then `python $R record <run> <stage> <file>`.
   - `record` errors → re-prompt the same agent once with the errors appended. Agent crash or no
     JSON → `python $R fail <run> <stage> "<reason>"` and retry. Retry only that stage.
3. Order, sending independent stages in one message so they run in parallel:
   - `analysis` ∥ `spec`
   - `implement` ∥ `test-design` — kept parallel and blind to each other on purpose.
   - `test-run`
   - `review-security` ∥ `review-performance` ∥ `review-quality`
4. Failure loop. For each `test-run` failure:
   - `impl-bug` → new `implement` attempt; packet adds only the failing test id and assertion output.
   - `test-bug` → new `test-design` attempt; packet adds only the failing test id, assertion output and
     the REQ it claims to check. Do not hand it source code.
   - `spec-ambiguity` → ask the user; record their answer with `decide`.
   - `env` → fix the environment yourself, re-run `test-run`.
   Then re-run `test-run` and the reviews. `run.py` caps every stage at 3 attempts.
5. Disagreements: `python $R conflicts <run>`. A conflict is not settled by counting votes. For each,
   read the cited evidence yourself, run the decisive command if needed, and `decide` with the
   reason and the evidence. If evidence cannot settle it, it goes in the report as unresolved.
6. Completion gate — do not report done unless all hold, each checked by you, not taken from an
   agent's claim:
   - every stage `done` in `python $R status <run>`;
   - you re-ran `python -m pytest tests/ -q -p no:cacheprovider` in the worktree and it passed;
   - no `fail` claim and no unsettled conflict remains, or each is listed as a remaining risk;
   - `.claude/agents.md` acceptance checks for touched deliverables pass.
7. Integration: show the user the worktree diff. Merge into the main tree only with their approval.
   Independent tests in `tests/_wf/` stay out of the merge unless the user asks to keep them.
8. Report: write `.claude/runs/<run>/report.md`, then give the user its path and a short summary.

## Report template

```
# <task> — run <run>
## Analysed        files and docs, from analysis + spec `sources_read`
## Changed         diff stat; per file, what and why (cite REQ-n)
## Tests           every command with exit code; counts for independent, regression, implementer tests
## Decisions       each `decide` entry, incl. conflict resolutions and their evidence
## Findings        by lens and severity, each with path:line
## Facts / assumptions / inferences / unresolved   separate lists, from all stages' claims
## Remaining risks
## Recommended follow-up
## Audit trail     .claude/runs/<run>/ (state.json, log.jsonl, per-attempt prompt.md + output.json)
```
