"""Things the PM adds when continuing an investigation: typed notes and files.

Everything is masked before the model sees it (phone numbers, emails, IP addresses, credentials) and is treated as
untrusted data, never as instructions. Delivery-log exports are copied into LOGS_DIR, where fetch_delivery_logs reads
them; the model only ever sees the summary that tool returns.
"""
from __future__ import annotations

import csv
import hashlib
import re
import shutil
from pathlib import Path

from . import config, tools

TEXT_EXT = {".txt", ".md", ".log", ".json", ".csv", ".tsv"}
MAX_EXPORT_BYTES = 25 * 1024 * 1024
MAX_TEXT_CHARS = 6000
MAX_NOTE_CHARS = 4000


def input_dir() -> Path:
    return config.state_dir() / "inputs"


class InputError(Exception):
    """A plain message the PM can act on."""


_PHONE = re.compile(r"(?<!\d)\+?\d[\d \-]{8,14}\d(?!\d)")
_EMAIL = re.compile(r"[\w.+\-]+@[\w\-]+\.[\w.\-]+")
_IP = re.compile(r"\b\d{1,3}(?:\.\d{1,3}){3}\b")


def mask_text(s: str) -> str:
    s = _EMAIL.sub("[email]", s)
    s = _IP.sub("[ip]", s)
    s = _PHONE.sub(lambda m: config.mask_phone(m.group(0)), s)
    return config.redact(s)


def _sha(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _is_delivery_export(p: Path) -> bool:
    try:
        with open(p, newline="", encoding="utf-8-sig") as fh:
            head = next(csv.reader(fh), [])
    except (OSError, UnicodeDecodeError, csv.Error):
        return False
    return "sent_at" in head and "status" in head


def add_note(text: str) -> dict:
    text = (text or "").strip()
    if not text:
        raise InputError("the note is empty")
    clipped = text[:MAX_NOTE_CHARS]
    return {"kind": "note", "name": "note",
            "summary": mask_text(clipped) + (" [note shortened]" if len(text) > MAX_NOTE_CHARS else "")}


def add_file(path: str) -> dict:
    p = Path(path).expanduser()
    if not p.is_absolute():
        p = (Path.cwd() / p).resolve()
    if not p.is_file():
        raise InputError(f"file not found: {path}")
    ext = p.suffix.lower()
    if ext not in TEXT_EXT:
        raise InputError(f"{p.name}: file type {ext or '(none)'} is not supported. Supported: delivery-log exports and text "
                         "files (.csv .txt .md .log .json .tsv). For anything else, type what it shows with --note.")
    size = p.stat().st_size
    sha = _sha(p)
    if ext == ".csv" and _is_delivery_export(p):
        if size > MAX_EXPORT_BYTES:
            raise InputError(f"{p.name} is larger than {MAX_EXPORT_BYTES // (1024 * 1024)} MB; export a shorter period")
        dest_dir = tools.logs_dir()
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / p.name
        already = dest.exists() and _sha(dest) == sha
        if dest.exists() and not already:
            dest = dest_dir / f"{p.stem}_{sha[:6]}{p.suffix}"
            already = dest.exists() and _sha(dest) == sha
        if not already and p.resolve() != dest.resolve():
            shutil.copy2(p, dest)
        days, rows = set(), 0
        with open(p, newline="", encoding="utf-8-sig") as fh:
            for r in csv.DictReader(fh):
                rows += 1
                ts = tools._ts(r.get("sent_at"))
                if ts:
                    days.add(ts.date().isoformat())
        if not rows:
            raise InputError(f"{p.name} has a header but no rows")
        d = sorted(days)
        span = f"{d[0]} to {d[-1]}" if d else "unknown dates"
        return {"kind": "log_export", "name": p.name, "sha": sha,
                "summary": f"Delivery-log export added: {rows} rows covering {len(d)} days ({span}, UTC). It is now part of "
                           "the export folder; fetch_delivery_logs will use it for dates older than 7 days. "
                           + ("(This exact file was already there.)" if already else "")}
    raw = p.read_bytes()[:200_000].decode("utf-8", errors="replace")
    clipped = raw[:MAX_TEXT_CHARS]
    return {"kind": "text_file", "name": p.name, "sha": sha,
            "summary": f"Text file {p.name} (masked, "
                       f"{'first ' + str(MAX_TEXT_CHARS) + ' characters' if len(raw) > MAX_TEXT_CHARS else 'complete'}):\n"
                       + mask_text(clipped)}


def new_files_in_inputs(known_shas: set[str]) -> list[Path]:
    """Files dropped into inputs/ that this session has not seen yet."""
    d = input_dir()
    if not d.is_dir():
        return []
    return [p for p in sorted(d.iterdir()) if p.is_file() and not p.name.startswith(".") and _sha(p) not in known_shas]
