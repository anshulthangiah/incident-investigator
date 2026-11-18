"""Build the per-scenario SQLite file mock.db: tables accounts, sessions and outbox.

All rows are invented and deterministic. The data is consistent with the scenario: the same requests that appear in
the provider logs appear here as queue rows, and the user counts match users_summary.json.

Columns (invented):
  accounts  id, login_ref, language, country_prefix, is_active, phone_verified, created_at, updated_at
  sessions  id, account_id, code_valid_until, last_seen_at, updated_at
  outbox    id, kind, state, created_at, updated_at, body, destination
            (body and destination are present but never read by any tool)
Timestamps are UTC, text, 'YYYY-MM-DD HH:MM:SS'.
"""
from __future__ import annotations

import random
import sqlite3
import zlib
from datetime import datetime, timedelta, timezone
from pathlib import Path

TS = "%Y-%m-%d %H:%M:%S"

SCHEMA = """
CREATE TABLE accounts (id INTEGER PRIMARY KEY, login_ref TEXT NOT NULL, language TEXT, country_prefix TEXT,
                       is_active INTEGER, phone_verified INTEGER, created_at TEXT, updated_at TEXT);
CREATE TABLE sessions (id INTEGER PRIMARY KEY, account_id INTEGER NOT NULL, code_valid_until TEXT, last_seen_at TEXT,
                       updated_at TEXT);
CREATE TABLE outbox (id INTEGER PRIMARY KEY, kind TEXT NOT NULL, state TEXT NOT NULL, created_at TEXT,
                     updated_at TEXT, body TEXT, destination TEXT);
CREATE INDEX ix_outbox_created ON outbox (created_at);
"""


def national(i: int) -> str:
    """10-digit national number of invented user i (the full number is '99' + this)."""
    return "9000" + f"{i:06d}"


def _fmt(dt: datetime | None) -> str | None:
    return dt.astimezone(timezone.utc).strftime(TS) if dt else None


def build_mock_db(path: Path, sc: dict, reqs: list[dict], user_days: list[dict], seed: int) -> dict:
    from mock import generate as G  # late import: generate imports this module lazily too
    rng = random.Random(seed + 7)
    gen = sc["generate"]
    if path.exists():
        path.unlink()
    cn = sqlite3.connect(path)
    cn.executescript(SCHEMA)
    now = G.U(G.NOW)

    # ---- accounts: the pool that makes requests, then new users per creation day ----
    last_req: dict[int, datetime] = {}
    for r in reqs:
        if r["channel"] in ("delivery", "never_sent", "api_failed"):
            t = r["ts"]
            if r["user"] not in last_req or t > last_req[r["user"]]:
                last_req[r["user"]] = t
    users, devices = [], []
    for u in range(G.USER_POOL):
        created = G.BASELINE_START - timedelta(days=rng.randint(10, 120), hours=rng.randint(0, 23))
        users.append((u + 1, national(u), rng.choice(["en", "en", "fr", "es", "de", "pt"]), "+99", 1, 1 if rng.random() < 0.97 else 0,
                      _fmt(created), _fmt(created + timedelta(days=rng.randint(0, 9)))))
    planted_id = G.USER_POOL + 1
    users.append((planted_id, national(12345), "en", "+99", 1, 1, _fmt(G.BASELINE_START - timedelta(days=30)),
                  _fmt(G.BASELINE_START - timedelta(days=20))))
    uid = planted_id + 1
    new_ids: dict[str, list[int]] = {}
    for row in user_days:
        day = datetime.strptime(row["created_date"], "%Y-%m-%d").replace(tzinfo=timezone.utc)
        n, dial_bad = row["new_users"], row["dial_code_missing"]
        cfg = gen.get("user_data", {})
        starts = [G.U(G.parse_ts(cfg[k]["start"])) for k in ("missing_dial_code",) if k in cfg]
        for k in range(n):
            bad_dial = k >= n - dial_bad
            lo_hour = 0
            if bad_dial and starts and day.date() == min(starts).date():
                lo_hour = min(starts).hour
            hi_hour = max(0, now.hour - 1) if day.date() == now.date() else 23
            hour = rng.randint(min(lo_hour, hi_hour) if bad_dial else 0, hi_hour)
            created = day + timedelta(hours=hour, minutes=rng.randint(0, 59), seconds=rng.randint(0, 59))
            locale = rng.choice(["en", "en", "fr", "es", "de", "pt"])
            dial = "+99"
            if bad_dial:
                dial = [None, ""][k % 2]
            users.append((uid, national(G.USER_POOL + 1 + (uid - G.USER_POOL - 2)), locale, dial, 1,
                          1 if rng.random() < 0.9 else 0, _fmt(created), _fmt(created)))
            new_ids.setdefault(row["created_date"], []).append(uid)
            uid += 1
    cn.executemany("INSERT INTO accounts VALUES (?,?,?,?,?,?,?,?)", users)

    did = 1
    for u in range(G.USER_POOL):
        for _ in range(1 if rng.random() < 0.85 else 2):
            last = last_req.get(u)
            expiry = (last + timedelta(minutes=10)) if last else G.BASELINE_START - timedelta(days=rng.randint(2, 30))
            login = (last + timedelta(seconds=rng.randint(20, 120))) if last else expiry
            devices.append((did, u + 1, _fmt(expiry), _fmt(login), _fmt(login)))
            did += 1
    # the planted number's single device
    devices.append((did, planted_id, _fmt(G.PLANTED_TS + timedelta(minutes=10)), _fmt(G.PLANTED_TS), _fmt(G.PLANTED_TS)))
    cn.executemany("INSERT INTO sessions VALUES (?,?,?,?,?)", devices)

    # ---- outbox ----
    rows = []
    qid = 1

    def add(channel, status, created, updated, target):
        nonlocal qid
        rows.append((qid, channel, status, _fmt(created), _fmt(updated), "[mock body]", target))
        qid += 1

    for r in sorted(reqs, key=lambda x: x["ts"]):
        created = r["ts"]
        if r["channel"] == "api_failed":
            continue  # these never reached the queue
        if r["channel"] == "never_sent" and not r.get("stuck"):
            continue  # lost before the queue (app or API)
        if r.get("stuck"):
            add("sms", "SENDING", created, created + timedelta(seconds=2), "mock-destination")
            continue
        wait = 1 + zlib.crc32(G.seed_key(r["request_id"]).encode()) % 6
        add("sms", "SENT", created, created + timedelta(seconds=wait), "mock-destination")
    # other traffic in the same queue: push messages and a few other texts
    hour = G.BASELINE_START.replace(minute=0, second=0, microsecond=0)
    while hour < now:
        for _ in range(max(0, round(6 * G.HOURLY_SHAPE[hour.hour] + rng.gauss(0, 1)))):
            c = hour + timedelta(seconds=rng.randrange(3600))
            if c < now:
                add("push", "SENT", c, c + timedelta(seconds=rng.randint(1, 5)), "mock-destination")
        hour += timedelta(hours=1)
    cn.executemany("INSERT INTO outbox VALUES (?,?,?,?,?,?,?)", rows)
    cn.commit()
    cn.close()
    return {"users": len(users), "devices": len(devices), "queue_rows": len(rows)}
