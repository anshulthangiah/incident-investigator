"""Regenerate evals/scenarios/expected.lock.json.

Run this ONLY on purpose, after deliberately changing an expected answer.
If results already exist, also record the change in CHANGELOG.md.
"""
import hashlib
import json
from pathlib import Path

SCEN = Path(__file__).resolve().parent / "scenarios"


def expected_hash(expected: dict) -> str:
    return hashlib.sha256(json.dumps(expected, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def main() -> None:
    lock = {}
    for f in sorted(SCEN.glob("S*.json")):
        data = json.loads(f.read_text(encoding="utf-8"))
        lock[data["id"]] = expected_hash(data["expected"])
    (SCEN / "expected.lock.json").write_text(json.dumps(lock, indent=2) + "\n")
    print(f"locked {len(lock)} expected answers")


if __name__ == "__main__":
    main()
