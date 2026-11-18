"""Phone numbers the PM wants checked.

Design: the AI never sees a number. It sees aliases (N1, N2 ...). A number is kept only in memory for the current run,
and only as a keyed fingerprint (HMAC, see config.local_key) in the saved session, so session and report files contain
no numbers and cannot be reversed without this machine's secret file. Numbers typed into the question or a note are
swapped for aliases before anything is sent to the model.
"""
from __future__ import annotations

import re

from . import config, tools

MAX_NUMBERS = 20


class NumberError(Exception):
    """A plain message the PM can act on."""


_CANDIDATE = re.compile(r"(?<![\w.])\+?\d[\d \-]{8,16}\d(?![\w])")


def digits10(s: str) -> str:
    d = re.sub(r"\D", "", s or "")
    return d[-10:] if len(d) >= 10 else ""


def looks_like_phone(raw: str) -> bool:
    """10 to 13 digits, and the last 10 start with an allowed leading digit (PHONE_LEADING_DIGITS, default empty: any digit).
    This keeps request IDs, timestamps and counts from being treated as numbers."""
    d = re.sub(r"\D", "", raw or "")
    return 10 <= len(d) <= 13 and (not config.get("PHONE_LEADING_DIGITS") or d[-10] in config.get("PHONE_LEADING_DIGITS"))


def parse_list(text: str) -> list[str]:
    return [t for t in re.split(r"[,\s;]+", text or "") if t and looks_like_phone(t)]


def register(state: dict, raw: str) -> str:
    """Add a number to the investigation and return its alias. Safe to call twice with the same number."""
    if not looks_like_phone(raw):
        raise NumberError("that does not look like a phone number (10 to 13 digits)")
    d = digits10(raw)
    h = tools.tel10(d)
    nums = state.setdefault("numbers", {})
    for alias, v in nums.items():
        if v["hmac"] == h:
            tools.remember_plain(alias, d)
            return alias
    if len(nums) >= MAX_NUMBERS:
        raise NumberError(f"at most {MAX_NUMBERS} numbers per investigation")
    alias = f"N{len(nums) + 1}"
    nums[alias] = {"hmac": h, "hint": d[-2:]}
    tools.remember_plain(alias, d)
    return alias


def scrub(text: str, state: dict, register_new: bool) -> str:
    """Replace phone numbers in text by aliases. Known numbers always; unknown ones are registered (notes, the question)
    or masked (files and model output, so a pasted list of thousands of numbers is never registered)."""
    def sub(m):
        raw = m.group(0)
        if not looks_like_phone(raw):
            return raw
        d = digits10(raw)
        h = tools.tel10(d)
        for alias, v in state.get("numbers", {}).items():
            if v["hmac"] == h:
                return alias
        if register_new:
            try:
                return register(state, raw)
            except NumberError:
                pass
        return "*" * 8 + d[-2:]
    return _CANDIDATE.sub(sub, text or "")


def describe(state: dict) -> list[str]:
    """For the PM's own screen only (the model never gets this): which alias is which number."""
    return [f"{a} = a number ending in {v['hint']}" for a, v in state.get("numbers", {}).items()]
