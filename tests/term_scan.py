"""Shared repository scanner for the privacy tests.

The scanner reads an optional private word list (plain text, one lowercase word per line) from the file named
by the environment variable II_TERMS_FILE. The repository holds no word list. Without the variable, or when
the file is missing, the word check is skipped. Every shipped text file is lowercased and split into whole
words (identifiers are also split on underscore, hyphen, dot and camelCase boundaries, and adjacent parts are
tested joined with and without an underscore).
"""
import os
import re
from pathlib import Path

SKIP_MESSAGE = "set II_TERMS_FILE to a private word list to enable the term scan"

SKIP_DIRS = {".git", "__pycache__", "generated", ".venv", "node_modules", "results"}
SKIP_SUFFIXES = {".png", ".aiff", ".pyc", ".db", ".zip", ".ico", ".jpg", ".jpeg", ".gif"}

_CHUNK = re.compile(r"[A-Za-z0-9_\-.]+")
_CAMEL = re.compile(r"[A-Z]+(?![a-z])|[A-Z]?[a-z]+|[0-9]+")


def load_terms(path=None) -> frozenset:
    """Words from the private list; empty when no list is configured or the file is missing."""
    path = path if path is not None else os.environ.get("II_TERMS_FILE", "")
    if not path:
        return frozenset()
    try:
        lines = Path(path).read_text(encoding="utf-8").splitlines()
    except OSError:
        return frozenset()
    return frozenset(x.strip().lower() for x in lines if x.strip() and not x.startswith("#"))


def candidate_words(text: str):
    """Yield every lowercase candidate word in the text."""
    for chunk in _CHUNK.findall(text):
        lowered = chunk.lower()
        yield lowered
        parts = [x for x in re.split(r"[_\-.]+", chunk) if x]
        pieces = []
        for part in parts:
            pieces.extend(m.group(0).lower() for m in _CAMEL.finditer(part))
            yield part.lower()
        yield from pieces
        for seq in (parts and [p.lower() for p in parts], pieces):
            for a, b in zip(seq, seq[1:]):
                yield a + b
                yield a + "_" + b


def forbidden_in_text(text: str, terms) -> set:
    """The listed words found in the text."""
    return {w for w in set(candidate_words(text)) if w in terms}


def shipped_files(root: Path):
    for p in sorted(root.rglob("*")):
        if not p.is_file() or SKIP_DIRS & set(p.relative_to(root).parts):
            continue
        if p.name in (".DS_Store", ".env", ".ii_secret") or p.suffix in SKIP_SUFFIXES:
            continue   # .env and .ii_secret are local, git-ignored and left out of the release zip
        yield p


def scan_tree(root: Path, terms=None) -> list:
    """Return 'relative path: forbidden word found' for each hit (the word itself is not printed)."""
    terms = load_terms() if terms is None else terms
    hits = []
    if not terms:
        return hits
    for p in shipped_files(root):
        try:
            text = p.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for _ in sorted(forbidden_in_text(text, terms)):
            hits.append(f"{p.relative_to(root)}: forbidden word from the private list")
    return hits
