"""Read-only tools. The model picks a tool and dates; it never supplies a URL, SQL, path or credential.

Every tool returns a small summary (counts, rates, timings). No phone numbers, message text or user rows leave this
file. All dates are UTC (YYYY-MM-DD).

Tools: fetch_delivery_logs, get_credit_balance, check_user_data, check_message_queue, check_numbers, check_code_api,
recent_code_changes.
"""
from __future__ import annotations

import base64
import csv
import glob
import hashlib
import json
import re
import statistics
import subprocess
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from . import config, db, reasons

UTC = config.UTC
MAX_DAYS = 14            # days per call
API_MAX_DAYS = 7         # the live log API serves only the last 7 days
csv.field_size_limit(10 ** 9)


class ToolError(Exception):
    """A clean error message with no URL and no credential in it."""


def now_utc() -> datetime:
    return config.now_utc()


def _days(start: str, end: str) -> list[date]:
    try:
        a, b = date.fromisoformat(start), date.fromisoformat(end)
    except (ValueError, TypeError):
        raise ToolError("dates must be YYYY-MM-DD (UTC)")
    if b < a:
        raise ToolError("end date is before start date")
    if (b - a).days + 1 > MAX_DAYS:
        raise ToolError(f"at most {MAX_DAYS} days per call")
    return [a + timedelta(days=i) for i in range((b - a).days + 1)]


def _ts(s) -> datetime | None:
    s = (s or "").strip()
    if not s:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            return datetime.strptime(s, fmt).replace(tzinfo=UTC)
        except ValueError:
            pass
    try:
        d = datetime.fromisoformat(s)
        return d.astimezone(UTC) if d.tzinfo else d.replace(tzinfo=UTC)
    except ValueError:
        return None


def _hash(n: str) -> str:
    return hashlib.sha256(("ii:" + str(n)).encode()).hexdigest()[:10]


def tel10(n: str) -> str:
    """Keyed fingerprint of a phone number (its last 10 digits), so 9000000001, 999000000001 and +99 9000000001 all
    match. The number itself is never kept; see config.local_key()."""
    d = re.sub(r"\D", "", n or "")
    return config.fingerprint("t10", d[-10:]) if len(d) >= 10 else ""


def _reason(e: Exception) -> str:
    r = getattr(e, "reason", e)
    return f"{type(e).__name__}: {type(r).__name__}" if r is not e else type(e).__name__


# ---------- log sources ----------

def _row(ts, status, reason, delivered, template, rid, recipient, route="", sender="") -> dict:
    recipient = recipient or ""
    sci = bool(re.search(r"\d\.\d+[eE]\+\d+", recipient))  # a spreadsheet re-saved the number as 9.99E+11
    return {"ts": ts, "status": status or "", "reason": (reason or "").strip(), "delivered": delivered,
            "template": template or "", "route": str(route or "").strip(), "sender": str(sender or "").strip(), "rid": (rid or "").strip(), "tel10": tel10(recipient),
            "who": tel10(recipient) or _hash(recipient), "digits": len(re.sub(r"\D", "", recipient)), "damaged": sci}


def _norm_api(r: dict) -> dict:
    return _row(_ts(r.get("sent_at")), r.get("status"), r.get("failure"), _ts(r.get("delivered_at")),
                r.get("template"), r.get("request_ref"), r.get("to"), r.get("route"), r.get("sender"))


def _norm_csv(r: dict) -> dict:
    d = _ts(f"{r.get('delivered_on', '')} {r.get('delivered_at', '')}")
    return _row(_ts(r.get("sent_at")), r.get("status"), r.get("failure"), d, r.get("template"),
                r.get("request_ref"), r.get("to"), r.get("route"), r.get("sender"))


def logs_dir() -> Path:
    p = Path(config.get("LOGS_DIR") or "data/exports").expanduser()
    return p if p.is_absolute() else config.ROOT / p


_FILE_CACHE: dict = {}


def _read_csv(path: str, kind: str) -> list[dict]:
    st = Path(path).stat()
    key = (path, st.st_mtime_ns, st.st_size, kind)
    if key not in _FILE_CACHE:
        out = []
        with open(path, newline="", encoding="utf-8-sig") as fh:
            rd = csv.DictReader(fh)
            head = rd.fieldnames or []
            if kind == "delivery" and "sent_at" in head and "status" in head:
                out = [_norm_csv(r) for r in rd]
            elif kind == "failed" and "ref" in head and "code" in head:
                out = [{"ts": _ts(r.get("at")), "code": (r.get("code") or "").strip(),
                        "rid": (r.get("ref") or "").strip()} for r in rd]
        _FILE_CACHE.clear() if len(_FILE_CACHE) > 20 else None
        _FILE_CACHE[key] = [r for r in out if r["ts"]]
    return _FILE_CACHE[key]


def _csv_files() -> list[str]:
    return sorted(glob.glob(str(logs_dir() / "**" / "*.csv"), recursive=True))


def _iter_csv(kind: str):
    for f in _csv_files():
        try:
            yield from _read_csv(f, kind)
        except (OSError, csv.Error, UnicodeDecodeError):
            continue


def _csv_coverage() -> list[str]:
    """Dates that have at least one row in the export folder (so 'no rows' can be told apart from 'no file')."""
    return sorted({r["ts"].date().isoformat() for r in _iter_csv("delivery")})


def _rows_from_csv(days: list[date]) -> list[dict]:
    out, seen = [], set()
    for n in _iter_csv("delivery"):
        if n["ts"].date() in days:
            if n["rid"]:  # overlapping exports contain the same request twice; count it once
                if n["rid"] in seen:
                    continue
                seen.add(n["rid"])
            out.append(n)
    return out


def _api_get(path: str, params: dict, timeout: int = 60):
    base, key = config.get("PROVIDER_API_URL").rstrip("/"), config.get("PROVIDER_API_KEY")
    if not base or not key:
        raise ToolError("PROVIDER_API_URL and PROVIDER_API_KEY must both be set")
    _check_url(base, "PROVIDER_API_URL")
    req = urllib.request.Request(f"{base}{path}?{urllib.parse.urlencode(params)}",
                                 headers={"Accept": "application/json", "Authorization": f"Bearer {key}"})
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=config.ssl_context()) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        e.close()
        raise ToolError(f"the provider log call failed (HTTP {e.code})")
    except Exception as e:  # never let a URL or key escape in an exception message
        raise ToolError(f"the provider log call failed ({_reason(e)})")


def _check_url(url: str, setting: str) -> None:
    u = urllib.parse.urlparse(url)
    if not (u.scheme == "https" or (u.scheme == "http" and u.hostname in ("127.0.0.1", "localhost"))):
        raise ToolError(f"{setting} must start with https:// (plain http is allowed only for localhost)")


def _api_rows_for(days: list[date]) -> tuple[list[dict], list[str]]:
    out, notes, seen = [], [], set()
    for d in days:  # one call per day
        body = _api_get("/v1/logs", {"date": d.isoformat()})
        rows = body.get("data") or []
        total = (body.get("metadata") or {}).get("total")
        if isinstance(total, int) and total != len(rows):
            notes.append(f"{d}: the API reported {total} rows but returned {len(rows)}; figures for this day are INCOMPLETE")
        for r in rows:
            n = _norm_api(r)
            if n["rid"] and n["rid"] in seen:  # the provider repeats callbacks; one request counts once
                continue
            seen.add(n["rid"])
            out.append(n)
    return out, notes


def logs_mode() -> str:
    mode = (config.get("LOGS_SOURCE") or "auto").lower()
    if mode not in ("auto", "csv", "api"):
        raise ToolError("LOGS_SOURCE must be auto, csv or api")
    return mode


def _api_ready() -> bool:
    return bool(config.get("PROVIDER_API_URL") and config.get("PROVIDER_API_KEY"))


def logs_status() -> str:
    mode = (config.get("LOGS_SOURCE") or "auto").lower()
    cov = _csv_coverage()
    folder = (f"export folder {logs_dir()} ({len(cov)} dates: {cov[0]} to {cov[-1]})" if cov
              else f"export folder {logs_dir()} (no exports found)")
    key = "live API configured" if _api_ready() else "live API NOT configured"
    if mode == "csv":
        return f"{folder} only"
    if mode == "api":
        return f"live provider API only, {key}"
    return f"auto: last {API_MAX_DAYS} days from the live provider API ({key}); older dates from the {folder}"


def collect_rows(days: list[date]) -> tuple[list[dict], list[str], str, list[str]]:
    """Normalised request rows for these UTC days: (rows, notes, source, days_without_data).
    The last 7 days come from the live API (if configured), older days from the export folder."""
    mode = logs_mode()
    today = now_utc().date()
    rows, notes = [], []
    if mode == "api":
        if len(days) > API_MAX_DAYS or (today - days[0]).days > API_MAX_DAYS:
            raise ToolError(f"the live log API serves only the last {API_MAX_DAYS} days; use exported files "
                            "for older dates (LOGS_SOURCE=auto or csv)")
        api_days, csv_days = days, []
        rows, notes = _api_rows_for(days)
    else:
        api_days = [d for d in days if mode == "auto" and _api_ready() and 0 <= (today - d).days <= API_MAX_DAYS]
        csv_days = [d for d in days if d not in api_days]
        if api_days:
            try:
                r, n = _api_rows_for(api_days)
                rows += r
                notes += n
            except ToolError as e:
                notes.append(f"{e}; those days were read from the export folder instead")
                csv_days = sorted(set(csv_days) | set(api_days))
                api_days = []
        if csv_days:
            rows += _rows_from_csv(csv_days)
    rows = [r for r in rows if r["ts"]]
    source = "+".join(x for x, used in (("provider_live_api", api_days), ("csv_export_folder", csv_days)) if used)
    have = {r["ts"].date() for r in rows}
    missing = [d.isoformat() for d in (csv_days if mode != "api" else api_days) if d not in have]
    if missing:
        cov = _csv_coverage()
        hint = (" Recent dates need PROVIDER_API_URL and PROVIDER_API_KEY to be read from the live API."
                if (mode == "auto" and not _api_ready() and any((today - d).days <= API_MAX_DAYS for d in csv_days)) else "")
        notes.append("No log rows for: " + ", ".join(missing) + ". The export folder holds data for: "
                     + (", ".join(cov) if cov else "nothing") + ". A missing export file is the likely reason; this is "
                     "NOT evidence that no codes were requested. A delivery-log export (CSV, UTC) covering these dates "
                     "would fill the gap." + hint)
    return rows, notes, source, missing


def find_requests(hashes: set[str], days: list[date]) -> tuple[list[dict], list[str], list[str]]:
    rows, notes, _, missing = collect_rows(days)
    return [r for r in rows if r.get("tel10") in hashes], notes, missing


def _has_failed_log() -> bool:
    for f in _csv_files():
        try:
            with open(f, newline="", encoding="utf-8-sig") as fh:
                head = next(csv.reader(fh), [])
        except (OSError, UnicodeDecodeError, csv.Error):
            continue
        if "ref" in head and "code" in head:
            return True
    return False


def _failed_call_log(days: list[date]) -> dict | None:
    """Counts of calls the API refused before they reached the provider (a separate log, if present)."""
    rows = [r for r in _iter_csv("failed") if r["ts"].date() in days]
    if not rows and not _has_failed_log():
        return None
    by_code = Counter(r["code"] for r in rows)
    per_day: dict[str, Counter] = {}
    for r in rows:
        per_day.setdefault(r["ts"].date().isoformat(), Counter())[r["code"]] += 1
    items = []
    for code, n in by_code.most_common(8):
        e = reasons.explain_error_code(code)
        items.append({"error_code": code, "count": n, "label": e["label"], "meaning": e["meaning"]})
    return {"total": len(rows), "by_error_code": items,
            "per_day": {d: dict(c) for d, c in sorted(per_day.items())},
            "note": "These calls were refused before submission, so they have no row in the delivery logs. "
                    "E110 (duplicate within 20 seconds) is normal at a low level."}


GROUP_MIN_REQUESTS = 20
GROUP_MAX = 6
_DIMENSIONS = ("route", "sender", "template")


def _is_failed(r: dict) -> bool:
    return r["status"].lower() != "delivered"


def _rate(failed: int, n: int) -> float:
    return round(100 * failed / n, 1) if n else 0.0


def _group_table(rows: list[dict], dim: str) -> list[dict]:
    """Groups of one dimension with enough requests, worst failure rate first. Counts and rates only."""
    tot, bad = Counter(r[dim] for r in rows), Counter(r[dim] for r in rows if _is_failed(r))
    groups = [{"value": v, "requests": n, "failed": bad.get(v, 0), "failure_rate_pct": _rate(bad.get(v, 0), n)}
              for v, n in tot.items() if v and n >= GROUP_MIN_REQUESTS]
    groups.sort(key=lambda g: (-g["failure_rate_pct"], -g["requests"], g["value"]))
    return groups[:GROUP_MAX]


def _concentration(day_rows: list[dict], dims: list[str]) -> dict | None:
    """Rule: on the latest day one group fails at 3x or more the rate of all other rows of that dimension, has at
    least 20 failed rows and makes up at least 60 percent of that day's failures. Deterministic; counts only."""
    day_failed = sum(1 for r in day_rows if _is_failed(r))
    best = None
    for dim in dims:
        rows = [r for r in day_rows if r[dim]]
        for v in sorted({r[dim] for r in rows}):
            grp = [r for r in rows if r[dim] == v]
            rest = [r for r in rows if r[dim] != v]
            f = sum(1 for r in grp if _is_failed(r))
            fo = sum(1 for r in rest if _is_failed(r))
            if not rest or f < 20 or not day_failed:
                continue
            rate, other = 100 * f / len(grp), 100 * fo / len(rest)
            share = 100 * f / day_failed
            if rate >= 3 * other and rate > 0 and share >= 60:
                cand = {"dimension": dim, "value": v, "failure_rate_pct": round(rate, 1), "other_rate_pct": round(other, 1),
                        "share_of_failures_pct": round(share, 1), "first_bad_hour_utc": None}
                # first hour h where the group's rows in hours h and h+1 together are at least 30 percent failed
                # with at least 5 requests (a two-hour window, because night hours hold very few requests)
                for h in sorted({r["ts"].hour for r in grp}):
                    win = [r for r in grp if r["ts"].hour in (h, h + 1)]
                    if len(win) >= 5 and 100 * sum(1 for r in win if _is_failed(r)) / len(win) >= 30:
                        cand["first_bad_hour_utc"] = h
                        break
                if best is None or (cand["failure_rate_pct"], cand["share_of_failures_pct"]) > \
                        (best["failure_rate_pct"], best["share_of_failures_pct"]):
                    best = cand
    return best


def _breakdowns(rows: list[dict], notes: list[str]) -> dict:
    last_day = max(r["ts"].date() for r in rows)
    day_rows = [r for r in rows if r["ts"].date() == last_day]
    dims = [d for d in _DIMENSIONS if any(r[d] for r in rows)]
    for d in _DIMENSIONS:
        if d not in dims:
            notes.append(f"The log source has no {d} field, so failures are not broken down by {d}.")
    by_hour = {}
    for r in day_rows:
        by_hour.setdefault(r["ts"].hour, []).append(r)
    return {
        "failures_by_group": {d: {"whole_window": _group_table(rows, d), "latest_day": _group_table(day_rows, d)} for d in dims},
        "latest_day_utc": last_day.isoformat(),
        "failures_by_hour_latest_day": [
            {"hour": h, "requests": len(v), "failed": sum(1 for r in v if _is_failed(r)),
             "failure_rate_pct": _rate(sum(1 for r in v if _is_failed(r)), len(v))} for h, v in sorted(by_hour.items())],
        "concentration": _concentration(day_rows, dims),
    }


def fetch_delivery_logs(start_date: str, end_date: str) -> dict:
    days = _days(start_date, end_date)
    rows, notes, source, missing = collect_rows(days)
    failed_calls = _failed_call_log(days) if logs_mode() != "api" else None
    if not rows:
        res = {"source": source, "days": [d.isoformat() for d in days], "total": 0, "days_without_data": missing,
               "notes": notes, "note": " ".join(notes) or
               "The live API returned no requests for these dates. If requests should exist, this itself is a finding."}
        if failed_calls:
            res["api_failed_calls"] = failed_calls
        return res
    failed = [r for r in rows if r["status"].lower() != "delivered"]
    delays = sorted((r["delivered"] - r["ts"]).total_seconds() for r in rows
                    if r["delivered"] and r["status"].lower() == "delivered")
    per_day = Counter(r["ts"].date().isoformat() for r in rows)
    fail_day = Counter(r["ts"].date().isoformat() for r in failed)
    res = {
        "source": source, "days": [d.isoformat() for d in days], "total": len(rows),
        "delivered": len(rows) - len(failed), "failed": len(failed),
        "failure_rate_pct": round(100 * len(failed) / len(rows), 1),
        "requests_per_day": dict(sorted(per_day.items())),
        "failure_rate_pct_per_day": {d: round(100 * fail_day.get(d, 0) / n, 1) for d, n in sorted(per_day.items())},
        "days_without_data": missing,
        **reasons.summarise(Counter(r["reason"] or "(none)" for r in failed).most_common(8)),
        "templates": Counter(r["template"] for r in rows).most_common(8),
        "distinct_recipients": len({r["who"] for r in rows}),
        "recipient_digit_lengths": dict(sorted(Counter(r["digits"] for r in rows).items())),
        "notes": notes,
    }
    res.update(_breakdowns(rows, notes))
    damaged = sum(1 for r in rows if r["damaged"])
    if damaged:
        res["data_quality"] = (f"{damaged} of {len(rows)} recipient values look re-saved by a spreadsheet (scientific notation). "
                               "Number-shape checks and repeat-request counts are unreliable for this export; ask for a fresh export.")
    win_min = config.get_int("CODE_EXPIRY_MIN", 10)
    by_who: dict[str, list] = {}
    for r in rows:
        if r.get("tel10"):
            by_who.setdefault(r["tel10"], []).append(r["ts"])
    rep_recipients = rep_requests = three_plus = 0
    rep_day = Counter()
    for stamps in by_who.values():
        stamps.sort()
        reps = [b for a, b in zip(stamps, stamps[1:]) if (b - a) <= timedelta(minutes=win_min)]
        if reps:
            rep_recipients += 1
            rep_requests += len(reps)
            for b in reps:
                rep_day[b.date().isoformat()] += 1
        if len(reps) >= 2:
            three_plus += 1
    res["repeat_requests"] = {
        "window_minutes": win_min, "recipients_with_a_repeat": rep_recipients, "repeat_requests": rep_requests,
        "recipients_with_two_or_more_repeats": three_plus,
        "share_of_requests_pct": round(100 * rep_requests / len(rows), 1),
        "share_of_requests_pct_per_day": {d: round(100 * rep_day.get(d, 0) / n, 1) for d, n in sorted(per_day.items())},
        "note": "A repeat is a request for the same number within the code validity window of the one before. "
                "A newer code replaces the older one, so repeats are one reason a code typed by the user can be 'invalid'. "
                "The logs cannot show which code the user typed."}
    if delays:
        res["delivery_delay_s"] = {"median": statistics.median(delays),
                                   "p90": delays[int(0.9 * (len(delays) - 1))], "max": delays[-1]}
    if len(days) <= 3:
        res["requests_per_hour_utc"] = dict(sorted(Counter(r["ts"].strftime("%m-%d %H") for r in rows).items()))
    if failed_calls:
        res["api_failed_calls"] = failed_calls
    return res


def get_credit_balance() -> dict:
    base, key = config.get("CREDIT_URL"), config.get("PROVIDER_API_KEY")
    if not base or not key:
        raise ToolError("CREDIT_URL and PROVIDER_API_KEY must both be set")
    _check_url(base, "CREDIT_URL")
    req = urllib.request.Request(base, headers={"Accept": "application/json",
                                                config.get("CREDIT_KEY_HEADER", "X-Api-Key"): key})
    try:
        with urllib.request.urlopen(req, timeout=30, context=config.ssl_context()) as resp:
            text = resp.read().decode("utf-8").strip().strip('"')
    except urllib.error.HTTPError as e:
        e.close()
        raise ToolError(f"the credit call failed (HTTP {e.code})")
    except Exception as e:
        raise ToolError(f"the credit call failed ({_reason(e)})")
    try:
        try:
            parsed = json.loads(text)
        except ValueError:
            parsed = text
        if isinstance(parsed, dict):
            parsed = parsed.get("balance")
        if isinstance(parsed, bool):
            raise ValueError
        bal = float(parsed)
    except (ValueError, TypeError):
        raise ToolError("the credit response was not a number or an object with a 'balance' number")
    cost = config.get_float("CREDIT_PER_REQUEST", 0.05) or 0.05
    return {"balance": bal, "requests_remaining_at_current_rate": int(bal / cost),
            "note": "Credit is shared by every message type on the account. This is the balance now; it does not show "
                    "the balance at an earlier time."}


# ---------- database checks ----------

def _db_ready() -> tuple[str, "db.Adapter"]:
    if not config.get_bool("DB_ENABLED"):
        raise ToolError("the database checks are switched off (DB_ENABLED is not true)")
    try:
        ad = db.adapter()
    except db.DbConfigError as e:
        raise ToolError(str(e))
    tz = config.get("DB_TIMESTAMP_TZ", "UTC").upper()
    if tz != "UTC":
        raise ToolError("set DB_TIMESTAMP_TZ to UTC (the only zone the tools read; convert in the view if needed)")
    if ad.kind != "sqlite":
        missing = [n for n in ("DB_HOST", "DB_NAME", "DB_USER", "DB_PASSWORD") if not config.get(n)]
        if missing:
            raise ToolError("not set: " + ", ".join(missing))
    return tz, ad


def _db_naive(dt_utc: datetime) -> datetime:
    return dt_utc.astimezone(timezone.utc).replace(tzinfo=None)


def _db_aware(dt: datetime) -> datetime:
    return dt.replace(tzinfo=UTC)


def _to_utc(dt):
    dt = db.to_dt(dt)
    return None if dt is None else _db_aware(dt).strftime("%Y-%m-%d %H:%M")


def _connect(ad):
    try:
        return ad.connect()
    except db.DbConfigError as e:
        raise ToolError(str(e))
    except Exception as e:
        raise ToolError("database check failed: " + ad.error(e))


def check_user_data(start_date: str, end_date: str) -> dict:
    """One fixed aggregate statement per day. Counts only; no user rows."""
    tz, ad = _db_ready()
    days = _days(start_date, end_date)
    try:
        sql = db.build_sql(ad)
    except db.DbConfigError as e:
        raise ToolError(str(e))
    cn = _connect(ad)
    out = []
    try:
        cur = cn.cursor()
        for d in days:
            lo = datetime(d.year, d.month, d.day, tzinfo=UTC)
            hi = lo + timedelta(days=1)
            db.execute(cur, ad, sql, (db.param(ad, _db_naive(lo)), db.param(ad, _db_naive(hi))))
            n, loc, dial = cur.fetchone()
            out.append({"created_date_utc": d.isoformat(), "new_users": int(n or 0),
                        "locale_empty": int(loc or 0), "dial_code_empty": int(dial or 0)})
    except db.DbConfigError as e:
        raise ToolError(str(e))
    except Exception as e:
        raise ToolError("database check failed: " + ad.error(e))
    finally:
        try:
            cn.close()
        except Exception:
            pass
    res = {"database": ad.kind, "timestamps_stored_as": tz, "days": out,
           "limits": "Counts show the data as it is NOW. Records edited by hand later can hide earlier problems; counts here "
                     "are current, not historical. A zero here for a past day is NOT proof the fault did not occur."}
    if config.get_bool("DB_REPLICA"):
        res["replica"] = "connected to a read replica (DB_REPLICA=true): counts may trail the live database by minutes"
    return res


def recent_code_changes(since_date: str, until_date: str) -> dict:
    paths = [p.strip() for p in config.get("REPO_PATHS").split(",") if p.strip()]
    if not paths:
        raise ToolError("REPO_PATHS is not set")
    _days(since_date, until_date)
    repos = {}
    for p in paths:
        pp = Path(p).expanduser()
        if not pp.is_absolute():
            pp = config.ROOT / pp
        if not (pp / ".git").exists():
            repos[pp.name] = {"error": "not a git repository"}
            continue
        try:
            r = subprocess.run(["git", "-C", str(pp), "log", f"--since={since_date} 00:00 +0000",
                                f"--until={until_date} 23:59 +0000", "--max-count=30", "--date=iso",
                                "--format=@@%h|%ad|%an|%s", "--name-only"], capture_output=True, text=True, timeout=30)
        except (OSError, subprocess.TimeoutExpired):
            repos[pp.name] = {"error": "git could not be run"}
            continue
        commits, cur = [], None
        for line in r.stdout.splitlines():
            if line.startswith("@@"):
                h, d, a, s = line[2:].split("|", 3)
                cur = {"commit": h, "date": d, "author": a, "subject": s, "files": []}
                commits.append(cur)
            elif line.strip() and cur is not None and len(cur["files"]) < 15:
                cur["files"].append(line.strip())
        repos[pp.name] = {"commits": commits}
    return {"repos": repos, "note": "Commit subjects and file names only; code is not read, so a change that looks harmless "
                                    "by its subject can still be the cause."}


# ---------- specific phone numbers (the model sees aliases only) ----------

CASE: dict = {}          # alias -> {"hmac": fingerprint, "hint": last 2 digits}; saved in the session
_PLAIN: dict = {}        # alias -> 10-digit number; this process only, never written anywhere
MAX_CASE_NUMBERS = 20


def set_case(case: dict, keep_plain: bool = True) -> None:
    CASE.clear()
    CASE.update(case or {})
    for a in list(_PLAIN):
        if not keep_plain or a not in CASE:
            del _PLAIN[a]


def remember_plain(alias: str, digits: str) -> None:
    _PLAIN[alias] = digits


def _lookup_accounts(plain: dict) -> dict:
    """One user-record summary per number (flags and timestamps only). Needs the numbers in memory."""
    _, ad = _db_ready()
    try:
        user_sql, dev_sql = db.build_user_sql(ad)
    except db.DbConfigError as e:
        raise ToolError(str(e))
    cn = _connect(ad)
    out = {}
    try:
        cur = cn.cursor()
        for alias, number in plain.items():
            db.execute(cur, ad, user_sql, (number,))
            n, loc0, dial0, act, pc, created, updated = cur.fetchone()
            rec = {"user_records_found": int(n or 0)}
            if n:
                rec.update({"locale_empty": bool(loc0), "dial_code_empty": bool(dial0),
                            "is_active": None if act is None else bool(act),
                            "phone_confirmed": None if pc is None else bool(pc),
                            "created_utc": _to_utc(created), "updated_utc": _to_utc(updated)})
                if dev_sql:
                    db.execute(cur, ad, dev_sql, (number,))
                    dn, exp, login = cur.fetchone()
                    rec.update({"devices": int(dn or 0), "latest_code_expiry_utc": _to_utc(exp),
                                "latest_login_utc": _to_utc(login)})
            out[alias] = rec
    except db.DbConfigError as e:
        raise ToolError(str(e))
    except Exception as e:
        raise ToolError("database check failed: " + ad.error(e))
    finally:
        try:
            cn.close()
        except Exception:
            pass
    return out


def check_numbers(start_date: str, end_date: str) -> dict:
    """Look up the numbers the PM registered (aliases N1, N2 ...) in the delivery logs and, if possible, the user table."""
    if not CASE:
        raise ToolError("no phone numbers were given for this investigation. The PM can add them with --number, "
                        "--numbers-file or --prompt-numbers (the AI only ever sees aliases such as N1)")
    days = _days(start_date, end_date)
    want = {v["hmac"]: alias for alias, v in CASE.items()}
    rows, notes, missing = find_requests(set(want), days)
    per = {alias: [] for alias in CASE}
    for r in sorted(rows, key=lambda x: x["ts"]):
        per[want[r["tel10"]]].append(r)
    out_numbers, by_cat = [], Counter()
    for alias in CASE:
        rs = per[alias]
        failed = [r for r in rs if r["status"].lower() != "delivered"]
        rapid = sum(1 for a, b in zip(rs, rs[1:]) if (b["ts"] - a["ts"]).total_seconds() <= 120)
        timeline = []
        for r in rs[-15:]:
            e = reasons.explain(r["reason"]) if r["status"].lower() != "delivered" else None
            timeline.append({"time_utc": r["ts"].strftime("%m-%d %H:%M:%S"), "status": r["status"],
                             **({"reason": e["reason"], "meaning": e["meaning"], "category": e["category_label"]} if e else {}),
                             **({"delay_s": int((r["delivered"] - r["ts"]).total_seconds())}
                                if r["delivered"] and not e else {})})
        for r in failed:
            by_cat[reasons.explain(r["reason"])["category_label"]] += 1
        out_numbers.append({"alias": alias, "requests": len(rs), "delivered": len(rs) - len(failed), "failed": len(failed),
                            "requests_within_2_min_of_previous": rapid, "latest_requests": timeline})
    res = {"days": [d.isoformat() for d in days], "numbers": out_numbers,
           "summary": {"numbers_checked": len(CASE),
                       "numbers_with_no_request_in_logs": sum(1 for n in out_numbers if not n["requests"]),
                       "numbers_with_a_failure": sum(1 for n in out_numbers if n["failed"]),
                       "failures_by_category": dict(by_cat)},
           "days_without_data": missing, "notes": notes}
    if missing:
        res["note"] = ("Dates without log data cannot show requests. A number with no request on those dates is NOT "
                       "evidence that none was made.")
    try:
        plain = {a: n for a, n in _PLAIN.items() if a in CASE}
        if not plain:
            res["user_records"] = ("not checked: numbers are kept only in memory for the run that received them. "
                                   "Re-supply them with --number or --prompt-numbers to check the user records.")
        else:
            accts = _lookup_accounts(plain)
            res["user_records"] = accts
            skipped = [a for a in CASE if a not in accts]
            if skipped:
                res["user_records_not_checked"] = skipped
    except ToolError as e:
        res["user_records"] = f"not checked: {e}"
    return res


# ---------- direct check of the verification API (the probe) ----------

PROBE = {"count": 0, "last": 0.0}
_PROBE_LOCK = threading.Lock()
NEEDS_CONFIRM = {"check_code_api": "This check calls your verification API once and sends ONE real verification code to "
                                   "your own test number (it uses a small amount of credit)."}


def _jwt_expiry(token: str):
    try:
        p = token.split(".")[1]
        return json.loads(base64.urlsafe_b64decode(p + "=" * (-len(p) % 4))).get("exp")
    except Exception:
        return None


def _probe_body(phone: str) -> dict:
    vals = {"country_prefix": config.get("PROBE_COUNTRY_PREFIX", "+99"), "phone": phone,
            "client": config.get("PROBE_CLIENT", "incident-probe")}
    tmpl = config.get("CODE_API_BODY_TEMPLATE")
    if tmpl:
        try:
            body = json.loads(tmpl)
        except ValueError:
            raise ToolError("CODE_API_BODY_TEMPLATE is not valid JSON")
        return {k: (re.sub(r"\$\{(\w+)\}", lambda m: vals.get(m.group(1), m.group(0)), v) if isinstance(v, str) else v)
                for k, v in body.items()}
    return {"country_prefix": vals["country_prefix"], "phone": vals["phone"], "client": vals["client"]}


def check_code_api() -> dict:
    """Call the verification API once for the PM's own test number and report what happened, then look for the request
    in the provider's log. The model passes no parameters: URL, token and number all come from settings."""
    if not config.get_bool("PROBE_ENABLED"):
        raise ToolError("the API check is switched off (PROBE_ENABLED is not true)")
    url, token = config.get("CODE_API_URL"), config.get("CODE_API_TOKEN")  # the token is optional
    phone = re.sub(r"\D", "", config.get("PROBE_PHONE"))[-10:]
    missing = [n for n, v in (("CODE_API_URL", url), ("PROBE_PHONE", phone)) if not v]
    if missing:
        raise ToolError("not set: " + ", ".join(missing))
    u = urllib.parse.urlparse(url)
    if not (u.scheme == "https" or (u.scheme == "http" and u.hostname in ("127.0.0.1", "localhost"))):
        raise ToolError("CODE_API_URL must start with https:// (plain http is allowed only for localhost)")
    if len(phone) != 10:
        raise ToolError("PROBE_PHONE must be a number you own, with at least 10 digits")
    exp = _jwt_expiry(token) if token else None
    if exp and exp < time.time():
        when = datetime.fromtimestamp(exp, UTC).strftime("%Y-%m-%d %H:%M UTC")
        raise ToolError(f"CODE_API_TOKEN expired at {when}. Put a fresh token in .env and run again")
    with _PROBE_LOCK:
        if PROBE["count"] >= config.get_int("PROBE_MAX_PER_RUN", 2):
            raise ToolError("the API check already ran the maximum number of times in this session")
        wait = config.get_int("PROBE_MIN_GAP_S", 15) - (time.time() - PROBE["last"])
        if wait > 0:
            raise ToolError(f"wait {int(wait) + 1}s before another API check (the provider drops a repeat request to "
                            "the same number within 20 seconds)")
        PROBE["count"] += 1
        PROBE["last"] = time.time()
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=json.dumps(_probe_body(phone)).encode(), method="POST", headers=headers)
    started_wall, t0 = now_utc(), time.perf_counter()
    res = {"called_at_utc": started_wall.strftime("%Y-%m-%d %H:%M:%S"), "sent_to": "the PM's test number (not shown)"}
    timeout = config.get_int("PROBE_TIMEOUT_S", 30)
    text, status = "", None
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=config.ssl_context()) as resp:
            status, text = resp.status, resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        status, text = e.code, e.read().decode("utf-8", "replace")
        e.close()
    except Exception as e:
        res["elapsed_ms"] = int((time.perf_counter() - t0) * 1000)
        slow = "timed out" in str(getattr(e, "reason", e)).lower() or "timeout" in str(getattr(e, "reason", e)).lower() \
            or isinstance(e, TimeoutError) or isinstance(getattr(e, "reason", None), TimeoutError)
        res["result"] = "no_answer" if slow else "network_error"
        res["detail"] = f"no answer within {timeout}s" if slow else f"could not connect ({_reason(e)})"
        res["reading"] = ("The API did not answer in time. A client that waits for a long default timeout would show the "
                          "user a spinner and no code." if slow else
                          "The API could not be reached from this machine (VPN, URL or network). That says nothing "
                          "about the API itself.")
        return res
    res["elapsed_ms"] = int((time.perf_counter() - t0) * 1000)
    res["http_status"] = status
    msg, code_present = "", False
    try:
        j = json.loads(text)
        msg = str(j.get("message", ""))[:160] if isinstance(j, dict) else ""
        code_present = bool(isinstance(j, dict) and str(j.get("code", "")).strip())
    except ValueError:
        msg = re.sub(r"\s+", " ", text)[:120]
    res["response_message"] = config.redact(msg)
    if code_present:  # the value itself is deliberately not recorded
        res["SECURITY_FINDING"] = ("The API response contains a verification code value. It was not recorded here. "
                                   "A code should never be returned to the caller.")
    expect = config.get("PROBE_EXPECT_TEXT", "Request accepted")
    if status in (401, 403):
        res["result"] = "auth_rejected"
        res["reading"] = ("The API rejected the request" + (" and the token (expired or invalid). Refresh CODE_API_TOKEN; "
                          "this is not an outage." if token else " because it sent no token. If this endpoint is meant to "
                          "be called before login, that is itself a finding; otherwise set CODE_API_TOKEN."))
    elif status and status >= 500:
        res["result"] = "server_error"
        res["reading"] = ("The API itself failed. Users hitting it would get no code and nothing would reach the provider. "
                          "The cause is in the API server's own log, which no tool here can read.")
    elif status and status >= 400:
        res["result"] = "request_rejected"
        res["reading"] = "The API refused this request. Compare the message with what the app sends."
    elif expect.lower() not in msg.lower():
        res["result"] = "unexpected_response"
        res["reading"] = f"HTTP {status} but the message is not the usual success text."
    else:
        res["result"] = "ok_but_slow" if res["elapsed_ms"] > config.get_int("PROBE_SLOW_MS", 5000) else "ok"
        res["reading"] = ("The API answered with its usual success message. This alone does NOT prove a message was "
                          "requested from the provider: see provider_log.")
    if res["result"] in ("ok", "ok_but_slow", "unexpected_response"):
        res["provider_log"] = _probe_provider_check(phone, started_wall)
    else:
        res["provider_log"] = {"checked": False, "why": "the API did not report success, so no request is expected at the provider"}
    return res


def _probe_provider_check(phone: str, started: datetime) -> dict:
    """Did the provider's live log show a request for the test number after the call? The log lags, so we poll for a
    while and, if nothing shows, say 'not seen yet' rather than hinting at a fault."""
    if not _api_ready() or (config.get("LOGS_SOURCE") or "auto").lower() == "csv":
        return {"checked": False, "why": "needs PROVIDER_API_URL, PROVIDER_API_KEY and the live log API (LOGS_SOURCE auto or api)"}
    h, waited, deadline = tel10(phone), 0.0, config.get_float("PROBE_LOG_WAIT_S", 60)
    poll = max(config.get_float("PROBE_LOG_POLL_S", 5), 0.05)
    since = started - timedelta(seconds=10)
    while True:
        try:
            rows, _, _ = find_requests({h}, [started.date()])
            hits = [r for r in rows if r["ts"] >= since]
            if hits:
                r = sorted(hits, key=lambda x: x["ts"])[-1]
                e = reasons.explain(r["reason"]) if r["status"].lower() != "delivered" else None
                out = {"checked": True, "row_seen": True, "provider_status": r["status"], "waited_s": round(waited, 1)}
                if r["delivered"]:
                    out["delivery_delay_s"] = int((r["delivered"] - r["ts"]).total_seconds())
                if e:
                    out["failure"] = f"{e['reason']}: {e['meaning']}"
                return out
        except ToolError as ex:
            return {"checked": False, "why": str(ex)}
        if waited >= deadline:
            break
        time.sleep(poll)
        waited += poll
    return {"checked": True, "row_seen": False, "waited_s": round(waited, 1),
            "reading": f"Not seen yet in the provider log after {int(waited)}s. The live log lags, so this is NOT a sign of a "
                       "fault. Do not conclude a break between the API and the provider from this alone. Check again a few "
                       "minutes later (fetch_delivery_logs or another API check) before suspecting one."}


# ---------- the message queue ----------

QUEUE_KNOWN_STATUSES = {"PENDING", "SENDING", "SENT", "FAILED", "ON_HOLD", "BLOCKED"}


def check_message_queue(start_date: str, end_date: str) -> dict:
    """Aggregate view of the queue that holds outgoing messages. Counts and timings only."""
    tz, ad = _db_ready()
    days = _days(start_date, end_date)
    try:
        waiting_sql, daily_sql, wait_sql, newest_sql = db.build_queue_sql(ad)
        fresh_sql = db.build_freshness_sql(ad)
    except db.DbConfigError as e:
        raise ToolError(str(e))
    cn = _connect(ad)
    now = now_utc()
    exp_min = config.get_int("CODE_EXPIRY_MIN", 10)
    lo = datetime(days[0].year, days[0].month, days[0].day, tzinfo=UTC)
    hi = datetime(days[-1].year, days[-1].month, days[-1].day, tzinfo=UTC) + timedelta(days=1)
    P = lambda dt: db.param(ad, _db_naive(dt))
    fresh = None
    try:
        cur = cn.cursor()
        db.execute(cur, ad, waiting_sql, (P(now - timedelta(minutes=exp_min)),))
        waiting = cur.fetchall()
        db.execute(cur, ad, daily_sql, (P(lo), P(hi)))
        daily = cur.fetchall()
        db.execute(cur, ad, wait_sql, (P(lo), P(hi)))
        waits = cur.fetchall()
        db.execute(cur, ad, newest_sql, ())
        newest_row = cur.fetchall()
        if config.get_bool("DB_REPLICA"):
            try:  # a busy table that is current to the minute tells us how far behind this replica is
                db.execute(cur, ad, fresh_sql, ())
                fresh = db.to_dt(cur.fetchall()[0][0])
            except Exception:
                fresh = None
    except db.DbConfigError as e:
        raise ToolError(str(e))
    except Exception as e:
        raise ToolError("database check failed: " + ad.error(e))
    finally:
        try:
            cn.close()
        except Exception:
            pass

    now_rows, waiting_by_ch = [], {}
    for ch, st, n, oldest, over, untouched in waiting:
        rec = {"channel": str(ch), "status": st, "rows": int(n or 0), "never_touched": int(untouched or 0),
               f"older_than_{exp_min}_min": int(over or 0)}
        o = db.to_dt(oldest)
        if o:
            o = _db_aware(o)
            rec["oldest_created_utc"] = o.strftime("%Y-%m-%d %H:%M")
            rec["oldest_age_minutes"] = int((now - o).total_seconds() // 60)
        now_rows.append(rec)
        if st == "PENDING":
            waiting_by_ch[str(ch)] = waiting_by_ch.get(str(ch), 0) + int(n or 0)
    batch, tick = max(config.get_int("QUEUE_BATCH_SIZE", 20), 1), max(config.get_int("QUEUE_TICK_S", 30), 1)
    per_min = batch * 60 / tick
    drain = {ch: round(n / per_min, 1) for ch, n in waiting_by_ch.items()}

    by_day, statuses = {}, Counter()
    for dte, ch, st, n in daily:
        by_day.setdefault(str(dte), {}).setdefault(str(ch), {})[st] = int(n or 0)
        statuses[st] += int(n or 0)
    unusual = {st: n for st, n in statuses.items() if st not in QUEUE_KNOWN_STATUSES}

    wait_out = {}
    for ch, total, a, b, c, d_, e_ in waits:
        wait_out[str(ch)] = {"sent_rows": int(total or 0), "under_30_s": int(a or 0), "30_s_to_2_min": int(b or 0),
                             "2_to_10_min": int(c or 0), "10_to_30_min": int(d_ or 0), "over_30_min": int(e_ or 0)}
    res = {"as_of_utc": now.strftime("%Y-%m-%d %H:%M"), "timestamps_stored_as": tz,
           "window": [d.isoformat() for d in (days[0], days[-1])],
           "waiting_now": sorted(now_rows, key=lambda r: (r["channel"], r["status"])),
           "estimated_minutes_to_clear_waiting": drain,
           "estimate_basis": f"mock defaults: {batch} rows per channel every {tick}s ({per_min:.0f} rows a minute), "
                             "one worker. The real rate can be lower; verify QUEUE_BATCH_SIZE and QUEUE_TICK_S.",
           "code_validity_minutes_assumed": exp_min, "rows_by_created_day": by_day,
           "unusual_statuses_in_window": unusual, "wait_before_sent": wait_out,
           "limits": ["Counts only: the body and destination columns are never read, so verification-code rows cannot be "
                      "told apart from other text messages here.",
                      "SENT means the worker handed the row to the provider, not that the user received it; check "
                      "delivery in the provider logs.",
                      "Wait is last-update minus created.",
                      "This is the current state of the table. Records edited by hand later can hide earlier problems; counts here are current, not historical."]}
    newest = db.to_dt(newest_row[0][0]) if newest_row and newest_row[0] else None
    if newest is None:
        res["newest_row_recent"] = False
        res["queue_note"] = "The queue table has no rows at all. An empty or old queue is not evidence of health: do not describe the queue as healthy."
    else:
        n_utc = _db_aware(newest)
        res["newest_row_created_utc"] = n_utc.strftime("%Y-%m-%d %H:%M")
        if n_utc < lo:
            res["newest_row_recent"] = False
            res["queue_note"] = (f"The newest row in this queue table was created {n_utc.strftime('%Y-%m-%d %H:%M')} UTC, "
                                    "BEFORE the window asked about, so it holds nothing for these dates. An empty or old "
                                    "queue is NOT evidence of health: do not describe the queue as healthy.")
        else:
            res["newest_row_recent"] = True
    if config.get_bool("DB_REPLICA"):
        rep = {"connected_to": "a read replica (DB_REPLICA=true)",
               "warning": "Replica data can trail the live database by seconds to minutes or more. Newest rows may be "
                          "missing, so the queue can look smaller, and a row can look stuck when the live database has "
                          "already moved it on."}
        if fresh is not None:
            lag = max(0, int((now - _db_aware(fresh)).total_seconds() // 60))
            rep["freshest_signup_minutes_ago"] = lag
            rep["freshness_reading"] = (f"The newest user record here is {lag} minute(s) old. If sign-ups are frequent, that is "
                                        "roughly how far this replica trails the live database (an upper bound only when "
                                        "sign-ups are frequent).")
        else:
            rep["freshness_reading"] = "Replica lag could not be measured. Treat counts as 'at least as of some minutes ago'."
        res["replica"] = rep
    if unusual:
        res["unusual_statuses_note"] = ("Statuses outside the documented set usually mean rows were closed or re-labelled by "
                                        "hand. They show rows were closed manually, not why.")
    readings = []
    old_q = sum(r.get(f"older_than_{exp_min}_min", 0) for r in now_rows if r["status"] == "PENDING")
    if old_q:
        oldest = max((r.get("oldest_age_minutes", 0) for r in now_rows if r["status"] == "PENDING"), default=0)
        readings.append(f"{old_q} rows are still PENDING after more than {exp_min} minutes (oldest about {oldest} minutes). "
                        "If any are verification codes, they would already have expired before sending.")
        if drain and max(drain.values()) < exp_min and oldest > exp_min:
            readings.append("The documented rate would clear the queue within minutes, yet rows are older than that: the worker "
                            "is probably slower than documented, or it is not running. This tool cannot tell which.")
    stuck = sum(r["rows"] for r in now_rows if r["status"] == "SENDING" and r.get(f"older_than_{exp_min}_min", 0))
    if stuck:
        readings.append(f"{stuck} rows have been SENDING for longer than {exp_min} minutes. A row is normally in SENDING "
                        "for seconds. Rows waiting this long are usually reset by a scheduled job or a restart; whether such a "
                        "job exists and is running cannot be seen by any tool here. Ask whoever runs the database (the DBA).")
    slow = sum(w["2_to_10_min"] + w["10_to_30_min"] + w["over_30_min"] for w in wait_out.values())
    tot_done = sum(w["sent_rows"] for w in wait_out.values())
    if tot_done and slow / tot_done > 0.1:
        readings.append(f"{slow} of {tot_done} sent rows waited 2 minutes or more before being sent "
                        f"({round(100 * slow / tot_done)}%).")
    if readings:
        res["reading"] = " ".join(readings)
    return res


# ---------- registry ----------

TOOLS = {
    "fetch_delivery_logs": (fetch_delivery_logs,
        "Summary of the verification-code delivery logs (counts, failure reasons with plain meanings and who fixes them, delivery delay, "
        "repeat requests, per-day and per-hour volume, failures by route, sender and template, failures by hour on the latest day, "
        "and a rule-based 'concentration' when one route, sender or template accounts for most failures on the latest day) for UTC dates start_date..end_date (max 14 days). The last 7 days come "
        "from the live provider API; older dates come from exported CSV files. days_without_data lists dates with no data at all: "
        "that means a missing export, not zero traffic. Missing requests are a finding too: compare volume across days.",
        {"start_date": "YYYY-MM-DD", "end_date": "YYYY-MM-DD"}),
    "get_credit_balance": (get_credit_balance, "Current credit balance of the messaging provider account.", {}),
    "check_user_data": (check_user_data,
        "Counts of users created per UTC day, and how many have an empty locale or an empty dial code. Use when codes seem "
        "never requested or numbers look wrong. Reads current data only.",
        {"start_date": "YYYY-MM-DD", "end_date": "YYYY-MM-DD"}),
    "check_message_queue": (check_message_queue,
        "Aggregate view of the outgoing message queue: how many rows are waiting now and for how long (per channel), how long "
        "sent rows waited before being sent, rows per day and status, and unusual statuses left by manual clean-ups. Use "
        "when codes arrive late or never, provider volume is lower than expected, or the PM mentions a queue. "
        "Counts only; dates are UTC, "
        "max 14 days.",
        {"start_date": "YYYY-MM-DD", "end_date": "YYYY-MM-DD"}),
    "check_numbers": (check_numbers,
        "Look up the specific phone numbers the PM supplied, shown to you only as aliases N1, N2 ... (you never see numbers): "
        "their requests, statuses, failure reasons with meanings, delays, rapid retries, and (if the PM re-supplied them this "
        "run) a user-record summary. Use when the PM names specific users. Dates are UTC, max 14 days.",
        {"start_date": "YYYY-MM-DD", "end_date": "YYYY-MM-DD"}),
    "check_code_api": (check_code_api,
        "Call the verification-code API once with the PM's own test number and see how it answers: status, time taken, message, "
        "and whether the provider's log then shows a request. It sends ONE real message to the PM's test number and needs the "
        "PM's approval. Use it when requests may be failing before they reach the provider (volume drop with no failures), or to "
        "test the API directly. Takes no parameters.",
        {}),
    "recent_code_changes": (recent_code_changes,
        "Commits in the configured repositories between two UTC dates (subjects and file names only).",
        {"since_date": "YYYY-MM-DD", "until_date": "YYYY-MM-DD"}),
}


# ---------- which tools can run right now ----------

ACTIVE: set | None = None      # None = all tools are offered to the model


def set_active(names) -> None:
    global ACTIVE
    ACTIVE = None if names is None else set(names)


def availability() -> dict:
    """tool name -> None if it can run now, else a one-line reason (with who can fix it). Cheap: settings plus one
    3-second connection test."""
    out = {}
    try:
        mode = logs_mode()
    except ToolError as e:
        mode = "auto"
        out["fetch_delivery_logs"] = str(e)
    if "fetch_delivery_logs" not in out:
        has_csv, api = bool(_csv_coverage()), _api_ready()
        out["fetch_delivery_logs"] = None if (has_csv or (api and mode != "csv")) else \
            "no PROVIDER_API_URL/PROVIDER_API_KEY and no exported delivery logs in LOGS_DIR (the PM can export a CSV from the provider's console)"
    out["get_credit_balance"] = None if (config.get("CREDIT_URL") and config.get("PROVIDER_API_KEY")) else \
        "CREDIT_URL or PROVIDER_API_KEY is not set (whoever owns the provider account can supply them)"
    out["recent_code_changes"] = None if config.get("REPO_PATHS") else "REPO_PATHS is not set (engineering can name the repositories)"
    if not config.get_bool("DB_ENABLED"):
        db_reason = "the database checks are switched off (DB_ENABLED is not true; the DBA must provide a read-only login)"
    else:
        try:
            ad = db.adapter()
            missing = [] if ad.kind == "sqlite" else [n for n in ("DB_HOST", "DB_NAME", "DB_USER", "DB_PASSWORD") if not config.get(n)]
        except db.DbConfigError as e:
            ad, missing, db_reason = None, [], str(e)
        else:
            db_reason = ("not set: " + ", ".join(missing) + " (the DBA can provide a read-only login)") if missing else db.reachable_reason()
    out["check_user_data"] = db_reason
    out["check_message_queue"] = db_reason
    out["check_numbers"] = None if CASE else "the PM gave no phone numbers (use --number, --numbers-file or --prompt-numbers)"
    if not config.get_bool("PROBE_ENABLED"):
        out["check_code_api"] = "the API check is switched off (PROBE_ENABLED is not true; the PM can turn it on and approve each run)"
    else:
        pm = [n for n in ("CODE_API_URL", "PROBE_PHONE") if not config.get(n)]
        out["check_code_api"] = ("not set: " + ", ".join(pm)) if pm else None
    return {k: v for k, v in out.items() if k in TOOLS}


def schemas() -> list[dict]:
    out = []
    for name, (_, desc, params) in TOOLS.items():
        if ACTIVE is not None and name not in ACTIVE:
            continue
        out.append({"name": name, "description": desc, "input_schema": {
            "type": "object", "properties": {k: {"type": "string", "description": v} for k, v in params.items()},
            "required": list(params)}})
    return out
