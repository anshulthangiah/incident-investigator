"""Build two tiny git repositories with fixed dates, so commit hashes are deterministic.

code_service and message_gateway each have a few ordinary commits and one benign commit
close to the release. One scenario variant plants a bad commit that strips the country prefix.
A fake secret is planted in code_service so the secret scrubbing can be tested.
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

PLANTED_SECRET = "MOCKKEY_NOT_A_REAL_KEY_0123456789"

ENV_BASE = {
    "GIT_CONFIG_GLOBAL": "/dev/null",
    "GIT_CONFIG_SYSTEM": "/dev/null",
    "GIT_AUTHOR_NAME": "Mock Dev",
    "GIT_AUTHOR_EMAIL": "dev@example.test",
    "GIT_COMMITTER_NAME": "Mock Dev",
    "GIT_COMMITTER_EMAIL": "dev@example.test",
}


def git(repo: Path, *args: str, date: str | None = None) -> None:
    env = {**os.environ, **ENV_BASE}
    if date:
        env["GIT_AUTHOR_DATE"] = env["GIT_COMMITTER_DATE"] = date
    subprocess.run(["git", "-C", str(repo), *args], check=True, env=env, capture_output=True, text=True)


CODE_SEND_GOOD = f'''"""Mock verification-code sender, used only to test the Incident Investigator."""
from .settings import CODE_EXPIRY_MINUTES

DEFAULT_API_KEY = "{PLANTED_SECRET}"  # mock value, not a real key


def build_provider_payload(dial_code, phone, template_id):
    number = dial_code.lstrip("+") + phone
    return {{"recipient": number, "template_id": template_id, "api_key": DEFAULT_API_KEY}}


def send_code(dial_code, phone, template_id, client):
    payload = build_provider_payload(dial_code, phone, template_id)
    return client.post("/codes", payload)
'''

CODE_SEND_BAD = CODE_SEND_GOOD.replace(
    '    number = dial_code.lstrip("+") + phone\n',
    '    # normalise: send the national number only\n    number = (dial_code + phone).replace("+99", "")\n',
)

GATEWAY_GOOD = '''"""Mock message gateway, used only to test the Incident Investigator."""


def normalise_number(dial_code, phone):
    return dial_code.lstrip("+") + phone


def dispatch(dial_code, phone, body, provider):
    number = normalise_number(dial_code, phone)
    return provider.send(number, body)
'''

# The "bad" gateway version drops the prefix for +99 numbers.
GATEWAY_BAD = GATEWAY_GOOD.replace(
    '    return dial_code.lstrip("+") + phone\n',
    '    # domestic routes expect the national number\n    if dial_code in ("+99", "99"):\n        return phone\n    return dial_code.lstrip("+") + phone\n',
)


def code_commits(variant: str):
    send = CODE_SEND_BAD if variant == "bad_commit" else CODE_SEND_GOOD
    benign_msg = "Update code expiry wording" if variant != "bad_commit" else "Normalise phone numbers before sending"
    commits = [
        ("2026-11-02T10:00:00+0000", "Initial code service",
         {"src/codes/send_code.py": CODE_SEND_GOOD, "src/codes/settings.py": "CODE_EXPIRY_MINUTES = 10\n"}),
        ("2026-11-06T15:20:00+0000", "Add resend limit",
         {"src/codes/resend.py": "MAX_RESENDS = 3\n"}),
        ("2026-11-10T11:05:00+0000", "Log provider response status",
         {"src/codes/logging_utils.py": "def log_status(resp):\n    return resp.status\n"}),
    ]
    if variant == "bad_commit":
        commits.append(("2026-11-15T17:30:00+0000", benign_msg, {"src/codes/send_code.py": send}))
    else:
        commits.append(("2026-11-15T17:30:00+0000", benign_msg,
                        {"src/codes/settings.py": "CODE_EXPIRY_MINUTES = 10  # shown to users as ten minutes\n"}))
    return commits


def gateway_commits(variant: str):
    commits = [
        ("2026-11-03T09:30:00+0000", "Initial message gateway",
         {"src/gateway/dispatch.py": GATEWAY_GOOD}),
        ("2026-11-09T14:00:00+0000", "Add retry on provider timeout",
         {"src/gateway/retry.py": "RETRIES = 2\n"}),
    ]
    if variant == "bad_commit":
        commits.append(("2026-11-15T17:40:00+0000", "Trim dial code for domestic routes",
                        {"src/gateway/dispatch.py": GATEWAY_BAD}))
    else:
        commits.append(("2026-11-15T17:40:00+0000", "Tidy gateway logging",
                        {"src/gateway/logging_utils.py": "def log(msg):\n    return msg\n"}))
    return commits


def build_repo(path: Path, commits) -> None:
    path.mkdir(parents=True)
    subprocess.run(["git", "init", "-q", "-b", "main", str(path)], check=True,
                   env={**os.environ, **ENV_BASE}, capture_output=True, text=True)
    for date, msg, files in commits:
        for rel, content in files.items():
            p = path / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")
        git(path, "add", "-A")
        git(path, "commit", "-q", "--no-gpg-sign", "-m", msg, date=date)


def build_repos(base: Path, variants: dict[str, str]) -> str:
    build_repo(base / "code_service", code_commits(variants.get("code_service", "clean")))
    build_repo(base / "message_gateway", gateway_commits(variants.get("message_gateway", "clean")))
    return PLANTED_SECRET
