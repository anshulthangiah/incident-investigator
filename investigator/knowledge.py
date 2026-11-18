"""Case memory: what past investigations and known failure patterns taught this tool.

Stored in knowledge/cases.json (plain JSON you can read and edit). Entry kinds:
  known_pattern   built-in generic leads for this invented domain; leads, not proof
  confirmed       a past investigation whose cause the PM confirmed
  probable / unresolved   a past investigation without a confirmed cause (kept so dead ends are not repeated)

Rules that keep memory from making investigations worse:
- Entries hold patterns only: no phone numbers, no raw rows, no names. Everything is scrubbed before saving.
- Nothing is saved without the PM's decision (outcome: confirmed, probable, unresolved or discard) and a yes.
- The AI treats entries as LEADS to check first. It must still verify against current evidence and cite [E#];
  it may never state a past cause as the answer on the strength of memory alone.
"""
from __future__ import annotations

import json
import re
from datetime import datetime

from . import config

OUTCOMES = ("confirmed", "probable", "unresolved", "discard")
MAX_PROMPT_ENTRIES = 6
MAX_FIELD = 400
SEED_SOURCE = "invented example for this project"


def kb_dir():
    return config.state_dir() / "knowledge"


def kb_file():
    return kb_dir() / "cases.json"


def _seed(id_, title, signature, reading, first_checks, distinguish):
    return {"id": id_, "kind": "known_pattern", "title": title, "signature": signature, "reading": reading,
            "first_checks": first_checks, "distinguish": distinguish, "source": SEED_SOURCE}


SEEDS = [
    _seed("K-background-noise", "Normal background failures are recipient-side",
          ["failed", "failure", "rate", "not delivered", "some users", "few people"],
          "A small share of requests fail every day for reasons on the recipient's side (unreachable phone, opted out, expired "
          "while the phone was off). A rate in the low single digits is not an incident on its own.",
          ["fetch_delivery_logs"],
          "Compare the failure categories and the daily rate with earlier days. An incident shows a new category, a sharp "
          "rate change, or a drop in volume."),
    _seed("K-credit-paused", "Credit exhausted: requests are paused before submission",
          ["no code", "not receiving", "stopped", "all users", "credit", "balance", "volume drop", "since morning"],
          "When the account has no credit the provider API refuses requests before they are submitted. They leave no delivery "
          "row, so delivery logs show fewer rows and no new failures. The refusals may show in the failed-call log.",
          ["get_credit_balance", "fetch_delivery_logs"],
          "Low or zero credit plus a volume drop and no new failed delivery rows, or error code E101 in the failed-call log. "
          "A healthy balance now does not prove it was healthy at the time."),
    _seed("K-registration", "Template or registration failures",
          ["template", "sender", "registration", "registered", "blocked", "rejected", "some users", "login", "reset"],
          "Failure reasons in the registration category mean a template or sender is not registered with the provider, "
          "usually after a template or sender change. One template or sender carries most of the failures.",
          ["fetch_delivery_logs", "recent_code_changes"],
          "failures_by_category shows Registration and one template id carries most failures; other templates are fine."),
    _seed("K-empty-dial-code", "Empty dial code on a user record",
          ["dial code", "country code", "invalid number", "some users", "group of users", "import", "new users", "never arrives"],
          "The dial code comes from the user record. If it is empty, the number sent to the provider is too short: either the "
          "provider rejects it with a number-format reason, or the request fails earlier. Only the affected users are hit.",
          ["check_user_data", "check_numbers", "fetch_delivery_logs"],
          "dial_code_empty above zero on the incident days; failed rows with 10-digit recipients while others have 12."),
    _seed("K-api-down", "The verification API fails or hangs, so nothing reaches the provider",
          ["spinner", "timeout", "no code", "all users", "api", "error", "slow", "hang", "server error", "500"],
          "If the API errors, is down, or waits for a downstream call, users get no code and neither the database nor the "
          "provider logs show anything. A success status can still come back after a very long wait.",
          ["check_code_api", "fetch_delivery_logs"],
          "check_code_api shows a server error, no answer, a very long response, or a success with no provider row for the "
          "test number. The reason behind a server error is only in the API server's own log."),
    _seed("K-stale-credential", "Stale or rejected credential on the API call",
          ["401", "403", "unauthorized", "token", "expired", "credential", "rejected"],
          "A 401 or 403 from the API check means the call was refused for lack of a token or for a stale one. A stale "
          "credential in the check says nothing about the live API used by the app.",
          ["check_code_api"],
          "check_code_api result is auth_rejected, or the tool reports that the token has expired."),
    _seed("K-late-delivery", "Codes delivered but late",
          ["late", "delay", "slow", "expired", "arrives after", "takes long", "minutes"],
          "Delivered rows with a long gap between request and delivery. The gap is measured at the provider only; a wait "
          "before the request reaches the provider is not part of it.",
          ["fetch_delivery_logs", "check_message_queue"],
          "delivery_delay_s p90 well above the usual few seconds on a day, not just the maximum. If the provider gap is "
          "normal but users still wait, look at the queue."),
    _seed("K-missing-export", "A date with no log data is a missing file, not zero traffic",
          ["compare", "baseline", "earlier", "yesterday", "last week", "missing", "hole", "gap"],
          "Past dates beyond the few most recent days that the live API serves come from exported files. No rows for a date means the export "
          "was not added, not that nobody asked for a code.",
          ["fetch_delivery_logs"],
          "days_without_data in the result; ask for an export that covers those dates."),
    _seed("K-hand-fix", "Records edited by hand later can hide earlier problems",
          ["fixed", "updated manually", "edited by hand", "past", "last week", "already fixed"],
          "The database checks read current data, so an old day can show zero empty values even though a fault happened.",
          ["check_user_data"],
          "See the note in the user-data result."),
    _seed("K-repeat-replaced", "Repeated requests replace earlier codes, so a code can be 'invalid'",
          ["invalid code", "wrong code", "login", "retry", "retries", "again", "resend", "repeated", "code not accepted"],
          "A newer code replaces the older one. A user who asks twice and types the first code is told it is invalid even "
          "though both messages arrived. The response to the login is the same for every cause.",
          ["fetch_delivery_logs", "check_numbers"],
          "repeat_requests shows a large share of recipients asking again within the validity window; for a specific user, "
          "requests_within_2_min_of_previous is high. The logs cannot show which code was typed."),
    _seed("K-jobs-stopped", "Scheduled database jobs stopped (no tool here can see it)",
          ["scheduled", "job", "agent", "not running", "stopped", "nightly", "cleanup", "batch", "devops", "dba", "stuck"],
          "Clean-up, reset and retry jobs run on the database server's scheduler. If the scheduler stops, rows stay in "
          "process or go stale and a small share of requests disappears. The database login used here cannot read the "
          "scheduler's status or any job history.",
          ["check_message_queue", "check_user_data"],
          "Only the server can show it. Ask whoever runs the database whether the scheduler is running, since when, and when each "
          "job last ran. Indirect hints: rows waiting far longer than normal, or old PENDING rows a job would normally clear."),
    _seed("K-old-codes-accepted", "An older code still works after a newer one was issued (a code-level fault)",
          ["old code", "previous code", "stale", "accepted", "security", "validate", "validation", "wrong code works"],
          "An older code still works after a newer one was issued, so earlier codes stay valid together with the "
          "latest. This is a code-level fault: it leaves no trace in the delivery logs or the queue.",
          ["recent_code_changes"],
          "Only code review shows it: does validation pick the latest record or search all of them? Logs cannot prove it "
          "either way."),
]


def _load() -> list[dict]:
    f = kb_file()
    if not f.exists():
        return list(SEEDS)
    try:
        data = json.loads(f.read_text(encoding="utf-8"))
        if not isinstance(data, list):
            return list(SEEDS)
    except (OSError, ValueError):
        return list(SEEDS)
    have = {e.get("id") for e in data}
    return data + [s for s in SEEDS if s["id"] not in have]


def all_entries() -> list[dict]:
    return _load()


def _seed_ids() -> set[str]:
    return {s["id"] for s in SEEDS}


def _save(entries: list[dict]) -> None:
    kb_dir().mkdir(parents=True, exist_ok=True)
    mine = [e for e in entries if e["id"] not in _seed_ids()]
    kb_file().write_text(json.dumps(mine, indent=1, ensure_ascii=False), encoding="utf-8")


def _words(s: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]{3,}", (s or "").lower()))


def relevant(symptom: str, n: int = MAX_PROMPT_ENTRIES) -> list[dict]:
    q = _words(symptom)
    scored = []
    for e in _load():
        keys = _words(" ".join(e.get("signature", [])) + " " + e.get("title", ""))
        scored.append((len(q & keys) + (0.5 if e.get("kind") == "confirmed" else 0), e))
    scored.sort(key=lambda x: -x[0])
    out = [e for s, e in scored if s > 0][:n]
    return out or [e for _, e in scored[:3]]


def prompt_block(symptom: str) -> str:
    """Compact text for the system prompt. Leads only; the model is told to verify."""
    lines = []
    for e in relevant(symptom):
        tag = {"known_pattern": "known pattern", "confirmed": "CONFIRMED earlier", "probable": "probable earlier",
               "unresolved": "unresolved earlier"}.get(e["kind"], e["kind"])
        lines.append(f"- [{e['id']}] ({tag}) {e['title']}. {e.get('reading', '')} First checks: "
                     f"{', '.join(e.get('first_checks', []))}. Tell apart: {e.get('distinguish', '')}")
    cls = "; ".join(f"{e['title']} (check: {', '.join(e.get('first_checks', [])[:2])})"
                    for e in _load() if e["kind"] == "known_pattern")
    return ("PAST CASES AND KNOWN PATTERNS. These are leads to check first, never conclusions. Verify each against current "
            "evidence and cite [E#]; never state a past cause as the answer because memory says so. If a lead does not fit "
            "the current evidence, say so.\n" + "\n".join(lines) +
            "\nFAILURE CLASSES TO COVER. In section 3, write ONE line naming the classes ruled out with evidence "
            "(with [E#] tags), then one short line each only for classes that are still possible or cannot be checked with "
            "the available tools, with the reason in a few words. Do not list a class twice: " + cls)


def clip(s, n: int = MAX_FIELD) -> str:
    return re.sub(r"\s+", " ", str(s or "")).strip()[:n]


class CaseError(ValueError):
    """The proposed case note is not valid and was not saved."""


def real_tool_names() -> set[str]:
    from . import tools
    return set(tools.TOOLS)


def validate_gist(gist: dict) -> None:
    if not isinstance(gist, dict):
        raise CaseError("the case note is not an object")
    for k in ("title", "what_it_was", "how_to_tell"):
        if not clip(gist.get(k)):
            raise CaseError(f"the case note has no '{k}'")
    checks = gist.get("first_checks") or []
    if not isinstance(checks, list) or not checks:
        raise CaseError("the case note names no first checks")
    bad = [c for c in checks if c not in real_tool_names()]
    if bad:
        raise CaseError("first_checks must be real tool names; not recognised: " + ", ".join(str(b)[:30] for b in bad))
    if not isinstance(gist.get("signature") or [], list):
        raise CaseError("signature must be a list of keywords")


def add_case(state: dict, gist: dict, outcome: str, cause: str, scrub) -> dict:
    if outcome not in OUTCOMES or outcome == "discard":
        raise CaseError("outcome must be confirmed, probable or unresolved")
    validate_gist(gist)
    entries = [e for e in _load() if e["id"] not in _seed_ids()]
    e = {"id": f"C-{state['id']}", "kind": outcome, "title": scrub(clip(gist.get("title"), 120)),
         "signature": [scrub(clip(x, 40)).lower() for x in (gist.get("signature") or [])][:12],
         "reading": scrub(clip(gist.get("what_it_was") or gist.get("reading"))),
         "first_checks": [c for c in gist["first_checks"] if c in real_tool_names()][:6],
         "distinguish": scrub(clip(gist.get("how_to_tell"))),
         "dead_ends": [scrub(clip(x, 160)) for x in (gist.get("ruled_out") or [])][:6],
         "pm_cause": scrub(clip(cause)), "evidence_strength": scrub(clip(gist.get("evidence_strength"), 160)),
         "source": f"investigation {state['id']}", "date": datetime.now().strftime("%Y-%m-%d"), "rounds": state.get("rounds")}
    entries = [x for x in entries if x["id"] != e["id"]] + [e]
    _save(entries)
    return e


def summary_lines() -> list[str]:
    return [f"{e['id']:<28} {e['kind']:<14} {e['title'][:70]}" for e in _load()]
