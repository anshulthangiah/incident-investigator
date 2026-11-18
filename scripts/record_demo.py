#!/usr/bin/env python3
"""Record real runs of the scripted stand-in for the browser demo.

    python3 scripts/record_demo.py

For each scenario in SCENARIOS it runs the real command line (`investigate.py --demo --mock-scenario ID "<question>"`)
against the local mock stack, reads the printed output (banner, tool calls, report, cost line) and the per-call
JSON results from the session file the tool wrote, and writes demo/recordings.js (window.RECORDINGS = {...}).
It also records two repo facts for the page footer: the number of scenarios and the number of tests, and how many
checks the scripted stand-in passes (from evals/run_evals.py --scripted). Nothing is typed by hand.

The fifth recording (S2-real) is read only from evals/published/real_model_v1.0.0.json; no model is called.
Standard library only. All working files go to a temporary folder and are removed. Output is deterministic: no
timestamps, ports or session ids are written.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "demo" / "recordings.js"
SCENARIOS = ["S7", "S21", "S2", "S8"]
PUBLISHED = ROOT / "evals" / "published" / "real_model_v1.0.0.json"
REAL_SCENARIO = "S2"


def run(cmd, env, timeout=900):
    return subprocess.run(cmd, cwd=ROOT, env=env, capture_output=True, text=True, timeout=timeout)


def clean_env(state: Path) -> dict:
    env = {k: v for k, v in os.environ.items() if not k.startswith(("LLM_", "PROVIDER_", "CODE_API", "DB_", "PROBE_", "MOCK_", "STATE_DIR", "SECRET_FILE", "LOGS_", "CREDIT_", "REPO_PATHS"))}
    env["STATE_DIR"] = str(state)
    env["SECRET_FILE"] = str(state / ".ii_secret")
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return env


def record(sid: str, work: Path) -> dict:
    sc = json.loads((ROOT / "evals" / "scenarios" / f"{sid}.json").read_text(encoding="utf-8"))
    state = work / sid
    state.mkdir(parents=True)
    env = clean_env(state)
    cp = run([sys.executable, "investigate.py", "--demo", "--mock-scenario", sid, sc["question"]], env)
    if cp.returncode != 0:
        raise SystemExit(f"{sid}: investigate.py failed:\n{cp.stdout}\n{cp.stderr}")
    lines = cp.stdout.splitlines()
    banner = next(l for l in lines if l.startswith("[SCRIPTED STAND-IN, NOT AI]"))
    unavailable = next((l.strip() for l in lines if l.strip().startswith("not available this run:")), "")
    calls_printed = [l.strip() for l in lines if re.match(r"^\s+\[E\d+\] ", l)]
    cost = next(l for l in lines if l.startswith("This round: no language model was used"))
    # the report is the printed block that starts at the second banner line and ends before the "Saved:" line
    idx = [i for i, l in enumerate(lines) if l.startswith("[SCRIPTED STAND-IN, NOT AI]")]
    start = idx[1]
    stop = next(i for i, l in enumerate(lines) if l.startswith("Saved:"))
    report = "\n".join(lines[start:stop]).strip("\n")
    sessions = sorted((state / "sessions").glob("*.json"))
    if len(sessions) != 1:
        raise SystemExit(f"{sid}: expected one session file, found {len(sessions)}")
    ses = json.loads(sessions[0].read_text(encoding="utf-8"))
    calls = [{"id": e["id"], "tool": e["tool"], "args": e["args"], "result": e["result"], "shortened_for_display": False}
             for e in ses["evidence"]]
    if [f"[{c['id']}] {c['tool']} {json.dumps(c['args'])}" for c in calls] != calls_printed:
        raise SystemExit(f"{sid}: printed tool calls do not match the session file")
    sys.path.insert(0, str(ROOT))
    from evals import run_evals  # the repo's own scoring rules, applied to the recorded report
    sc_score = run_evals.score(sc, report, ses["evidence"], [])
    ev = {"expected_outcome": sc["expected"]["outcome"], "outcome_from_report": sc_score["checks"]["outcome"]["got"],
          "checks_passed": sc_score["passed"], "checks_total": sc_score["total"],
          "failed_checks": [k for k, v in sc_score["checks"].items() if not v["pass"]],
          "scored_by": "evals/run_evals.py score() applied to this recorded report"}
    return {"id": sid, "title": sc["title"], "question": sc["question"], "expected_outcome": sc["expected"]["outcome"],
            "banner": banner, "tools_unavailable": unavailable, "calls": calls, "report": report, "eval": ev, "cost_line": cost,
            "source": f"python3 investigate.py --demo --mock-scenario {sid} \"<question>\"",
            "source_kind": "scripted_stand_in"}


def load_published():
    """The published real-model results file, or None (with a warning) if it is missing or unreadable. No model is called."""
    try:
        return json.loads(PUBLISHED.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        print(f"WARNING: {PUBLISHED.relative_to(ROOT)} not readable ({e}); the real-model recording is skipped", file=sys.stderr)
        return None


def record_real(pub: dict) -> dict | None:
    """Fifth recording: the saved report of one real-model scenario, read only from the published file.
    The per-call results were not saved there, so each call has a tool name and an id and nothing else."""
    sid = REAL_SCENARIO
    ent = next((x for x in pub.get("scenarios", []) if x.get("scenario") == sid), None)
    if not ent or not ent.get("report"):
        print(f"WARNING: {sid} has no saved report in the published file; the real-model recording is skipped", file=sys.stderr)
        return None
    sc = json.loads((ROOT / "evals" / "scenarios" / f"{sid}.json").read_text(encoding="utf-8"))
    run = next((r for r in pub.get("runs", []) if r.get("label") == ent.get("from_run")), {})
    m = re.match(r"(\d{4})(\d{2})(\d{2})_", str(run.get("run_id", "")))
    run_date = f"{m.group(1)}-{m.group(2)}-{m.group(3)}" if m else pub.get("date", "")
    sc_score = ent["score"]
    failed = [k for k, v in sc_score["checks"].items() if not v["pass"]]
    calls = [{"id": f"E{i}", "tool": t, "result_saved": False} for i, t in enumerate(ent["tools_called"], 1)]
    return {"id": f"{sid}-real", "title": "Provider outage on one route, answered by a real model", "question": sc["question"],
            "expected_outcome": ent["expected_outcome"], "source_kind": "real_model", "model": pub["model"], "provider": pub.get("provider", ""),
            "run_date": run_date, "scenario": sid, "calls": calls, "report": ent["report"],
            "eval": {"expected_outcome": ent["expected_outcome"], "outcome_from_report": sc_score["checks"]["outcome"]["got"],
                     "checks_passed": sc_score["passed"], "checks_total": sc_score["total"], "failed_checks": failed,
                     "scored_by": "evals/run_evals.py score(), saved in " + str(PUBLISHED.relative_to(ROOT))},
            # the published file stores spend per run, not per scenario, so no cost is shown here (never computed or invented)
            "usage": {k: ent.get(k) for k in ("input_tokens", "output_tokens", "model_calls", "seconds")},
            "source": f"{PUBLISHED.relative_to(ROOT)} (scenario {sid})"}


def real_facts(pub: dict) -> dict:
    t = pub["totals"]
    return {"model": pub["model"], "date": pub.get("date", ""), "scenarios": t["scenarios"], "checks_passed": t["checks_passed"],
            "checks_total": t["checks_total"], "scenarios_all_passed": len(t["scenarios_passing_every_check"]),
            "spend_usd": t.get("estimated_total_spend_usd"), "per_check": t["per_check"]}


def repo_facts(work: Path) -> dict:
    scen = sorted(p.stem for p in (ROOT / "evals" / "scenarios").glob("S*.json"))
    env = clean_env(work / "facts")
    (work / "facts").mkdir()
    res_dir = work / "facts_results"
    cp = run([sys.executable, "evals/run_evals.py", "--scripted", "--out", str(res_dir)], env, timeout=1800)
    if cp.returncode != 0:
        raise SystemExit("run_evals failed:\n" + cp.stdout[-2000:] + cp.stderr[-2000:])
    doc = json.loads(next(res_dir.glob("*.json")).read_text(encoding="utf-8"))
    passed = sum(r["score"]["passed"] for r in doc["scenarios"])
    total = sum(r["score"]["total"] for r in doc["scenarios"])
    full = sum(1 for r in doc["scenarios"] if r["score"]["all_passed"])
    cp = run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-t", "."], clean_env(work / "facts"), timeout=1800)
    m = re.search(r"Ran (\d+) tests?", cp.stderr + cp.stdout)
    if not m or cp.returncode != 0:
        raise SystemExit("unit tests did not pass; not recording:\n" + (cp.stderr or cp.stdout)[-2000:])
    return {"scenarios": len(scen), "tests": int(m.group(1)), "stand_in_checks_passed": passed, "stand_in_checks_total": total,
            "stand_in_scenarios_all_passed": full,
            "model_results": "Real-model results from one run are in evals/published/ (see docs/EVALUATION_RESULTS.md)"}


def main() -> int:
    work = Path(tempfile.mkdtemp(prefix="ii_record_"))
    try:
        data = {"recordings": [record(s, work) for s in SCENARIOS], "facts": repo_facts(work)}
        pub = load_published()
        if pub:
            rr = record_real(pub)
            if rr:
                data["recordings"].append(rr)
                data["facts"]["real_model"] = real_facts(pub)
    finally:
        shutil.rmtree(work, ignore_errors=True)
        for p in ROOT.rglob("__pycache__"):
            if "mock/generated" not in str(p):
                shutil.rmtree(p, ignore_errors=True)
    text = ("/* Recorded output of the real command line (scripted stand-in) on the mock system, plus one real-model report read from evals/published/. Written by scripts/record_demo.py; do not edit by hand. */\n"
            "window.RECORDINGS = " + json.dumps(data, indent=1, ensure_ascii=False, sort_keys=False) + ";\n")
    OUT.write_text(text, encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}: {len(data['recordings'])} recordings, facts {data['facts']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
