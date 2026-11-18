"""Run scenarios through the real agent loop and score the reports against the expected answers.

    python3 evals/run_evals.py --scripted                 # the scripted stand-in (no key, no AI): checks the plumbing
    python3 evals/run_evals.py --scenarios S19 S20        # a configured model (LLM_* settings); costs money
    python3 evals/run_evals.py --scripted --list

Each scenario runs against the local mock stack (invented data only). Results go to evals/results/<run id>.json and a
summary table is printed. Real-model results from one run are in evals/published/ (see docs/EVALUATION_RESULTS.md); this file provides the
means to produce them. Nothing here fabricates or pre-fills a result.

Scoring (all coarse, text-based, documented so nobody mistakes them for more than they are):
  outcome        verdict line says inconclusive -> inconclusive; says no issue / nothing wrong -> no_issue; else cause_found
  cause_category the words of the expected category (minus filler) appear in the verdict and evidence text, at least half;
                 for 'none' it is satisfied by outcome no_issue or inconclusive
  must_mention   every phrase appears somewhere in the report (case-insensitive)
  must_not_claim no phrase appears in section 1 (the verdict line); sections 3 and 5 may name what was ruled out
  shortest_path  every expected tool was called; extra_steps = tool calls beyond the expected ones
  citations      at least one [E#] and every cited tag exists
  section5       the report has an 'Information needed from you' section, and it is not 'None' when the outcome is inconclusive

Required phrases (must_mention) are matched by this rule, so a correct answer is not failed for wording the tool never showed:
  * a phrase is also accepted in a plain paraphrase listed in PHRASE_ALTERNATIVES (for example "nothing wrong" for "no issue");
  * the tool shows templates by id (tpl-0002), so a scenario's template key (T_VERIFY) is accepted as that id;
  * a trailing "(mock wording)" is ignored, because the tool shows the failure reason without it.
A phrase the tool DID show the model, and the model left out (a repository name, say), stays a miss.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from investigator import agent, config, demo as demo_mod, llm, tools  # noqa: E402

RESULTS_DIR = ROOT / "evals" / "results"
SCEN_DIR = ROOT / "evals" / "scenarios"

# Names used by the older scenario files mapped to the real tool names.
PATH_ALIASES = {
    "fetch_logs:delivery_reports": "fetch_delivery_logs", "fetch_logs:api_failed_log": "fetch_delivery_logs",
    "call_api": "check_code_api", "get_release_changes": "recent_code_changes", "delegate_repo_check": "recent_code_changes",
}
FILLER = {"the", "and", "of", "to", "in", "a", "not", "none"}

# Plain paraphrases accepted for a required phrase. Keys are lowercase. Only wording, never a different claim.
PHRASE_ALTERNATIVES = {
    "no issue": ["no issue", "no fault", "no incident", "no problem", "nothing wrong", "nothing unusual", "found nothing", "no clear fault"],
    "not visible": ["not visible", "no tool here sees", "no tool here can see", "no tool can see", "cannot see", "can't see", "cannot be seen"],
    "replaced": ["replaced", "replaces", "replace", "replacing"],
    "latency": ["latency", "response time", "slow response", "slow to respond", "slow api"],
    "release": ["release", "deploy", "code change", "commit"],
}


def acceptable_forms(phrase: str) -> set:
    """Every form of a required phrase that counts as a match (all lowercase)."""
    p = re.sub(r"\s*\(mock wording\)\s*", "", phrase).strip().lower()
    forms = {p} | set(PHRASE_ALTERNATIVES.get(p, []))
    try:
        from mock import generate
        alias = {k.lower(): v[0] for k, v in generate.TEMPLATES.items()}.get(p)
    except Exception:
        alias = None
    if alias:
        forms.add(alias)
    return forms


class BudgetExceeded(tools.ToolError):
    """Raised before a model call that could take the run over the spending cap."""


class BudgetedModel:
    """Wraps a model function and stops BEFORE any call whose worst case would pass the cap.

    Worst case for one call = a generous estimate of the input tokens (2.5 characters per token, more than real text needs)
    at the input price, plus the full MAX_OUTPUT_TOKENS at the output price. Real usage is added after each call.
    The spend is shared by every scenario in the run, so the cap covers the whole run.
    With cap_usd=None there is no limit: the spend is still added up and reported.
    """

    def __init__(self, model, cap_usd: float | None, price_in: float, price_out: float, max_out_tokens: int):
        self.model, self.cap, self.p_in, self.p_out, self.max_out = model, cap_usd, price_in, price_out, max_out_tokens
        self.spent, self.calls = 0.0, 0

    def __call__(self, messages, system, use_tools=True):
        est_in = (len(json.dumps(messages, default=str)) + len(system or "")) / 2.5
        worst = est_in * self.p_in / 1e6 + self.max_out * self.p_out / 1e6
        if self.cap is not None and self.spent + worst > self.cap:
            raise BudgetExceeded(f"spending cap of ${self.cap:.2f} reached (spent ${self.spent:.4f}); stopped before the next call")
        resp = self.model(messages, system, use_tools)
        u = resp.get("usage") or {}
        self.spent += u.get("input_tokens", 0) * self.p_in / 1e6 + u.get("output_tokens", 0) * self.p_out / 1e6
        self.calls += 1
        return resp


def load_scenario(sid: str) -> dict:
    return json.loads((SCEN_DIR / f"{sid}.json").read_text(encoding="utf-8"))


def all_ids() -> list[str]:
    return sorted(p.stem for p in SCEN_DIR.glob("S*.json"))


def sections(report: str) -> dict:
    """Split a report into its numbered sections (1 to 5). Missing sections are empty strings."""
    out = {str(i): "" for i in range(1, 6)}
    parts = re.split(r"(?m)^\s*[#*\s]*([1-5])\s*[\).:][^\n]*", report or "")
    # parts: [pre, num, body, num, body ...] where body excludes the heading text; keep the heading line with the body
    heads, want = [], 1
    for m in re.finditer(r"(?m)^\s*[#*\s]*([1-5])\s*[\).:][^\n]*$", report or ""):
        if int(m.group(1)) == want:  # numbered items inside section 5 ("1. ...") are not new sections
            heads.append(m)
            want += 1
    for i, m in enumerate(heads):
        end = heads[i + 1].start() if i + 1 < len(heads) else len(report)
        out[m.group(1)] = report[m.start():end]
    del parts
    return out


def derive_outcome(report: str) -> str:
    verdict = sections(report)["1"].lower()
    if not verdict:
        verdict = (report or "")[:300].lower()
    if "inconclusive" in verdict or "cannot be determined" in verdict or "not determined" in verdict:
        return "inconclusive"
    if re.search(r"\bno (issue|fault|incident|problem|slowness|sign)\b|nothing (is )?(wrong|unusual)|found nothing|did not find|didn't find|within (the )?normal|looks normal|no clear fault", verdict):
        return "no_issue"
    return "cause_found"


def tokens_of(category: str) -> list[str]:
    return [t for t in re.split(r"[_+\s]+", category.lower()) if t and t not in FILLER]


def score(sc: dict, report: str, evidence: list[dict], warnings: list[str]) -> dict:
    exp = sc["expected"]
    sec = sections(report)
    low = (report or "").lower()
    outcome = derive_outcome(report)
    checks = {}
    checks["outcome"] = {"pass": outcome == exp["outcome"], "got": outcome, "expected": exp["outcome"]}
    if exp["cause_category"] == "none":
        cat_ok, hit = outcome in ("no_issue", "inconclusive"), []
    else:
        toks = tokens_of(exp["cause_category"])
        text = (sec["1"] + " " + sec["2"]).lower()
        hit = [t for t in toks if t in text or t.rstrip("s") in text]
        cat_ok = bool(toks) and len(hit) / len(toks) >= 0.5
    checks["cause_category"] = {"pass": cat_ok, "expected": exp["cause_category"], "words_found": hit}
    missing = [p for p in exp["must_mention"] if not any(f in low for f in acceptable_forms(p))]
    checks["must_mention"] = {"pass": not missing, "missing": missing}
    claimed = [p for p in exp["must_not_claim"] if p.lower() in sec["1"].lower()]
    checks["must_not_claim"] = {"pass": not claimed, "claimed_in_verdict": claimed}
    wanted = []
    for t in exp["shortest_path"]:
        t = PATH_ALIASES.get(t, t)
        if t not in wanted:
            wanted.append(t)
    used = [e["tool"] for e in evidence]
    used_ok = [e["tool"] for e in evidence if "error" not in e["result"] or "needs the PM's approval" in str(e["result"].get("error"))]
    not_called = [t for t in wanted if t not in used]
    checks["shortest_path"] = {"pass": not not_called, "expected_tools": wanted, "not_called": not_called,
                               "tool_calls": len(used), "extra_steps": max(0, len(used) - len(wanted))}
    del used_ok
    cited = set(re.findall(r"\[(E\d+)\]", report or ""))
    known = {e["id"] for e in evidence}
    checks["citations"] = {"pass": bool(cited) and cited <= known, "cited": sorted(cited), "unknown": sorted(cited - known)}
    s5 = sec["5"].strip()
    none5 = bool(re.search(r"(?i)information needed from you[\s\*:.\-]*none\b", s5.replace("\n", " ")))
    checks["section5"] = {"pass": bool(s5) and not (exp["outcome"] == "inconclusive" and none5),
                          "present": bool(s5), "says_none": none5}
    passed = sum(1 for c in checks.values() if c["pass"])
    return {"checks": checks, "passed": passed, "total": len(checks), "all_passed": passed == len(checks)}


def reset_tool_state() -> None:
    tools.PROBE.update({"count": 0, "last": 0.0})
    tools.set_case({}, keep_plain=False)
    tools._FILE_CACHE.clear()


def run_scenario(sid: str, model, scripted: bool, state_dir: Path, log=lambda *_: None) -> dict:
    """One scenario, one round, against the mock stack. `model` is a function(messages, system, use_tools=True)."""
    import os
    from mock import stack as mock_stack
    sc = load_scenario(sid)
    os.environ["STATE_DIR"] = str(state_dir)
    os.environ["SECRET_FILE"] = str(state_dir / ".ii_secret")
    os.environ["PROBE_ENABLED"] = "true"  # mock stack only; the run approves the check for this process
    reset_tool_state()
    st = mock_stack.start(sid)
    t0 = time.time()
    try:
        state = agent.new_state(sc["question"])
        res = agent.run(state, model, log=log, approved={"check_code_api"})
    finally:
        st.stop()
    sc_score = score(sc, res["report"], res["evidence"], res["warnings"])
    return {"scenario": sid, "scripted": scripted, "seconds": round(time.time() - t0, 1), "report": res["report"],
            "tools_called": [e["tool"] for e in res["evidence"]], "warnings": res["warnings"], "usage": res["usage"],
            "evidence": [{"id": e["id"], "tool": e["tool"], "args": e.get("args", {}), "result": e["result"]} for e in res["evidence"]],
            "score": sc_score, "expected": sc["expected"]}


def summary_table(results: list[dict]) -> str:
    rows = [("scenario", "outcome", "category", "mention", "not_claim", "path", "cites", "sec5", "extra", "score")]
    for r in results:
        c = r["score"]["checks"]
        f = lambda k: "pass" if c[k]["pass"] else "FAIL"
        rows.append((r["scenario"], f("outcome"), f("cause_category"), f("must_mention"), f("must_not_claim"),
                     f("shortest_path"), f("citations"), f("section5"), str(c["shortest_path"]["extra_steps"]),
                     f"{r['score']['passed']}/{r['score']['total']}"))
    widths = [max(len(row[i]) for row in rows) for i in range(len(rows[0]))]
    lines = ["  ".join(v.ljust(widths[i]) for i, v in enumerate(row)) for row in rows]
    lines.insert(1, "  ".join("-" * w for w in widths))
    full = sum(1 for r in results if r["score"]["all_passed"])
    lines.append(f"\n{full} of {len(results)} scenarios passed every check.")
    return "\n".join(lines)


def write_results(results: list[dict], scripted: bool, out_dir: Path = RESULTS_DIR, model_name: str = "", extra: dict | None = None) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S") + ("_scripted" if scripted else "")
    doc = {"run_id": run_id, "scripted_stand_in": scripted,
           "note": ("Scripted stand-in run: no language model was used. These numbers test the plumbing, not an AI."
                    if scripted else "Run with the configured model."),
           "model": "scripted stand-in" if scripted else model_name, "scenarios": results, **(extra or {})}
    p = out_dir / f"{run_id}.json"
    p.write_text(json.dumps(doc, indent=1, ensure_ascii=False), encoding="utf-8")
    return p


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--scripted", action="store_true", help="use the scripted stand-in (no key, no AI)")
    ap.add_argument("--scenarios", nargs="*", help="scenario ids (default: all)")
    ap.add_argument("--out", help="results folder (default evals/results)")
    ap.add_argument("--list", action="store_true", help="list scenario ids and exit")
    ap.add_argument("--max-cost", type=float, default=None, help="real-model runs: stop before a call that could pass this many US dollars in total. Default: no limit, so set it if you want one (the spend is always printed)")
    a = ap.parse_args(argv)
    ids = all_ids()
    if a.list:
        print(" ".join(ids))
        return 0
    config.load_env()
    wanted = a.scenarios or ids
    bad = [w for w in wanted if w not in ids]
    if bad:
        print("unknown scenario(s): " + ", ".join(bad))
        return 2
    if a.scripted:
        print(demo_mod.BANNER + "\n")
    else:
        if not config.get("LLM_API_KEY") and not llm._is_local(config.get("LLM_BASE_URL")):
            print("No LLM_API_KEY set. Use --scripted to run the stand-in, or set LLM_* in .env to run a real model.")
            return 2
        cap_text = f"capped at ${a.max_cost:.2f} in total" if a.max_cost is not None else "NO spending limit (use --max-cost to set one)"
        print(f"Running up to {len(wanted)} scenarios with a real model (this spends money, {cap_text}): provider "
              f"{config.get('LLM_PROVIDER') or 'anthropic'}, model {config.get('LLM_MODEL')}")
    import tempfile
    results, stopped = [], None
    budget = None if a.scripted else BudgetedModel(llm.get_llm(), a.max_cost, config.get_float("PRICE_IN_PER_MTOK", 2.0),
                                                   config.get_float("PRICE_OUT_PER_MTOK", 10.0), config.get_int("MAX_OUTPUT_TOKENS", 8000))
    with tempfile.TemporaryDirectory() as td:
        for sid in wanted:
            model = demo_mod.ScriptedModel() if a.scripted else budget
            print(f"running {sid} ...", flush=True)
            try:
                results.append(run_scenario(sid, model, a.scripted, Path(td)))
            except BudgetExceeded as e:
                stopped = f"{sid}: {e}"
                print(f"  stopped at {sid}: {e}")
                break
            except tools.ToolError as e:
                print(f"  {sid} could not run: {config.redact(str(e))}")
    if not results:
        return 2
    extra = None if budget is None else {"cap_usd": a.max_cost, "estimated_spend_usd": round(budget.spent, 4), "model_calls": budget.calls,
                                          "not_run": [w for w in wanted if w not in {r["scenario"] for r in results}], "stopped": stopped}
    path = write_results(results, a.scripted, Path(a.out) if a.out else RESULTS_DIR, config.get("LLM_MODEL"), extra)
    print("\n" + summary_table(results))
    if budget is not None:
        left = [w for w in wanted if w not in {r["scenario"] for r in results}]
        of_cap = f" of the ${a.max_cost:.2f} cap" if a.max_cost is not None else " (no cap was set)"
        print(f"\nSpent about ${budget.spent:.4f}{of_cap} in {budget.calls} model calls (an estimate from PRICE_*_PER_MTOK; check your provider's usage page).")
        if left:
            print("Not run (cap reached or error): " + ", ".join(left))
    print(f"\nResults written to {path}")
    if a.scripted:
        print("These are scripted stand-in results, not an AI's. Real-model results from one run are in evals/published/ (see docs/EVALUATION_RESULTS.md).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
