"""Self-check for run.py: python -m pytest .claude/skills/orchestrate/test_run.py -q"""

import importlib.util
import json
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location("run", Path(__file__).with_name("run.py"))
run = importlib.util.module_from_spec(spec)
spec.loader.exec_module(run)


def envelope(stage, claims, status="complete", **extra):
    return {"stage": stage, "agent": "x", "status": status, "summary": "s", "claims": claims, **extra}


def fact(subject, verdict, ref="docs/policy-matrix.md:10"):
    return {"id": "C1", "kind": "fact", "subject": subject, "statement": "s", "verdict": verdict,
            "evidence": [{"type": "doc", "ref": ref}]}


@pytest.fixture
def rid(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(run, "RUNS", tmp_path)
    run.main(["init", "task"])
    return capsys.readouterr().out.strip()


def write(tmp_path, name, obj):
    p = tmp_path / name
    p.write_text(obj if isinstance(obj, str) else json.dumps(obj))
    return str(p)


def test_fact_needs_evidence_and_line_refs():
    bad = {"id": "C1", "kind": "fact", "subject": "REQ-1", "statement": "s", "evidence": []}
    assert "C1: fact without evidence" in run.validate("spec", envelope("spec", [bad]))
    assert any("path:line" in e for e in run.validate("spec", envelope("spec", [fact("REQ-1", "ok", "docs/x.md")])))
    assert run.validate("spec", envelope("spec", [fact("REQ-1", "ok")])) == []


def test_verified_stage_cannot_complete_without_commands():
    assert run.validate("implement", envelope("implement", []))
    ok = envelope("implement", [], verification={"commands": [{"cmd": "pytest", "exit_code": 0}]})
    assert run.validate("implement", ok) == []


def test_test_design_rejects_implementation_sources():
    out = envelope("test-design", [], sources_read=["backend/models/invoice.py", "backend/agents/intake_agent.py"])
    errs = run.validate("test-design", out)
    assert len(errs) == 1 and "intake_agent" in errs[0]


def test_skip_retry_cap_and_conflicts(tmp_path, rid, capsys):
    prompt = write(tmp_path, "p.md", "same input")
    run.main(["prompt", rid, "review-security", prompt])
    assert run.main(["record", rid, "review-security", write(tmp_path, "a.json", "{bad")]) == 1
    run.main(["prompt", rid, "review-security", prompt])  # retry after invalid output
    run.main(["record", rid, "review-security", write(tmp_path, "b.json", envelope("review-security", [fact("REQ-2", "fail")]))])
    capsys.readouterr()
    run.main(["prompt", rid, "review-security", prompt])
    assert capsys.readouterr().out.startswith("SKIP")

    run.main(["prompt", rid, "review-quality", prompt])
    run.main(["record", rid, "review-quality", write(tmp_path, "c.json", envelope("review-quality", [fact("REQ-2", "pass")]))])
    d, state = run.load(rid)
    [c] = run.conflicts(d, state)
    assert c["subject"] == "REQ-2"

    for i in range(3):
        run.main(["prompt", rid, "implement", write(tmp_path, f"i{i}.md", str(i))])
    assert run.main(["prompt", rid, "implement", write(tmp_path, "i3.md", "3")]) == 2
    events = [json.loads(line)["event"] for line in (d / "log.jsonl").read_text().splitlines()]
    assert events.count("prompt") == 6 and events[0] == "init"
