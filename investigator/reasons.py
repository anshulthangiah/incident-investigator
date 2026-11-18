"""Plain-language meanings for failure reasons, read from data/reason_glossary.json.

The shipped file holds invented wording for the mock provider. To use a real provider, replace its 'reasons' list with
that provider's own documented list. A reason that is not in the file is reported as 'not documented'; it is never
guessed.
"""
from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

from . import config


def glossary_path() -> Path:
    p = Path(config.get("REASON_GLOSSARY") or "data/reason_glossary.json").expanduser()
    return p if p.is_absolute() else config.ROOT / p


@lru_cache(maxsize=4)
def _load(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def reload() -> None:
    _load.cache_clear()


def glossary() -> dict:
    try:
        return _load(str(glossary_path()))
    except (OSError, ValueError):
        return {"categories": {"unknown": {"label": "Not documented", "who_fixes": "The glossary file could not be read."}},
                "reasons": [], "error_codes": {}}


def _norm(s: str) -> str:
    s = re.sub(r"\((?:mock wording|mock)\)", "", s or "", flags=re.I)
    return re.sub(r"\s+", " ", s.strip().rstrip(".")).lower()


def _clip_untrusted(s: str, n: int = 60) -> str:
    s = re.sub(r"\s+", " ", s or "").strip()
    return s[:n] + (" [...]" if len(s) > n else "")


def explain(reason: str) -> dict:
    """{reason, category, category_label, who_fixes, meaning, documented}. Unknown reasons are 'not documented'."""
    g = glossary()
    raw = (reason or "").strip()
    cats = g.get("categories", {})
    norm = _norm(raw)
    for entry in g.get("reasons", []):
        if any(m in norm for m in (_norm(x) for x in entry.get("match", [])) if m):
            cat = entry.get("category", "unknown")
            c = cats.get(cat, cats.get("unknown", {"label": "Not documented", "who_fixes": ""}))
            return {"reason": entry.get("label", raw), "category": cat, "category_label": c["label"],
                    "who_fixes": c["who_fixes"], "meaning": entry["meaning"], "documented": True}
    c = cats.get("unknown", {"label": "Not documented", "who_fixes": "Ask the provider."})
    meaning = ("The log row is marked failed but has no failure reason." if not raw or raw == "(none)"
               else "This reason is not in the glossary, so its meaning is not known here.")
    # Unknown text comes from outside: show only a short clipped copy and mark it as untrusted data.
    return {"reason": "(none)" if not raw or raw == "(none)" else "(not documented) " + _clip_untrusted(raw),
            "category": "unknown", "category_label": c["label"], "who_fixes": c["who_fixes"],
            "meaning": meaning, "documented": False}


def explain_error_code(code: str) -> dict:
    e = glossary().get("error_codes", {}).get((code or "").strip().upper())
    if not e:
        return {"code": (code or "").strip()[:12], "label": "not documented", "meaning": "This error code is not in the glossary.",
                "category_label": "Not documented"}
    cats = glossary().get("categories", {})
    return {"code": code.strip().upper(), "label": e["label"], "meaning": e["meaning"],
            "category_label": cats.get(e.get("category", "unknown"), {}).get("label", "Not documented")}


def summarise(counted: list[tuple[str, int]]) -> dict:
    """counted = [(reason, n), ...] -> per-reason explanations and totals per category."""
    items, by_cat = [], {}
    for reason, n in counted:
        e = explain(reason)
        items.append({"reason": e["reason"], "meaning": e["meaning"], "category": e["category_label"],
                      "who_fixes": e["who_fixes"], "count": n})
        by_cat[e["category_label"]] = by_cat.get(e["category_label"], 0) + n
    return {"failure_reasons": items, "failures_by_category": dict(sorted(by_cat.items(), key=lambda x: -x[1]))}
