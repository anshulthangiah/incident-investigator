"""A scripted stand-in for the language model, so the whole loop runs offline with no API key.

THIS IS NOT AI. It picks tools by fixed keyword rules and fills a fixed template from the numbers in the tool results.
It cannot reason, cannot notice anything the rules do not name, and will be wrong whenever a case does not fit the
rules. It exists so that anyone can clone the project and see the tools, the evidence tags, the privacy scrubbing and
the report layout work end to end. Every text it produces starts with BANNER.

It has the same call shape as the real model functions in llm.py: model(messages, system, use_tools=True) -> response.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timedelta

from . import config

BANNER = ("[SCRIPTED STAND-IN, NOT AI] The text below comes from fixed keyword rules and a template, not from a language "
          "model. It only repeats numbers from the tool results and can miss or misread anything.")

# keyword -> tool. The first rule that matches adds its tool; a tool is added once.
RULES = [
    ("get_credit_balance", ("credit", "balance", "at all", "all users", "not arriving", "not coming", "since early", "since the early")),
    ("check_user_data", ("new user", "new users", "locale", "dial code", "some users", "group of users", "never get", "never arrives", "never arrive", "import")),
    ("check_message_queue", ("queue", "late", "delay", "expired", "slow", "arrives after", "arrive after", "never arrive", "small share")),
    ("check_code_api", ("spinner", "error", "nothing arrives", "api", "server", "tap", "no code", "never arrive", "small share", "dropped")),
    ("recent_code_changes", ("release", "update", "change", "deploy", "started after", "since last", "after the")),
]


def _text_of(content) -> str:
    if isinstance(content, str):
        return content
    return " ".join(b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text")


def plan_tools(question: str, available: list[str]) -> list[str]:
    q = question.lower()
    picked = ["fetch_delivery_logs"]
    for tool, words in RULES:
        if any(w in q for w in words) and tool not in picked:
            picked.append(tool)
    if "check_numbers" in available:  # only offered when the PM supplied numbers
        picked.append("check_numbers")
    return [t for t in picked if t in available]


def _window():
    today = config.now_utc().date()
    return (today - timedelta(days=6)).isoformat(), today.isoformat()


def _args(tool: str) -> dict:
    start, end = _window()
    if tool in ("fetch_delivery_logs", "check_user_data", "check_message_queue", "check_numbers"):
        return {"start_date": start, "end_date": end}
    if tool == "recent_code_changes":
        return {"since_date": start, "until_date": end}
    return {}


def _results(messages: list) -> list[tuple[str, dict, str]]:
    """(evidence id, parsed result, tool name) for every tool result in the conversation."""
    names = {}
    out = []
    for m in messages:
        if isinstance(m.get("content"), list):
            for b in m["content"]:
                if b.get("type") == "tool_use":
                    names[b["id"]] = b["name"]
                if b.get("type") == "tool_result":
                    s = str(b.get("content", ""))
                    mm = re.match(r"\[(E\d+)\]\s*(.*)", s, re.S)
                    if mm:
                        try:
                            out.append((mm.group(1), json.loads(mm.group(2)), names.get(b["tool_use_id"], "?")))
                        except ValueError:
                            pass
    return out


def _unavailable(system: str) -> list[tuple[str, str]]:
    m = re.search(r"TOOLS NOT AVAILABLE THIS RUN[^:]*:\s*(.*)$", system or "", re.S)
    if not m:
        return []
    items = []
    for part in m.group(1).split(" | "):
        if ":" in part:
            n, why = part.split(":", 1)
            items.append((n.strip(), why.strip()))
    return items


def _available(system: str) -> list[str]:
    from . import tools
    return [s["name"] for s in tools.schemas()]


def _num(x) -> str:
    return f"{round(float(x), 1):g}"


def _day(iso: str) -> str:
    try:
        d = datetime.strptime(iso, "%Y-%m-%d")
        return f"{d.day} {d.strftime('%b')}"
    except (ValueError, TypeError):
        return str(iso)


def _short_reason(why: str) -> str:
    return why.split(" (")[0].strip().rstrip(".")


def _optional_line(unavailable: list[tuple[str, str]]) -> str:
    """One line for the checks that are switched off; the stand-in never makes them a 'needed' item."""
    parts = []
    for n, why in unavailable:
        if n == "check_numbers":
            parts.append("phone-number lookup (use --number or --prompt-numbers)")
        elif n == "check_code_api":
            if "PROBE_ENABLED" in why:
                parts.append("the test-message check of the verification API (set PROBE_ENABLED and use --approve-probe; "
                             "it sends one real message to your own test number)")
            else:
                parts.append("the test-message check of the verification API (first set CODE_API_URL and PROBE_PHONE)")
    if not parts:
        return ""
    return "Optional checks that are switched off in this run: " + " and ".join(parts) + "."


def _concentration_sentence(c: dict) -> str:
    dim, val = c["dimension"], c["value"]
    s = (f"on the latest day {_num(c['failure_rate_pct'])}% of requests on {dim} {val} failed, against "
         f"{_num(c['other_rate_pct'])}% on other {dim}s")
    if c.get("first_bad_hour_utc") is not None:
        s += f", starting around {int(c['first_bad_hour_utc']):02d}:00 UTC"
    return s + f". The failures are concentrated on {dim} {val}, not spread evenly"


def _concentration_step(c: dict, date_iso: str) -> str:
    dim, val = c["dimension"], c["value"]
    when = f"from about {int(c['first_bad_hour_utc']):02d}:00 UTC on {_day(date_iso)}" if c.get("first_bad_hour_utc") is not None \
        else f"on {_day(date_iso)}"
    other = {"route": "send through another route", "sender": "send through another sender",
             "template": "use another template"}.get(dim, f"use another {dim}")
    return (f"Ask your provider whether {dim} {val} had an incident {when}; compare against that {dim}'s rate in earlier "
            f"days; if you can, {other} meanwhile.")


def build_report(results: list[tuple[str, dict, str]], system: str, question: str) -> str:
    by = {}
    for eid, res, tool in results:
        by[tool] = (eid, res)
    ev, findings, kinds, steps, needs = [], [], [], {}, []
    inconclusive = False

    def finding(text: str, kind: str, step: str | None = None):
        findings.append(text)
        kinds.append(kind)
        if step and kind not in steps:
            steps[kind] = step

    if "fetch_delivery_logs" in by:
        e, r = by["fetch_delivery_logs"]
        if r.get("error"):
            ev.append(f"- fetch_delivery_logs could not run: {r['error']} [{e}]")
        elif not r.get("total"):
            ev.append(f"- fetch_delivery_logs found no rows; days without data: {', '.join(r.get('days_without_data') or []) or 'none'} [{e}]")
            if r.get("days_without_data"):
                inconclusive = True
                finding(f"Some dates have no log data, which means a missing export, not zero traffic [{e}].", "missing",
                        "Get the delivery-log export for the dates without data before drawing any conclusion.")
                needs.append((f"A delivery-log export (CSV, UTC) covering {', '.join(_day(d) for d in r['days_without_data'])}",
                              "it would show whether codes were requested then",
                              "export it from the provider's console and add it with --file"))
        else:
            n_days = len(r["days"])
            ev.append(f"- Volume: {r['total']} requests over {n_days} days, {r['failed']} failed ({_num(r['failure_rate_pct'])} percent) [{e}]")
            rpd, frd = r["requests_per_day"], r.get("failure_rate_pct_per_day", {})
            ev.append(f"- Requests per day [{e}]")
            ev += [f"  - {_day(d)}: {n} requests, {_num(frd.get(d, 0))} percent failed" for d, n in rpd.items()]
            per_day = list(rpd.items())
            if len(per_day) >= 3:
                hours = r.get("requests_per_hour_utc")
                # the last day is a part day, so compare per-hour volume in the last 6 hours when it is available
                if hours and len(hours) >= 12:
                    vals = list(hours.values())
                    recent, before = vals[-6:], vals[-30:-6] or vals[:-6]
                    if before and sum(recent) / len(recent) < 0.7 * (sum(before) / len(before)):
                        finding(f"Request volume in the last 6 hours is under 70 percent of the hours before it [{e}] (volume rule).",
                                "volume", "Compare request volume with the same hours on earlier days, and ask engineering whether "
                                          "the app stopped sending requests.")
            conc = r.get("concentration")
            latest = r.get("latest_day_utc") or (per_day[-1][0] if per_day else "")
            if conc:
                finding(_concentration_sentence(conc) + f" [{e}] (concentration rule).", "concentration",
                        _concentration_step(conc, latest))
                groups = (r.get("failures_by_group", {}).get(conc["dimension"], {}) or {}).get("latest_day", [])
                ev.append(f"- Failures by {conc['dimension']} on the latest day [{e}]")
                ev += [f"  - {conc['dimension']} {g['value']}: {_num(g['failure_rate_pct'])} percent of {g['requests']} requests failed"
                       for g in groups]
            if r.get("failure_reasons"):
                top = r["failure_reasons"][0]
                ev.append(f"- Most common failure reason: {top['reason']} ({top['count']} rows). Category: {top['category']}. "
                          f"Who fixes it: {top['who_fixes']} [{e}]")
                last_day = list(frd.values())
                if last_day and last_day[-1] > 8 and not conc:
                    finding(f"On the latest day {_num(last_day[-1])} percent of requests failed, above the usual low single digits, "
                            f"and no single route, sender or template stands out by the fixed rule [{e}] (failure-rate rule).",
                            "rate", f"Ask your provider for a status report for {_day(latest)} and compare it with the previous week.")
                    for dim, tabs in (r.get("failures_by_group") or {}).items():
                        top3 = tabs.get("latest_day", [])[:3]
                        if top3:
                            ev.append(f"- Highest failure rates by {dim} on the latest day [{e}]")
                            ev += [f"  - {dim} {g['value']}: {_num(g['failure_rate_pct'])} percent of {g['requests']} requests failed"
                                   for g in top3]
                    cats = list(r.get("failures_by_category", {}))
                    if cats:
                        finding(f"Largest failure category: {cats[0]} [{e}].", "category")
            rep = r.get("repeat_requests", {})
            daily = rep.get("share_of_requests_pct_per_day", {})
            if daily and list(daily.values())[-1] >= 10:
                finding(f"{_num(list(daily.values())[-1])} percent of requests on the latest day are repeats within the validity "
                        f"window, and a newer code replaces an older one [{e}] (repeat rule). The logs cannot show which code was typed.",
                        "repeat", "Ask engineering how the server decides which code to accept when more than one is active. "
                                  "To test: request two codes in a row and enter the first one.")
                ev.append(f"- Repeat requests: {rep.get('recipients_with_a_repeat')} recipients, {_num(rep.get('share_of_requests_pct'))} percent of requests [{e}]")
            d = r.get("delivery_delay_s")
            if d:
                ev.append(f"- Delivery delay at the provider: median {d['median']} s, p90 {d['p90']} s, max {d['max']} s [{e}]")
                if d["p90"] > 60:
                    finding(f"Delivery delay at the provider is high (p90 {d['p90']} s) [{e}] (delay rule).", "delay",
                            f"Ask your provider about delivery delay on {_day(latest)}, and check that the code validity window "
                            "is longer than the delay.")
            if r.get("days_without_data"):
                ev.append(f"- Days without data: {', '.join(_day(x) for x in r['days_without_data'])} (a missing export, not zero traffic) [{e}]")
            if r.get("data_quality"):
                inconclusive = True
                finding(f"Data quality problem: {r['data_quality']} [{e}]", "quality",
                        "Get a fresh export that was not re-saved by a spreadsheet, then run again.")
                needs.append(("A fresh delivery-log export that was not re-saved by a spreadsheet",
                              "number-shape and repeat checks need it", "export it again from the provider's console"))

    if "get_credit_balance" in by:
        e, r = by["get_credit_balance"]
        if r.get("error"):
            ev.append(f"- get_credit_balance could not run: {r['error']} [{e}]")
        else:
            ev.append(f"- Credit balance now: {r['balance']} [{e}]")
            if r["balance"] <= 0:
                finding(f"The credit balance is zero, so requests are refused before submission [{e}] (credit rule).", "credit",
                        "Top up credit; paused requests may need to be replayed.")

    if "check_user_data" in by:
        e, r = by["check_user_data"]
        if r.get("error"):
            ev.append(f"- check_user_data could not run: {r['error']} [{e}]")
        else:
            bad = [d for d in r["days"] if d["locale_empty"] or d["dial_code_empty"]]
            ev.append(f"- Users created with an empty locale or dial code on {len(bad)} of {len(r['days'])} days [{e}]")
            if bad:
                tot_l, tot_d = sum(d["locale_empty"] for d in bad), sum(d["dial_code_empty"] for d in bad)
                finding(f"New users with an empty locale ({tot_l}) or empty dial code ({tot_d}) appear from {bad[0]['created_date_utc']} [{e}] (user-data rule).", "userdata",
                        f"Ask engineering what changed in sign-up from {_day(bad[0]['created_date_utc'])}, and check one affected user record.")

    if "check_message_queue" in by:
        e, r = by["check_message_queue"]
        if r.get("error"):
            ev.append(f"- check_message_queue could not run: {r['error']} [{e}]")
        else:
            ev.append(f"- Queue: {sum(x['rows'] for x in r['waiting_now'])} rows waiting now; newest row recent: {r.get('newest_row_recent')} [{e}]")
            if r.get("newest_row_recent") is False:
                inconclusive = True
                finding(f"The newest queue row is not recent: {r.get('queue_note')} [{e}]", "queue_stale",
                        "Find out where current queue data is held before relying on the queue check.")
                needs.append(("Where current queue data is held", "the queue table has nothing recent for these dates",
                              "ask engineering or the DBA"))
            if r.get("reading"):
                ev.append(f"- Queue reading: {r['reading']} [{e}]")
            stuck = [x for x in r["waiting_now"] if x["status"] == "SENDING" and x.get("oldest_age_minutes", 0) > 30]
            if stuck:
                inconclusive = True
                finding(f"Rows have been waiting far longer than normal in SENDING [{e}]. A scheduled database job would normally reset them, and no tool here can see whether the scheduled jobs are running.",
                        "stuck", "Ask the DBA whether the scheduled database jobs are running and when each last ran.")
                needs.append(("Whether the scheduled database jobs are running and when each last ran",
                              "it would confirm or rule out stopped jobs", "ask whoever runs the database (the DBA)"))
            old = [x for x in r["waiting_now"] if x["status"] == "PENDING" and x.get(f"older_than_{r['code_validity_minutes_assumed']}_min", 0)]
            if old:
                finding(f"Rows have been PENDING for longer than the code validity of {r['code_validity_minutes_assumed']} minutes, so codes in them would have expired [{e}] (queue rule). The queue cannot tell code rows from other text messages.",
                        "queue_old", "Ask engineering why rows wait longer than the code validity, and whether the sending worker is running.")
            if r.get("unusual_statuses_in_window"):
                ev.append(f"- Unusual statuses (manual clean-ups): {r['unusual_statuses_in_window']} [{e}]")

    if "check_code_api" in by:
        e, r = by["check_code_api"]
        if r.get("error"):
            ev.append(f"- check_code_api did not run: {r['error']} [{e}]")
            if "approval" in r["error"]:
                needs.insert(0, ("Your approval to call the verification API once with your own test number",
                                 "it tests the API directly and sends one real message to your test number",
                                 f"run again with --approve-probe ({r.get('to_approve')})"))
        else:
            ev.append(f"- API check: result {r.get('result')}, HTTP {r.get('http_status')}, {r.get('elapsed_ms')} ms, message: {r.get('response_message')} [{e}]")
            if r.get("SECURITY_FINDING"):
                finding(f"SECURITY: {r['SECURITY_FINDING']} [{e}]", "security",
                        "Tell the owner of the verification API about this security finding today.")
            if r.get("result") in ("server_error", "no_answer"):
                finding(f"The verification API answers '{r.get('result')}', so affected requests never reach the provider [{e}] (API rule). {r.get('reading', '')}",
                        "api", "Ask engineering for the API server's own log entry for the failing call.")
                needs.append(("The API server's own log entry for the failing call", "it names the real cause", "ask engineering"))
            pl = r.get("provider_log", {})
            if pl.get("row_seen") is False:
                ev.append(f"- Provider log: not seen yet after {pl.get('waited_s')} s; the log lags, this is not a sign of a fault [{e}]")

    if "recent_code_changes" in by:
        e, r = by["recent_code_changes"]
        if r.get("error"):
            ev.append(f"- recent_code_changes could not run: {r['error']} [{e}]")
        else:
            n = sum(len(v.get("commits", [])) for v in r["repos"].values())
            ev.append(f"- Code changes: {n} commits in the configured repositories in the window (subjects only) [{e}]")

    if "check_numbers" in by:
        e, r = by["check_numbers"]
        if r.get("error"):
            ev.append(f"- check_numbers could not run: {r['error']} [{e}]")
        else:
            ev.append(f"- Numbers checked: {r['summary']} [{e}]")

    unavailable = _unavailable(system)

    if not findings:
        verdict = "No clear fault found by the fixed rules. Confidence: low. This is not proof that nothing is wrong."
    elif inconclusive and not any("rule)" in f for f in findings):
        verdict = "Inconclusive: " + findings[0].split(" [")[0].rstrip(".") + ". Confidence: low."
    else:
        verdict = "Rule-based reading: " + findings[0].split(" [")[0].rstrip(".") + ". Confidence: low to medium; check the evidence yourself."
    cites = re.findall(r"\[(E\d+)\]", " ".join(findings))
    verdict += f" [{cites[0]}]" if cites else (f" [{results[0][0]}]" if results else "")

    first_e = results[0][0] if results else "E1"
    ran = sorted({t for _, _, t in results})
    lines = [BANNER, "", "1) Verdict", verdict, "", "2) Evidence"] + (ev or ["- No tool results"])
    if len(findings) > 1:
        lines.append(f"- Rule findings [{first_e}]")
        lines += [f"  - {f}" for f in findings]
    lines += ["", "3) Not checked / limits",
              f"- Checks that ran: {', '.join(ran) or 'none'}. This scripted stand-in does not decide which causes are ruled out, so treat every other cause as not yet checked [{first_e}].",
              "- Not visible to any tool here: the API server's own log, the database scheduler, the code that validates a code, and "
              "anything outside the configured sources."]
    for n, why in unavailable:
        lines.append(f"- {n} was not run: {_short_reason(why)}.")
    next_steps = list(steps.values())[:3]
    lines += ["", "4) Suggested next steps"] + ([f"- {t}" for t in next_steps] or
                                                ["- Add a more specific symptom or the affected dates and run again."])
    opt = _optional_line(unavailable)
    if not findings and not needs:
        # No rule fired: the report says "no clear fault, not proof", so it must also say what would narrow it down.
        needs = [("The dates and times when people saw the problem, and which app or screen they used",
                  "the rules read a whole window and can miss a short or narrow fault",
                  "ask the people who reported it, then run again with those dates in the question")]
        if any(n == "check_numbers" for n, _ in unavailable):
            needs.append(("One or two phone numbers of affected users",
                          "the tool can then look at those users' requests and repeats (it sees aliases such as N1, never the numbers)",
                          "use --number or --prompt-numbers"))
            opt = _optional_line([u for u in unavailable if u[0] != "check_numbers"])
        needs.append(("The verification API server's own log for a time when it failed",
                      "some faults leave nothing in the delivery log and no tool here can read that log",
                      "ask engineering"))
    if needs:
        lines += ["", "5) Information needed from you"]
        for i, (thing, why, how) in enumerate(needs, 1):
            lines += [f"{i}. {thing}", f"   - Why: {why}", f"   - How or who to ask: {how}"]
        if opt:
            lines += ["", opt]
    else:
        lines += ["", "5) Information needed from you: None." + (f"\n{opt}" if opt else "")]
    return "\n".join(lines)


def gist_json(messages: list) -> str:
    text = _text_of(messages[-1]["content"]) if messages else ""
    tools_used = re.findall(r"Tools used: ([^\n]*)", text)
    names = [t.strip() for t in (tools_used[0].split(",") if tools_used else []) if t.strip()]
    from . import tools
    names = [n for n in names if n in tools.TOOLS] or ["fetch_delivery_logs"]
    return json.dumps({"title": "Scripted stand-in case note", "signature": ["scripted", "demo"],
                       "what_it_was": "Not determined by the stand-in; see the PM's own words.",
                       "first_checks": names[:4], "how_to_tell": "See the report; the stand-in did not analyse it.",
                       "ruled_out": [], "evidence_strength": "None: written by a template."})


class ScriptedModel:
    """Same call shape as the real model functions."""
    is_scripted = True

    def __init__(self):
        self.calls = 0

    def __call__(self, messages: list, system: str, use_tools: bool = True) -> dict:
        self.calls += 1
        if not use_tools:
            return {"content": [{"type": "text", "text": BANNER + "\n" + gist_json(messages)}], "stop_reason": "end_turn",
                    "usage": {"input_tokens": 0, "output_tokens": 0}}
        results = _results(messages)
        last = messages[-1] if messages else {}
        fresh_results = isinstance(last.get("content"), list) and any(b.get("type") == "tool_result" for b in last["content"])
        if not fresh_results:
            first = _text_of(messages[0]["content"])
            extra = " ".join(_text_of(m["content"]) for m in messages[1:] if m["role"] == "user" and not (
                isinstance(m["content"], list) and any(b.get("type") == "tool_result" for b in m["content"])))
            plan = plan_tools(first + " " + extra, _available(system))
            blocks = [{"type": "text", "text": f"{BANNER}\nRunning these tools by keyword rule: {', '.join(plan)}."}]
            for i, t in enumerate(plan):
                blocks.append({"type": "tool_use", "id": f"demo_{self.calls}_{i}", "name": t, "input": _args(t)})
            return {"content": blocks, "stop_reason": "tool_use", "usage": {"input_tokens": 0, "output_tokens": 0}}
        question = _text_of(messages[0]["content"])
        return {"content": [{"type": "text", "text": build_report(results, system, question)}], "stop_reason": "end_turn",
                "usage": {"input_tokens": 0, "output_tokens": 0}}
