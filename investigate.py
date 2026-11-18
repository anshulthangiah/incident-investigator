#!/usr/bin/env python3
"""Incident investigator: a read-only, evidence-citing assistant for missing or late verification codes.

  Start:     python3 investigate.py "users say no code arrives after retries"
  Offline:   python3 -m mock.generate --all ; python3 investigate.py --demo     (scripted stand-in, NOT AI, no key)
  Continue:  python3 investigate.py --continue --file export.csv --note "support says 40 users affected"
             (add --session <id> to pick an older one; plain --continue resumes the latest)
  Numbers:   --number 999000000001 (repeatable)  --numbers-file list.txt  --prompt-numbers (typed hidden)
             The AI sees only aliases N1, N2 ...; numbers are never saved to files (only keyed fingerprints).
  API check: --approve-probe lets the investigation call your verification API once with your test number
  Memory:    --finish [--outcome confirmed|probable|unresolved|discard --cause "what it was"]   save a case note
             --knowledge   list what the tool remembers
  Other:     --sessions   list investigations          --check [--live]   what is configured / try each source
             --tools-only run the tools yourself, no AI
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

from investigator import agent, config, demo as demo_mod, inputs, knowledge, llm, numbers, tools

DEFAULT_DEMO_QUESTION = "Some users say they never get a verification code, even after trying again. Is something wrong?"


def _compact_json(obj) -> str:
    """Indented JSON, but small flat lists and objects (a group row, an hour row) stay on one line."""
    def flat(v):
        return not isinstance(v, (dict, list))

    def fmt(v, ind):
        pad = "  " * ind
        if isinstance(v, dict):
            if not v:
                return "{}"
            if all(flat(x) for x in v.values()) and len(v) <= 6:
                return json.dumps(v, default=str)
            return "{\n" + ",\n".join(f"{pad}  {json.dumps(k)}: {fmt(x, ind + 1)}" for k, x in v.items()) + f"\n{pad}}}"
        if isinstance(v, list):
            if not v:
                return "[]"
            if all(flat(x) for x in v) and len(json.dumps(v, default=str)) <= 100:
                return json.dumps(v, default=str)
            return "[\n" + ",\n".join(f"{pad}  {fmt(x, ind + 1)}" for x in v) + f"\n{pad}]"
        return json.dumps(v, default=str)
    return fmt(obj, 0)


def _yn(prompt: str) -> bool:
    try:
        return input(prompt).strip().lower() in ("y", "yes")
    except EOFError:
        return False


def status() -> None:
    def has(n):
        return "set" if config.get(n) else "NOT SET"
    prov = (config.get("LLM_PROVIDER") or "anthropic")
    print("Configuration (values are never shown)")
    print(f"  Language model ....... provider {prov}, key {has('LLM_API_KEY')}, model {config.get('LLM_MODEL') or 'NOT SET'}"
          f"   (--demo needs none of these)")
    print(f"  Delivery logs ........ {tools.logs_status()}")
    print(f"  Credit balance ....... url {has('CREDIT_URL')}, key {has('PROVIDER_API_KEY')}")
    print(f"  Repositories ......... {config.get('REPO_PATHS') or 'NOT SET'}")
    print(f"  Database checks ...... {'ON' if config.get_bool('DB_ENABLED') else 'off'}"
          f"   database: {config.get('DB_KIND') or 'sqlite'}   timestamp zone: {config.get('DB_TIMESTAMP_TZ') or 'UTC'}"
          f"   replica: {'yes' if config.get_bool('DB_REPLICA') else 'no'}")
    probe = "ON" if config.get_bool("PROBE_ENABLED") else "off"
    miss = [n for n in ("CODE_API_URL", "PROBE_PHONE") if not config.get(n)]
    print(f"  Code API check ....... {probe}" + (f"   (not set: {', '.join(miss)})" if probe == "ON" and miss else "")
          + "   sends 1 real message to your test number; needs your approval each run")
    entries = knowledge.all_entries()
    mine = sum(1 for e in entries if e["kind"] in ("confirmed", "probable", "unresolved"))
    print(f"  Memory ............... {len(entries)} entries ({mine} from your investigations)")
    print(f"  Limits ............... {config.get_int('MAX_STEPS', 12)} steps, {config.get_int('MAX_SECONDS', 120)} s per round, "
          f"{config.get_int('MAX_OUTPUT_TOKENS', 8000)} output tokens")
    avail = tools.availability()
    print("  Tools right now ...... " + ", ".join(f"{n}{'' if why is None else ' (off: ' + why + ')'}" for n, why in avail.items()))


def run_tool(name: str, **kw) -> None:
    try:
        out = tools.TOOLS[name][0](**kw)
        print(f"\n== {name} ==")
        print(config.redact(_compact_json(out)))
    except tools.ToolError as e:
        print(f"\n== {name} ==\n  could not run: {config.redact(str(e))}")


def collect_inputs(files: list[str], notes: list[str], state: dict | None) -> list[dict]:
    """state is None only before a session exists; notes are then scrubbed by the caller."""
    items = []
    for f in files or []:
        try:
            items.append(inputs.add_file(f))
            print(f"  added file: {items[-1]['name']}  ({items[-1]['kind']})")
            if items[-1]["kind"] == "log_export":
                print("    " + items[-1]["summary"])
        except inputs.InputError as e:
            print(f"  skipped: {e}")
    for n in notes or []:
        try:
            items.append(inputs.add_note(numbers.scrub(n, state, register_new=True) if state is not None else n))
            print("  added note")
        except inputs.InputError as e:
            print(f"  skipped: {e}")
    if state is not None:  # files dropped into inputs/ since the last round
        known = {p.get("sha") for p in state["provided"] if p.get("sha")}
        for p in inputs.new_files_in_inputs(known):
            try:
                items.append(inputs.add_file(str(p)))
                print(f"  picked up from inputs/: {p.name}")
            except inputs.InputError as e:
                print(f"  skipped {p.name}: {e}")
    return items


def reports_dir() -> Path:
    return config.state_dir() / "reports"


def show(res: dict, state: dict, scripted: bool = False) -> Path:
    print("\n" + res["report"] + "\n")
    for w in res["warnings"]:
        print(f"WARNING: {w}")
    out_dir = reports_dir()
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{state['id']}.md"
    ev = "\n\n".join(f"### {e['id']} {e['tool']} {json.dumps(e['args'])}\n```json\n{json.dumps(e['result'], indent=2)}\n```"
                     for e in state["evidence"])
    pv = "\n\n".join(f"### {p['id']} ({p['kind']}: {p['name']})\n{p['summary']}" for p in state["provided"]) or "(none)"
    rounds = "\n\n---\n\n".join(f"## Round {r['round']} ({r['at']})\n\n{r['report']}" for r in state["reports"])
    head = (demo_mod.BANNER + "\n\n") if scripted else ""
    text = (f"{head}# {state['symptom']}\n\nSession: {state['id']}\n\n{rounds}\n\n---\n## Evidence from tools\n\n{ev}\n\n"
            f"---\n## Information you provided\n\n{pv}\n")
    # the saved report is scrubbed like the session file
    text = numbers.scrub(config.redact(text), state, register_new=False)
    path.write_text(text, encoding="utf-8")
    try:
        path.chmod(0o600)
    except OSError:
        pass
    agent.save_state(state)
    u = res["usage"]
    print(f"Saved: {path}  (round {state['rounds']}, {res['seconds']} s, {len(state['evidence'])} tool calls so far)")
    if scripted:
        print("This round: no language model was used (scripted stand-in), cost 0.")
    else:
        print(f"This round: {u['calls']} model calls, {u['input']} in + {u['output']} out tokens, about ${u['cost_usd']} "
              f"(estimate from PRICE_IN_PER_MTOK and PRICE_OUT_PER_MTOK; check the provider's usage page)")
    if res["truncated"]:
        print("\nThe report was cut off. Run --continue to get a complete version.")
    elif not res["needs_more"]:
        print("\nThe report needs nothing more. To save what this taught the tool for future investigations:")
        print("  python3 investigate.py --finish" + (" --demo" if scripted else ""))
    else:
        print("\nThe report asks for more information (section 5). To continue:")
        print("  python3 investigate.py --continue --file <path-to-export-or-file> --note \"what you learned\"")
        print(f"  (or drop files into {inputs.input_dir()}/ and run: python3 investigate.py --continue)")
    return path


def ask_approval(tool: str, why: str) -> bool:
    """The model wants a tool that has side effects. Ask the person at the keyboard; never auto-approve."""
    if not sys.stdin.isatty():
        return False
    print(f"\n  The investigation wants to run '{tool}'.\n  {why}")
    return _yn("  Approve this now? [y/N] ")


def interactive_loop(state: dict, res: dict, model, approved: set, scripted: bool) -> None:
    while res["needs_more"]:
        print("\nAdd information now? Enter a file path or type a note; press Enter on an empty line to stop.")
        items = []
        while True:
            try:
                line = input("> ").strip()
            except EOFError:
                line = ""
            if not line:
                break
            p = Path(line.strip("'\"")).expanduser()
            try:
                items.append(inputs.add_file(str(p)) if p.exists() else inputs.add_note(numbers.scrub(line, state, True)))
                print(f"  added ({items[-1]['kind']})")
            except inputs.InputError as e:
                print(f"  skipped: {e}")
        items += collect_inputs([], [], state)
        if not items:
            print("Nothing added; stopping. Continue later with --continue.")
            return
        agent.add_user_input(state, items)
        print("\nContinuing the investigation...\n")
        res = agent.run(state, model, ask=ask_approval, approved=approved)
        show(res, state, scripted)


def gather_numbers(args, state: dict) -> list[str]:
    """Numbers from flags/file/prompt -> registered as aliases in the state. Returns lines for the PM's own screen."""
    raw = list(args.number or [])
    if args.numbers_file:
        try:
            raw += numbers.parse_list(Path(args.numbers_file).expanduser().read_text(encoding="utf-8", errors="replace"))
        except OSError:
            print(f"  skipped: cannot read {args.numbers_file}")
    if args.prompt_numbers:
        import getpass
        typed = getpass.getpass("Phone numbers (separate with commas or spaces; typing is hidden): ")
        raw += numbers.parse_list(typed)
    shown = []
    for r in raw:
        try:
            alias = numbers.register(state, r)
            shown.append(f"{alias} = a number ending in {numbers.digits10(r)[-2:]}")
        except numbers.NumberError as e:
            print(f"  skipped one entry: {e}")
    return shown


def get_model(args):
    """(model function, is_scripted)."""
    if args.demo:
        return demo_mod.ScriptedModel(), True
    return llm.get_llm(), False


def do_finish(args) -> int:
    state = agent.load_state(args.session)
    if not state["reports"]:
        print("That investigation has no report yet.")
        return 1
    scripted = bool(args.demo)
    if scripted:
        print(demo_mod.BANNER)
    print(f"Investigation {state['id']}: {state['symptom']}")
    outcome = args.outcome
    if not outcome:
        print("\nHow did it end? (this decides what the tool remembers)")
        print("  confirmed   - you know the cause\n  probable    - likely cause, not proven\n"
              "  unresolved  - cause not found (dead ends are still useful)\n  discard     - do not save anything")
        outcome = input("outcome> ").strip().lower()
    if outcome not in knowledge.OUTCOMES:
        print("Not saved: outcome must be confirmed, probable, unresolved or discard.")
        return 1
    if outcome == "discard":
        print("Nothing saved.")
        return 0
    cause = args.cause
    if not cause and outcome != "unresolved":
        cause = input("In your own words, what was the cause? > ").strip()
    model, scripted = get_model(args)  # only now: discard and bad answers never reach the model
    gist = agent.make_gist(state, model, outcome, cause or "")
    scrub = lambda t: numbers.scrub(config.redact(t), state, register_new=False)
    try:
        knowledge.validate_gist(gist)
    except knowledge.CaseError as e:
        print(f"Not saved: the drafted case note is not valid ({e}). Nothing was written.")
        return 1
    preview = {k: gist.get(k) for k in ("title", "signature", "what_it_was", "first_checks", "how_to_tell", "ruled_out",
                                         "evidence_strength")}
    print("\nProposed memory entry (patterns only; no numbers or names):")
    print(scrub(json.dumps(preview, indent=1, ensure_ascii=False)))
    print(f"Your cause, in your words: {scrub(cause or '(none)')}")
    if not args.yes and not _yn("\nSave this? [y/N] "):
        print("Not saved.")
        return 0
    e = knowledge.add_case(state, gist, outcome, cause or "", scrub)
    print(f"Saved as {e['id']} ({e['kind']}) in {knowledge.kb_file()}. Edit or delete it there any time.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("symptom", nargs="?", help="what the PM is seeing, in plain English")
    ap.add_argument("--continue", dest="cont", action="store_true", help="continue the latest (or --session) investigation")
    ap.add_argument("--session", help="session id to continue or finish (see --sessions)")
    ap.add_argument("--file", action="append", default=[], help="a file to add (delivery-log export CSV or text file); repeatable")
    ap.add_argument("--note", action="append", default=[], help="a typed note to add; repeatable")
    ap.add_argument("--ask", action="store_true", help="after a report that asks for more, prompt for files/notes right away")
    ap.add_argument("--number", action="append", default=[], help="a phone number to check (the AI sees an alias only); repeatable")
    ap.add_argument("--numbers-file", help="a text file with phone numbers (commas, spaces or lines)")
    ap.add_argument("--prompt-numbers", action="store_true", help="type numbers at a hidden prompt (not saved in shell history)")
    ap.add_argument("--approve-probe", action="store_true",
                    help="allow the investigation to call the verification API once (sends 1 real message to PROBE_PHONE)")
    ap.add_argument("--finish", action="store_true", help="close the investigation and save a case note to memory")
    ap.add_argument("--outcome", help="with --finish: confirmed, probable, unresolved or discard")
    ap.add_argument("--cause", help="with --finish: the cause, in your words")
    ap.add_argument("--yes", action="store_true", help="with --finish: save without asking")
    ap.add_argument("--knowledge", action="store_true", help="list what the tool remembers")
    ap.add_argument("--sessions", action="store_true", help="list saved investigations")
    ap.add_argument("--check", action="store_true", help="show configuration")
    ap.add_argument("--live", action="store_true", help="with --check: make one real call per source")
    ap.add_argument("--tools-only", action="store_true", help="run the tools without the AI")
    ap.add_argument("--date", help="UTC date YYYY-MM-DD for --tools-only / --live (default: today, or the mock date)")
    ap.add_argument("--days", type=int, default=1, help="days ending at --date (default 1)")
    ap.add_argument("--demo", action="store_true",
                    help="use the scripted stand-in instead of a language model: no API key, no AI, fixed rules and a template")
    ap.add_argument("--mock-scenario", metavar="ID",
                    help="start the local mock stack for a generated scenario (for example S19) and point the settings at it. "
                         "Same as MOCK_SCENARIO in .env")
    return ap


def main(argv: list[str] | None = None) -> int:
    config.load_env()
    ap = build_parser()
    a = ap.parse_args(argv)

    stack = None
    sid = a.mock_scenario or config.get("MOCK_SCENARIO")
    if sid:
        from mock import stack as mock_stack
        stack = mock_stack.start(sid)
        print(f"(mock stack for scenario {sid} running on {stack.api.base_url}; all data is invented)")
    try:
        return _main(a, ap)
    finally:
        if stack:
            stack.stop()


def _main(a, ap) -> int:
    today = config.now_utc().date()
    end = a.date or today.isoformat()
    start = (datetime.fromisoformat(end) - timedelta(days=max(a.days, 1) - 1)).date().isoformat()

    if a.knowledge:
        for line in knowledge.summary_lines():
            print(line)
        print(f"\nFile: {knowledge.kb_file()} (built-in patterns are always included; your saved cases are listed from the file)")
        return 0
    if a.finish:
        try:
            return do_finish(a)
        except (tools.ToolError, EOFError, KeyboardInterrupt) as e:
            print(f"Cannot finish: {config.redact(str(e)) if e else 'cancelled'}")
            return 2
    if a.sessions:
        rows = agent.list_sessions()
        if not rows:
            print("No saved investigations yet.")
        for r in rows:
            print(f"{r['id']}  rounds={r['rounds']}  {'OPEN (asks for more info)' if r['open'] else 'done'}  {r['symptom'][:70]}")
        return 0
    if a.check:
        status()
        if a.live:
            run_tool("fetch_delivery_logs", start_date=end, end_date=end)
            run_tool("get_credit_balance")
            run_tool("recent_code_changes", since_date=start, until_date=end)
            run_tool("check_user_data", start_date=end, end_date=end)
            run_tool("check_message_queue", start_date=end, end_date=end)
        return 0
    if a.tools_only:
        run_tool("fetch_delivery_logs", start_date=start, end_date=end)
        run_tool("get_credit_balance")
        run_tool("recent_code_changes", since_date=start, until_date=end)
        run_tool("check_user_data", start_date=start, end_date=end)
        run_tool("check_message_queue", start_date=start, end_date=end)
        return 0

    approved: set = {"check_code_api"} if a.approve_probe else set()
    try:
        model, scripted = get_model(a)
        if scripted:
            print(demo_mod.BANNER + "\n")
        if a.cont:
            state = agent.load_state(a.session)
            print(f"Continuing {state['id']}: {state['symptom']}\n")
            if a.approve_probe:
                print("  Code API check approved for this run (1 real message to your test number).")
            for line in gather_numbers(a, state):
                print("  " + line)
            if state.get("numbers") and not (a.number or a.numbers_file or a.prompt_numbers):
                print("  (numbers from earlier are remembered only as fingerprints: user records for them need the numbers "
                      "again via --number or --prompt-numbers)")
            items = collect_inputs(a.file, a.note, state)
            if not items:
                print("\nNothing new to add. Give --file and/or --note, or drop files into "
                      f"{inputs.input_dir()}/ . Continuing anyway: the investigation will re-check its tools with fresh data.")
                items = [inputs.add_note("No new information was added. Re-run the checks that were blocked or "
                                         "incomplete (new exports may have been added) and update the report.")]
            agent.add_user_input(state, items)
            print("\nContinuing the investigation...\n")
        else:
            symptom = a.symptom or (DEFAULT_DEMO_QUESTION if a.demo else None)
            if not symptom:
                ap.print_help()
                return 1
            if a.file or a.note:
                print("Starting a new investigation; adding what you provided up front:")
            state = agent.new_state(symptom)
            if a.approve_probe:
                print("  Code API check approved for this run (1 real message to your test number).")
            for line in gather_numbers(a, state):
                print("  " + line)
            items = collect_inputs(a.file, [numbers.scrub(n, state, register_new=True) for n in a.note], None)
            if items:
                agent.add_user_input(state, items)
            print(f"Investigating: {state['symptom']}\n")
        res = agent.run(state, model, ask=ask_approval, approved=approved)
    except tools.ToolError as e:
        print(f"Cannot continue: {config.redact(str(e))}")
        return 2
    show(res, state, scripted)
    if a.ask:
        try:
            interactive_loop(state, res, model, approved, scripted)
        except tools.ToolError as e:
            print(f"Cannot continue: {config.redact(str(e))}")
            return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
