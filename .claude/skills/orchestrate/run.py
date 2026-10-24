"""State, audit trail and output checks for the multi-agent workflow (stdlib only).

Usage:
  run.py init "<task>"                     -> prints run id
  run.py prompt <run> <stage> <prompt.md>  -> stores prompt, starts an attempt (or SKIP / ESCALATE)
  run.py record <run> <stage> <out.json>   -> validates + stores output, marks done or invalid
  run.py fail <run> <stage> "<reason>"     -> marks the current attempt failed
  run.py decide <run> "<decision>"         -> appends an orchestrator decision
  run.py conflicts <run>                   -> lists subjects where stages disagree
  run.py status <run>                      -> stage table
"""

import hashlib
import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path

RUNS = Path(__file__).resolve().parents[2] / "runs"
MAX_ATTEMPTS = 3
VERIFIED_STAGES = {"implement", "test-run"}
KINDS = {"fact", "assumption", "inference", "unresolved"}
STATUSES = {"complete", "blocked", "failed"}
POSITIVE, NEGATIVE = {"pass", "ok"}, {"fail", "risk"}
LINE_REF = re.compile(r"^[^\s:]+:\d+(-\d+)?$")


def now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def load(run: str) -> tuple[Path, dict]:
    d = RUNS / run
    return d, json.loads((d / "state.json").read_text())


def save(d: Path, state: dict, event: dict) -> None:
    (d / "state.json").write_text(json.dumps(state, indent=2))
    with (d / "log.jsonl").open("a") as f:  # append-only audit trail
        f.write(json.dumps({"at": now(), **event}) + "\n")


def validate(stage: str, out: dict) -> list[str]:
    errs = [f"missing key: {k}" for k in ("stage", "agent", "status", "summary", "claims") if k not in out]
    if errs:
        return errs
    if out["stage"] != stage:
        errs.append(f"stage is {out['stage']!r}, expected {stage!r}")
    if out["status"] not in STATUSES:
        errs.append(f"bad status {out['status']!r}")
    for c in out["claims"]:
        cid = c.get("id", "?")
        if c.get("kind") not in KINDS:
            errs.append(f"{cid}: bad kind {c.get('kind')!r}")
        if not c.get("subject") or not c.get("statement"):
            errs.append(f"{cid}: subject and statement required")
        ev = c.get("evidence") or []
        if c.get("kind") == "fact" and not ev:
            errs.append(f"{cid}: fact without evidence")
        for e in ev:
            if e.get("type") in ("file", "doc") and not LINE_REF.match(e.get("ref", "")):
                errs.append(f"{cid}: {e.get('type')} evidence needs path:line, got {e.get('ref')!r}")
    if stage in VERIFIED_STAGES and out["status"] == "complete":
        cmds = (out.get("verification") or {}).get("commands") or []
        if not cmds or any("exit_code" not in c for c in cmds):
            errs.append("complete without verification commands and exit codes")
    if stage == "test-design":
        leaked = [
            p for p in out.get("sources_read", [])
            if p.startswith("backend/") and not p.startswith("backend/models/") and not p.endswith("README.md")
        ]
        if leaked:
            errs.append(f"test design read implementation: {leaked}")
    return errs


def conflicts(d: Path, state: dict) -> list[dict]:
    by_subject: dict[str, list[tuple[str, str, str]]] = {}
    for name, s in state["stages"].items():
        if s["status"] != "done":
            continue
        out = json.loads((d / s["output"]).read_text())
        for c in out["claims"]:
            by_subject.setdefault(c["subject"], []).append((name, c.get("verdict", "n/a"), c["id"]))
    found = []
    for subject, views in by_subject.items():
        verdicts = {v for _, v, _ in views}
        if verdicts & POSITIVE and verdicts & NEGATIVE:
            found.append({"subject": subject, "views": [{"stage": s, "verdict": v, "claim": i} for s, v, i in views]})
    return found


def main(argv: list[str]) -> int:
    cmd, args = argv[0], argv[1:]
    if cmd == "init":
        run = datetime.now(UTC).strftime("%Y%m%dT%H%M%S")
        d = RUNS / run
        d.mkdir(parents=True)
        save(d, {"run": run, "task": args[0], "created": now(), "stages": {}, "decisions": []},
             {"event": "init", "task": args[0]})
        print(run)
        return 0

    d, state = load(args[0])
    if cmd == "status":
        for name, s in state["stages"].items():
            print(f"{name:20} {s['status']:9} attempts={s['attempts']}")
        return 0
    if cmd == "conflicts":
        print(json.dumps(conflicts(d, state), indent=2))
        return 0
    if cmd == "decide":
        state["decisions"].append({"at": now(), "decision": args[1]})
        save(d, state, {"event": "decide", "decision": args[1]})
        return 0

    stage = args[1]
    s = state["stages"].setdefault(stage, {"status": "pending", "attempts": 0, "input_sha": None})
    if cmd == "prompt":
        text = Path(args[2]).read_text()
        sha = hashlib.sha256(text.encode()).hexdigest()
        if s["status"] == "done" and s["input_sha"] == sha:
            print("SKIP: stage already done with identical input")
            return 0
        if s["attempts"] >= MAX_ATTEMPTS:
            print(f"ESCALATE: {stage} used {MAX_ATTEMPTS} attempts")
            return 2
        s.update(status="running", attempts=s["attempts"] + 1, input_sha=sha)
        p = d / stage / f"attempt-{s['attempts']}" / "prompt.md"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
        save(d, state, {"event": "prompt", "stage": stage, "attempt": s["attempts"], "sha": sha})
        print(f"attempt {s['attempts']}")
        return 0
    if cmd == "record":
        raw = Path(args[2]).read_text()
        rel = f"{stage}/attempt-{s['attempts']}/output.json"
        (d / rel).parent.mkdir(parents=True, exist_ok=True)
        (d / rel).write_text(raw)
        try:
            errs = validate(stage, json.loads(raw))
        except json.JSONDecodeError as e:
            errs = [f"not JSON: {e}"]
        s.update(status="invalid" if errs else "done", output=rel)
        save(d, state, {"event": "record", "stage": stage, "attempt": s["attempts"], "errors": errs})
        print("\n".join(errs) if errs else "OK")
        return 1 if errs else 0
    if cmd == "fail":
        s["status"] = "failed"
        save(d, state, {"event": "fail", "stage": stage, "attempt": s["attempts"], "reason": args[2]})
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
