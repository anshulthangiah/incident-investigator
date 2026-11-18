"""Start the whole mock stack for one scenario inside this process and point the settings at it.

    from mock.stack import start
    stack = start("S1a")      # generates the scenario if needed, starts the mock API on a free local port
    ...
    stack.stop()

What it sets (only for this process): MOCK_NOW (the moment the data was generated, running forward), LOGS_DIR,
PROVIDER_API_URL / PROVIDER_API_KEY, CREDIT_URL, CODE_API_URL / CODE_API_TOKEN, DB_KIND=sqlite, DB_NAME, DB_ENABLED,
REPO_PATHS and PROBE_PHONE. Nothing is written to .env.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from mock import generate as G
from mock.api_server import MockApi, DEFAULT_PROVIDER_KEY

TEST_PHONE = "999000000001"  # invented


class Stack:
    def __init__(self, sid: str, folder: Path, api: MockApi):
        self.sid, self.folder, self.api = sid, folder, api

    def stop(self):
        self.api.stop()


def apply_env(sid: str, folder: Path, base_url: str, token: str, provider_key: str) -> dict:
    env = {
        "MOCK_NOW": G.U(G.NOW).replace(tzinfo=None).isoformat(),
        "LOGS_DIR": str(folder),
        "PROVIDER_API_URL": base_url, "PROVIDER_API_KEY": provider_key,
        "CREDIT_URL": base_url + "/v1/account/balance",
        "CODE_API_URL": base_url + "/v1/verify/start", "CODE_API_TOKEN": token,
        "DB_ENABLED": "true", "DB_KIND": "sqlite", "DB_NAME": str(folder / "mock.db"),
        "REPO_PATHS": f"{folder}/repos/code_service,{folder}/repos/message_gateway",
    }
    os.environ.update(env)
    os.environ.setdefault("PROBE_PHONE", TEST_PHONE)
    os.environ.setdefault("PROBE_LOG_WAIT_S", "10")
    os.environ.setdefault("PROBE_LOG_POLL_S", "0.5")
    os.environ.setdefault("PROBE_MIN_GAP_S", "1")
    return env


def start(sid: str, regenerate: bool = False, token: str = "mock-token-not-secret",
          provider_key: str = DEFAULT_PROVIDER_KEY) -> Stack:
    folder = G.OUT_DIR / sid
    if regenerate or not (folder / "mock.db").exists():
        if not (G.SCEN_DIR / f"{sid}.json").exists():
            raise SystemExit(f"unknown scenario {sid}; known: {', '.join(G.all_ids())}")
        G.generate(sid)
    mode = json.loads((folder / "api_mode.json").read_text())
    api = MockApi(mode, token=token, folder=folder, provider_key=provider_key).start()
    apply_env(sid, folder, api.base_url, token, provider_key)
    return Stack(sid, folder, api)
