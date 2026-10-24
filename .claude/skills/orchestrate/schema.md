# Stage output envelope

Every workflow subagent ends its reply with exactly one fenced ```json block in this shape.
The orchestrator saves it and runs `run.py record`; an invalid envelope counts as a failed attempt.

```json
{
  "stage": "test-design",
  "agent": "wf-test-designer",
  "status": "complete | blocked | failed",
  "summary": "one paragraph, no claims that are not also listed below",
  "claims": [
    {
      "id": "C1",
      "kind": "fact | assumption | inference | unresolved",
      "subject": "REQ-3 | backend/governance/policy_engine.py:42 | tests/_wf/test_x.py::test_y",
      "statement": "what is claimed",
      "verdict": "pass | fail | risk | ok | n/a",
      "evidence": [
        {"type": "file | doc | command | test", "ref": "path:line | command | test id", "detail": "quote or output excerpt"}
      ]
    }
  ],
  "sources_read": ["docs/policy-matrix.md", "backend/models/invoice.py"],
  "artifacts": ["paths written by this stage"],
  "verification": {
    "commands": [{"cmd": "python -m pytest tests/ -q", "exit_code": 0, "output_excerpt": "212 passed"}]
  }
}
```

## Rules the validator enforces

- `kind: fact` needs at least one evidence item. `file`/`doc` refs must be `path:line` or `path:start-end`.
- `assumption`, `inference`, `unresolved` may have no evidence, but must say so honestly — never
  upgrade an inference to a fact.
- `subject` is the join key for contradiction detection. Use the same form across agents:
  `REQ-<n>` for requirements, `path:line` for code, `file::test` for tests.
- `status: complete` on `implement` and `test-run` needs at least one `verification.commands`
  entry with an `exit_code`. Work without a run command is not complete.
- `test-design` must not list implementation sources in `sources_read`: anything under `backend/`
  except `backend/models/` (public data contracts) is rejected.
