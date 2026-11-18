"""Mock backend API. Standard library only. All behaviour is invented.

Endpoints:
  POST /v1/verify/start   body: country_prefix, phone, client; Authorization: Bearer <token>
        Success: 200 {"message": "Request accepted", "code": ""}   (for ANY country prefix, including empty)
        The token is read from MOCK_NOTIFY_API_TOKEN (default mock-token-not-secret).
  GET  /v1/logs?date=YYYY-MM-DD   the provider's live log for one day; Authorization: Bearer <provider key>
        Returns {"data": [...rows like provider_logs.jsonl...], "metadata": {"total": n}}. Needs a scenario folder.
  GET  /v1/account/balance   key in the X-Api-Key header; no query parameters. Returns {"balance": <number>, "units": "credits"}. Needs a scenario folder.

Scenario behaviour comes from api_mode.json (and backend.json for credit and logs):
  latency_ms              artificial delay before answering the send call
  forward                 "keep" or "strip_prefix": what the mock would forward to the provider
  echo_forwarded_number   if true, the send response adds "_mock_forwarded" with the (masked) forwarded number
  error_status            if set (for example 500), the send call answers that status with error_message
  error_message           message used with error_status
  return_code             if true, the send response puts a (fake) code value in "code": a security finding for the tool
  record_probe_in_log     default true: a successful send adds a row to the live log
  log_lag_s               seconds before such a row becomes visible in the live log (the real log lags)
"""
from __future__ import annotations

import json
import os
import random
import threading
import time
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from mock.generate import rid

DEFAULT_MODE = {"latency_ms": 80, "forward": "keep", "echo_forwarded_number": False}
DEFAULT_PROVIDER_KEY = "mock-provider-key-not-secret"


def mask_phone(n: str) -> str:
    return n[:2] + "*" * max(len(n) - 6, 0) + n[-4:] if len(n) > 6 else "*" * len(n)


def mock_now() -> datetime:
    """Same clock as the tools use (MOCK_NOW plus elapsed time), so probe rows land inside the tool's search window."""
    from investigator import config
    return config.now_utc()


class Backend:
    """Reads a generated scenario folder: the provider log file and the credit value."""

    def __init__(self, folder: Path | None):
        self.rows: list[dict] = []
        self.credit = "4200.00"
        self.probe_rows: list[tuple[float, dict]] = []   # (visible-at monotonic time, row)
        if folder:
            info = json.loads((Path(folder) / "backend.json").read_text())
            self.credit = info.get("credit", self.credit)
            f = Path(folder) / info.get("provider_log_file", "provider_logs.jsonl")
            if f.exists():
                with f.open(encoding="utf-8") as fh:
                    self.rows = [json.loads(line) for line in fh if line.strip()]
        self.by_date: dict[str, list[dict]] = {}
        for r in self.rows:
            self.by_date.setdefault(r["sent_at"][:10], []).append(r)

    def day(self, d: str) -> list[dict]:
        now = time.monotonic()
        return list(self.by_date.get(d, [])) + [r for vis, r in self.probe_rows if vis <= now and r["sent_at"][:10] == d]


def make_handler(mode: dict, token: str, calls: list, backend: Backend, provider_key: str):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *a):  # quiet
            pass

        def _send(self, code: int, body, raw: bool = False):
            data = (body if raw else json.dumps(body)).encode()
            self.send_response(code)
            self.send_header("Content-Type", "text/plain" if raw else "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_POST(self):
            if self.path != "/v1/verify/start":
                return self._send(404, {"message": "Not found (mock)"})
            auth = self.headers.get("Authorization", "")
            if auth != f"Bearer {token}":
                return self._send(401, {"message": "Unauthorized (mock wording)"})
            length = int(self.headers.get("Content-Length", "0") or 0)
            try:
                body = json.loads(self.rfile.read(length) or b"{}")
            except json.JSONDecodeError:
                return self._send(400, {"message": "Invalid JSON (mock wording)"})
            if "phone" not in body or "country_prefix" not in body:
                return self._send(400, {"message": "Missing field (mock wording)"})
            time.sleep(mode.get("latency_ms", 80) / 1000)
            if mode.get("error_status"):
                calls.append({"error": mode["error_status"]})
                return self._send(int(mode["error_status"]), {"message": mode.get("error_message", "Server error (mock wording)")})
            dc, phone = str(body["country_prefix"]), str(body["phone"])
            forwarded = (dc.lstrip("+") + phone)
            if mode.get("forward") == "strip_prefix" and forwarded.startswith("99") and len(forwarded) > 10:
                forwarded = forwarded[2:]
            calls.append({"country_prefix": dc, "phone_len": len(phone), "forwarded_len": len(forwarded)})
            resp = {"message": "Request accepted", "code": "571204" if mode.get("return_code") else ""}  # fake value
            if mode.get("echo_forwarded_number"):
                resp["_mock_forwarded"] = mask_phone(forwarded)  # mock-only field
            if mode.get("record_probe_in_log", True) and backend is not None and not mode.get("return_code_no_log"):
                now = mock_now()
                row = {"request_ref": rid(random.getrandbits(96)), "sent_at": now.isoformat(), "to": forwarded,
                       "country": "Mockland", "status": "delivered", "sender": "MOCKA",
                       "delivered_at": (now + timedelta(seconds=3)).isoformat(), "cost": "0.05", "length": "1",
                       "failure": "", "client_ip": "203.0.113.5",
                       "template": "tpl-0001", "registration_ref": "reg-0001", "channel": "api", "route": "4"}
                backend.probe_rows.append((time.monotonic() + float(mode.get("log_lag_s", 0)), row))
            self._send(200, resp)

        def do_GET(self):
            u = urlparse(self.path)
            q = parse_qs(u.query)
            if backend is None:
                return self._send(404, {"message": "Not found (mock)"})
            if u.path == "/v1/logs":
                if self.headers.get("Authorization", "") != f"Bearer {provider_key}":
                    return self._send(401, {"message": "Unauthorized (mock wording)"})
                rows = backend.day((q.get("date") or [""])[0])
                return self._send(200, {"data": rows, "metadata": {"total": len(rows)}})
            if u.path == "/v1/account/balance":
                if self.headers.get("X-Api-Key", "") != provider_key:
                    return self._send(401, {"message": "Unauthorized (mock wording)"})
                return self._send(200, {"balance": float(backend.credit), "units": "credits"})
            self._send(404, {"message": "Not found (mock)"})

    return Handler


class _Server(ThreadingHTTPServer):
    daemon_threads = True  # a hanging mock call must not block shutdown


class MockApi:
    """Run in a thread; use as a context manager in tests. `folder` is a generated scenario folder (for logs and credit)."""

    def __init__(self, mode: dict | None = None, token: str | None = None, port: int = 0, folder: Path | str | None = None,
                 provider_key: str | None = None):
        self.mode = {**DEFAULT_MODE, **(mode or {})}
        self.token = token or os.environ.get("MOCK_NOTIFY_API_TOKEN", "mock-token-not-secret")
        self.provider_key = provider_key or os.environ.get("MOCK_PROVIDER_KEY", DEFAULT_PROVIDER_KEY)
        self.calls: list = []
        self.backend = Backend(Path(folder)) if folder else Backend(None)
        if not folder:
            self.backend = None
        self.server = _Server(("127.0.0.1", port), make_handler(self.mode, self.token, self.calls, self.backend,
                                                                           self.provider_key))
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    @property
    def base_url(self) -> str:
        return f"http://127.0.0.1:{self.server.server_address[1]}"

    def start(self):
        self.thread.start()
        return self

    def stop(self):
        self.server.shutdown()
        self.server.server_close()

    def __enter__(self):
        return self.start()

    def __exit__(self, *exc):
        self.stop()


if __name__ == "__main__":
    import sys
    scen_dir = sys.argv[1] if len(sys.argv) > 1 else None
    mode = json.loads((Path(scen_dir) / "api_mode.json").read_text()) if scen_dir else {}
    api = MockApi(mode, port=int(os.environ.get("MOCK_PORT", "8099")), folder=scen_dir)
    print(f"mock backend API on {api.base_url} (mode: {api.mode}); token from MOCK_NOTIFY_API_TOKEN, "
          f"provider key from MOCK_PROVIDER_KEY")
    api.server.serve_forever()
