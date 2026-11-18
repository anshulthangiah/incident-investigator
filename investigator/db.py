"""Database adapters. One fixed, parameterised, aggregate statement per check; no free-form SQL anywhere.

DB_KIND = sqlite (the mock stack, no extra package) | mssql (needs pymssql) | postgres (needs psycopg).
Drivers are imported only when used. Add another database by adding one Adapter below.

Rules:
- Object and column names come from settings and are validated as plain identifiers before they enter SQL.
- Dates are always parameters, never pasted into SQL.
- Every statement is checked: it must be one SELECT. Sessions are read-only where the database supports it.
- Only counts, flags and timestamps are returned. Never a name, number, address, token or message text.
- Error text is rewritten into short friendly sentences that never contain the host, user or password.
"""
from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from . import config


class DbConfigError(Exception):
    """A clean message about settings. Never contains a password, user name or host."""


_PLAIN = r"[A-Za-z_][A-Za-z0-9_]*"
_BRACKETED = r"\[[A-Za-z_][A-Za-z0-9_ ]*\]"
_QUOTED = r'"[A-Za-z_][A-Za-z0-9_ ]*"'


def split_host(host: str, default_port: int) -> tuple[str, int]:
    m = re.fullmatch(r"([^,:\s]+)(?:[,:](\d+))?", (host or "").strip())
    if not m:
        raise DbConfigError("DB_HOST should be a host name or address, optionally with a port "
                            "(for example 203.0.113.5,1433 or db.example.test:5432)")
    return m.group(1), int(m.group(2) or config.get_int("DB_PORT", default_port))


def column(name_setting: str, default: str) -> str:
    v = config.get(name_setting, default)
    if not re.fullmatch(_PLAIN, v):
        raise DbConfigError(f"{name_setting} must be a plain column name (letters, digits, underscore)")
    return v


def assert_select(sql: str) -> str:
    """Last line of defence: one SELECT statement, nothing else."""
    s = sql.strip()
    if not re.match(r"(?is)^select\b", s) or ";" in s.rstrip(";") or re.search(
            r"(?i)\b(insert|update|delete|drop|alter|create|truncate|exec|execute|merge|grant|attach|pragma)\b", s):
        raise DbConfigError("built-in safety check refused a statement that is not a single SELECT")
    return s


# ---------------- object name validation ----------------

def _plain_object(setting: str):
    def check(raw: str) -> str:
        if not re.fullmatch(rf"{_PLAIN}(\.{_PLAIN}){{0,1}}", raw or ""):
            raise DbConfigError(f"{setting} must be a plain table or view name such as accounts or main.accounts "
                                "(host and database go in DB_HOST and DB_NAME, not here)")
        return raw
    return check


def _mssql_object(setting: str):
    ident = rf"(?:{_BRACKETED}|{_PLAIN})"

    def check(raw: str) -> str:
        if not re.fullmatch(rf"{ident}(\.{ident}){{0,2}}", raw or ""):
            raise DbConfigError(f"{setting} must be a plain table or view name like app.accounts "
                                "(host and database go in DB_HOST and DB_NAME, not here)")
        return raw
    return check


def _pg_object(setting: str):
    ident = rf"(?:{_QUOTED}|{_PLAIN})"

    def check(raw: str) -> str:
        if not re.fullmatch(rf"{ident}(\.{ident}){{0,1}}", raw or ""):
            raise DbConfigError(f"{setting} must be like public.accounts or accounts (optionally \"Quoted\" names); "
                                "host and database go in DB_HOST and DB_NAME, not here")
        return raw
    return check


# ---------------- connections and errors ----------------

def sqlite_path() -> Path:
    name = config.get("DB_NAME")
    if not name:
        raise DbConfigError("DB_NAME must be the path of the SQLite file (for example mock/generated/S19/mock.db)")
    p = Path(name).expanduser()
    return p if p.is_absolute() else config.ROOT / p


def _sqlite_connect():
    p = sqlite_path()
    if not p.is_file():
        raise DbConfigError("the SQLite file in DB_NAME does not exist (run: python3 -m mock.generate --all)")
    cn = sqlite3.connect(f"file:{p}?mode=ro", uri=True, timeout=5)  # read-only open
    cn.execute("PRAGMA query_only = ON")
    return cn


def _sqlite_error(e: Exception) -> str:
    t = str(e).lower()
    if "no such table" in t or "no such column" in t:
        return "table or column not found (check DB_USERS_OBJECT, DB_DEVICES_OBJECT, DB_QUEUE_OBJECT and the DB_COL_* names)"
    if "locked" in t:
        return "the database file is locked; try again"
    return type(e).__name__


def _mssql_connect():
    try:
        import pymssql  # type: ignore
    except ImportError:
        raise DbConfigError("pymssql is not installed (pip install pymssql); it is optional and used only for DB_KIND=mssql")
    host, port = split_host(config.get("DB_HOST"), 1433)
    kw = {"tds_version": config.get("DB_TDS_VERSION")} if config.get("DB_TDS_VERSION") else {}
    return pymssql.connect(server=host, port=port, user=config.get("DB_USER"), password=config.get("DB_PASSWORD"),
                           database=config.get("DB_NAME"), login_timeout=15, timeout=30, **kw)


def _mssql_error(e: Exception) -> str:
    code = e.args[0] if e.args and isinstance(e.args[0], int) else None
    text = " ".join(str(x) for x in e.args).lower()
    if code == 18456 or "login failed" in text:
        return "login was rejected (check DB_USER and DB_PASSWORD)"
    if code == 4060 or "cannot open database" in text:
        return "the login cannot open that database (check DB_NAME and the login's permissions)"
    if code in (207, 208) or "invalid object name" in text or "invalid column" in text:
        return "table or column not found (check the DB_*_OBJECT and DB_COL_* settings)"
    if code in (229, 230) or "permission was denied" in text:
        return "the login has no SELECT permission on that object"
    if code == 20009 or "unable to connect" in text or "timed out" in text or "adaptive server is unavailable" in text:
        return "could not reach the server (is the VPN connected? is DB_HOST correct?)"
    return type(e).__name__ + (f" (error {code})" if code else "")


def _pg_connect():
    try:
        import psycopg  # type: ignore
    except ImportError:
        raise DbConfigError("psycopg is not installed (pip install \"psycopg[binary]\"); it is optional and used only for DB_KIND=postgres")
    host, port = split_host(config.get("DB_HOST"), 5432)
    cn = psycopg.connect(host=host, port=port, user=config.get("DB_USER"), password=config.get("DB_PASSWORD"),
                         dbname=config.get("DB_NAME"), connect_timeout=15, sslmode=config.get("DB_SSLMODE", "prefer"),
                         options="-c statement_timeout=30000 -c default_transaction_read_only=on")
    cn.read_only = True  # the session refuses writes, in addition to the fixed statements
    return cn


def _pg_error(e: Exception) -> str:
    state = getattr(e, "sqlstate", None) or getattr(getattr(e, "diag", None), "sqlstate", None)
    text = str(e).lower()
    if state == "28P01" or "password authentication failed" in text:
        return "login was rejected (check DB_USER and DB_PASSWORD)"
    if state == "28000" or "no pg_hba.conf entry" in text:
        return "the server refused this connection (login, SSL mode or allowed address); see DB_SSLMODE"
    if state == "3D000" or ("does not exist" in text and "database" in text):
        return "database not found (check DB_NAME)"
    if state in ("42P01", "42703") or "does not exist" in text:
        return "table or column not found (check the DB_*_OBJECT and DB_COL_* settings; Postgres folds unquoted names to lower case)"
    if state == "42501" or "permission denied" in text:
        return "the login has no SELECT permission on that object"
    if any(x in text for x in ("timeout", "could not connect", "connection refused", "timed out", "could not translate host name")):
        return "could not reach the server (is the VPN connected? is DB_HOST correct?)"
    return type(e).__name__ + (f" (SQLSTATE {state})" if state else "")


# ---------------- registry ----------------

@dataclass(frozen=True)
class Adapter:
    kind: str
    check_object: object      # (setting_name) -> validator(raw)
    connect: object
    error: object
    trim: str                 # trims whitespace: format(c=column)
    secs: str                 # seconds from a to b: format(a=, b=)
    date_of: str              # the calendar date of a timestamp: format(c=)
    ph: str                   # parameter placeholder
    default_users: str
    default_devices: str
    default_queue: str


ADAPTERS = {
    "sqlite": Adapter("sqlite", _plain_object, _sqlite_connect, _sqlite_error, "TRIM({c})",
                      "(strftime('%s', {b}) - strftime('%s', {a}))", "date({c})", "?", "accounts", "sessions", "outbox"),
    "mssql": Adapter("mssql", _mssql_object, _mssql_connect, _mssql_error, "LTRIM(RTRIM({c}))",
                     "DATEDIFF(second, {a}, {b})", "CAST({c} AS date)", "%s", "accounts", "sessions", "outbox"),
    "postgres": Adapter("postgres", _pg_object, _pg_connect, _pg_error, "BTRIM({c})",
                        "EXTRACT(EPOCH FROM ({b} - {a}))", "CAST({c} AS date)", "%s", "public.accounts", "public.sessions",
                        "public.outbox"),
}


def adapter() -> Adapter:
    kind = (config.get("DB_KIND") or "sqlite").lower()
    if kind in ("postgresql", "pg"):
        kind = "postgres"
    if kind not in ADAPTERS:
        raise DbConfigError(f"DB_KIND must be one of: {', '.join(ADAPTERS)}")
    return ADAPTERS[kind]


def param(a: Adapter, dt: datetime):
    """A naive timestamp as a driver parameter (sqlite stores text)."""
    return dt.strftime("%Y-%m-%d %H:%M:%S") if a.kind == "sqlite" else dt


def to_dt(v):
    """A timestamp read back from any driver, as a naive datetime (or None)."""
    if v is None or isinstance(v, datetime):
        return v
    s = str(v).strip().replace("T", " ")[:19]
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            pass
    return None


def execute(cur, a: Adapter, sql: str, params=()):
    return cur.execute(assert_select(sql), tuple(params))


def objects(a: Adapter) -> dict:
    return {"users": a.check_object("DB_USERS_OBJECT")(config.get("DB_USERS_OBJECT", a.default_users)),
            "devices": config.get("DB_DEVICES_OBJECT", a.default_devices),
            "queue": a.check_object("DB_QUEUE_OBJECT")(config.get("DB_QUEUE_OBJECT", a.default_queue))}


def build_sql(a: Adapter) -> str:
    """Per creation day: how many users, how many with an empty locale, how many with an empty dial code."""
    o = objects(a)["users"]
    loc, dial = column("DB_COL_LOCALE", "language"), column("DB_COL_DIAL_CODE", "country_prefix")
    created = column("DB_COL_CREATED", "created_at")
    empty = lambda c: f"SUM(CASE WHEN {c} IS NULL OR {a.trim.format(c=c)} = '' THEN 1 ELSE 0 END)"
    return (f"SELECT COUNT(*), {empty(loc)}, {empty(dial)} FROM {o} WHERE {created} >= {a.ph} AND {created} < {a.ph}")


def build_user_sql(a: Adapter) -> tuple[str, str | None]:
    """Two fixed statements for ONE user, found by user name (the national number, passed as a parameter).
    They return flags, counts and timestamps only: never a name, number, address, token or the code itself."""
    o = objects(a)
    obj = o["users"]
    loc, dial = column("DB_COL_LOCALE", "language"), column("DB_COL_DIAL_CODE", "country_prefix")
    created, updated = column("DB_COL_CREATED", "created_at"), column("DB_COL_UPDATED", "updated_at")
    uname, uid = column("DB_COL_USERNAME", "login_ref"), column("DB_COL_USER_ID", "id")
    active, pconf = column("DB_COL_ACTIVE", "is_active"), column("DB_COL_PHONE_CONFIRMED", "phone_verified")
    empty = lambda c: f"MAX(CASE WHEN {c} IS NULL OR {a.trim.format(c=c)} = '' THEN 1 ELSE 0 END)"
    user_sql = (f"SELECT COUNT(*), {empty(loc)}, {empty(dial)}, MAX(CAST({active} AS int)), MAX(CAST({pconf} AS int)), "
                f"MIN({created}), MAX({updated}) FROM {obj} WHERE {uname} = {a.ph}")
    dev_raw = o["devices"]
    if dev_raw.lower() in ("none", "off", "-"):
        return user_sql, None
    dev = a.check_object("DB_DEVICES_OBJECT")(dev_raw)
    d_uid = column("DB_COL_DEV_USERID", "account_id")
    d_exp, d_login = column("DB_COL_DEV_CODE_EXPIRY", "code_valid_until"), column("DB_COL_DEV_LOGIN", "last_seen_at")
    dev_sql = (f"SELECT COUNT(*), MAX(d.{d_exp}), MAX(d.{d_login}) FROM {dev} d INNER JOIN {obj} u "
               f"ON d.{d_uid} = u.{uid} WHERE u.{uname} = {a.ph}")
    return user_sql, dev_sql


def build_queue_sql(a: Adapter) -> tuple[str, str, str, str]:
    """Four fixed, aggregate-only statements about the message queue. They read only kind, state and two
    timestamps. Never the body or the destination."""
    obj = objects(a)["queue"]
    chan, status = column("DB_QCOL_CHANNEL", "kind"), column("DB_QCOL_STATUS", "state")
    created, updated = column("DB_QCOL_CREATED", "created_at"), column("DB_QCOL_UPDATED", "updated_at")
    w, p = a.secs.format(a=created, b=updated), a.ph
    waiting = (f"SELECT {chan}, {status}, COUNT(*), MIN({created}), "
               f"SUM(CASE WHEN {created} < {p} THEN 1 ELSE 0 END), SUM(CASE WHEN {updated} IS NULL THEN 1 ELSE 0 END) "
               f"FROM {obj} WHERE {status} IN ('PENDING', 'SENDING', 'ON_HOLD') GROUP BY {chan}, {status}")
    d = a.date_of.format(c=created)
    daily = (f"SELECT {d}, {chan}, {status}, COUNT(*) FROM {obj} "
             f"WHERE {created} >= {p} AND {created} < {p} GROUP BY {d}, {chan}, {status}")
    wait = (f"SELECT {chan}, COUNT(*), "
            f"SUM(CASE WHEN {w} >= 0 AND {w} < 30 THEN 1 ELSE 0 END), SUM(CASE WHEN {w} >= 30 AND {w} < 120 THEN 1 ELSE 0 END), "
            f"SUM(CASE WHEN {w} >= 120 AND {w} < 600 THEN 1 ELSE 0 END), SUM(CASE WHEN {w} >= 600 AND {w} < 1800 THEN 1 ELSE 0 END), "
            f"SUM(CASE WHEN {w} >= 1800 THEN 1 ELSE 0 END) "
            f"FROM {obj} WHERE {status} = 'SENT' AND {updated} IS NOT NULL AND {created} >= {p} AND {created} < {p} "
            f"GROUP BY {chan}")
    newest = f"SELECT MAX({created}) FROM {obj}"
    return waiting, daily, wait, newest


def build_freshness_sql(a: Adapter) -> str:
    """Newest user record: a one-value freshness check used to estimate replica lag."""
    obj = objects(a)["users"]
    return f"SELECT MAX({column('DB_COL_CREATED', 'created_at')}) FROM {obj}"


def reachable_reason() -> str | None:
    """None if the database can be opened within 3 s, else a short reason. Used by the preflight."""
    import socket
    try:
        a = adapter()
        if a.kind == "sqlite":
            return None if sqlite_path().is_file() else "the SQLite file in DB_NAME does not exist (run: python3 -m mock.generate --all)"
        host, port = split_host(config.get("DB_HOST"), 1433 if a.kind == "mssql" else 5432)
    except DbConfigError as e:
        return str(e)
    try:
        socket.create_connection((host, port), timeout=3).close()
        return None
    except OSError:
        return "the database server did not answer within 3 seconds (is the VPN connected? is DB_HOST correct?)"
