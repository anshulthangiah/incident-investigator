"""Settings, secret redaction, phone fingerprints and the TLS context.

Settings come from the environment, after a small .env loader has run. Secrets are never printed: every output goes
through redact().
"""
from __future__ import annotations

import hashlib
import hmac as _hmac
import os
import re
import ssl
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
UTC = timezone.utc

# Settings whose values are removed from every output.
SECRET_NAMES = ("LLM_API_KEY", "PROVIDER_API_KEY", "CODE_API_TOKEN", "DB_PASSWORD")


def parse_env_line(line: str):
    """Return (key, value) or None. Quoted values keep '#'; an unquoted ' # comment' is dropped."""
    line = line.strip()
    if not line or line.startswith("#") or "=" not in line:
        return None
    k, v = line.split("=", 1)
    v = v.strip()
    if v[:1] in ("'", '"') and v.count(v[0]) >= 2:
        v = v[1:v.index(v[0], 1)]
    elif v.startswith("#"):
        v = ""  # an empty value followed by a comment
    else:
        v = re.split(r"\s+#", v, maxsplit=1)[0].strip()
    k = k.strip()
    if k.startswith("export "):
        k = k[7:].strip()
    return (k, v) if k else None


def load_env(path: Path | None = None) -> Path | None:
    """Load .env (git-ignored). If there is none, fall back to .env.example, which holds only mock-stack values.
    Values already in the environment win. Returns the file used."""
    candidates = [path] if path else [ROOT / ".env", ROOT / ".env.example"]
    for p in candidates:
        if p and p.exists():
            for line in p.read_text(encoding="utf-8").splitlines():
                kv = parse_env_line(line)
                if kv:
                    os.environ.setdefault(*kv)
            return p
    return None


def get(name: str, default: str = "") -> str:
    """A setting; an empty value counts as not set, so the default applies."""
    v = os.environ.get(name, "").strip()
    return v if v else default


def get_int(name: str, default: int) -> int:
    try:
        return int(get(name, str(default)))
    except ValueError:
        return default


def get_float(name: str, default: float) -> float:
    try:
        return float(get(name, str(default)))
    except ValueError:
        return default


def get_bool(name: str, default: bool = False) -> bool:
    v = get(name, "true" if default else "false").lower()
    return v in ("1", "true", "yes", "on")


def state_dir() -> Path:
    """Where sessions/, reports/, knowledge/, inputs/ and the secret file live (STATE_DIR, default: the project folder)."""
    p = Path(get("STATE_DIR") or ROOT).expanduser()
    return p if p.is_absolute() else ROOT / p


_T0 = time.monotonic()


def now_utc() -> datetime:
    """The current time in UTC. MOCK_NOW (mock stack only) pins the clock to the moment the mock data was generated and
    lets it run forward from there, so the mock API and the tools agree on 'now'."""
    fixed = get("MOCK_NOW")
    if fixed:
        try:
            return datetime.fromisoformat(fixed).replace(tzinfo=UTC) + timedelta(seconds=time.monotonic() - _T0)
        except ValueError:
            pass
    return datetime.now(UTC)


# ---------- redaction ----------

_QUERY_KEY = re.compile(r"(?i)\b(api[_-]?key|apikey|key|password|token|secret|access_token)=([^&\s\"']+)")
_HEADER_KEY = re.compile(r"(?i)(x-api-key|api-key|authorization)(['\"]?\s*[:=]\s*['\"]?)((?:bearer\s+)?[^\s,'\"}]+)")
_URL_USERINFO = re.compile(r"(?i)\b([a-z][a-z0-9+.\-]*://)[^/\s:@]+:[^/\s@]+@")
_KEY_SHAPES = re.compile(r"\b(?:sk-[A-Za-z0-9_\-]{16,}|eyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{5,})")


def redact(text) -> str:
    """Remove every configured secret value and any credential-looking pattern from text."""
    s = text if isinstance(text, str) else str(text)
    for name in SECRET_NAMES:
        v = get(name)
        if len(v) >= 6:
            s = s.replace(v, "[REDACTED]")
    s = _URL_USERINFO.sub(lambda m: m.group(1) + "[REDACTED]@", s)
    s = _QUERY_KEY.sub(lambda m: f"{m.group(1)}=[REDACTED]", s)
    s = _HEADER_KEY.sub(lambda m: f"{m.group(1)}{m.group(2)}[REDACTED]", s)
    s = _KEY_SHAPES.sub("[REDACTED]", s)
    return s


def mask_phone(n: str) -> str:
    digits = re.sub(r"\D", "", n or "")
    return "*" * max(len(digits) - 2, 0) + digits[-2:] if digits else ""


# ---------- TLS ----------

_SYSTEM_CA = ("/etc/ssl/cert.pem", "/private/etc/ssl/cert.pem", "/etc/ssl/certs/ca-certificates.crt")


def ssl_context() -> ssl.SSLContext:
    """The default context (verification on). If this Python has no CA file (python.org builds on macOS), load the
    system one. Verification is never disabled."""
    ctx = ssl.create_default_context()
    paths = ssl.get_default_verify_paths()
    has_default = bool(os.environ.get("SSL_CERT_FILE")) or (paths.cafile and os.path.exists(paths.cafile))
    if not has_default:
        for p in _SYSTEM_CA:
            if os.path.exists(p):
                ctx.load_verify_locations(cafile=p)
                break
    return ctx


# ---------- per-install secret and phone fingerprints ----------

_KEYS: dict = {}


def secret_file() -> Path:
    return Path(os.environ.get("SECRET_FILE") or state_dir() / ".ii_secret")


def local_key() -> bytes:
    """A random per-install key, created on first use with permissions 600. Phone fingerprints are HMACs under this
    key, so a saved fingerprint cannot be brute-forced back to a number without this file."""
    p = secret_file()
    if str(p) not in _KEYS:
        if not p.exists():
            p.parent.mkdir(parents=True, exist_ok=True)
            fd = os.open(p, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, "wb") as fh:
                fh.write(os.urandom(32))
        try:
            p.chmod(0o600)
        except OSError:
            pass
        _KEYS[str(p)] = p.read_bytes()
    return _KEYS[str(p)]


def fingerprint(label: str, value: str) -> str:
    return _hmac.new(local_key(), f"{label}:{value}".encode(), hashlib.sha256).hexdigest()[:16]
