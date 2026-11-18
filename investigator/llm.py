"""Model providers, standard library only (urllib). Both are normalised to ONE built-in message format.

Built-in format (the same as the Anthropic Messages API, so saved sessions stay readable):
  message  = {"role": "user" | "assistant", "content": str | [block, ...]}
  block    = {"type": "text", "text": ...}
           | {"type": "tool_use", "id": ..., "name": ..., "input": {...}}
           | {"type": "tool_result", "tool_use_id": ..., "content": str}
  response = {"content": [block, ...], "stop_reason": "end_turn" | "tool_use" | "max_tokens",
              "usage": {"input_tokens": n, "output_tokens": n}}

LLM_PROVIDER=anthropic          Messages API with tools.
LLM_PROVIDER=openai_compatible  Chat Completions with tools; LLM_BASE_URL selects the service, so the same code serves
                                OpenAI, xAI, Google's OpenAI-compatible endpoint, LM Studio, Ollama and similar.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request

from . import config, tools

ANTHROPIC_URL = "https://api.anthropic.com"
OPENAI_URL = "https://api.openai.com/v1"
LLM_TIMEOUT_S = 120


class LlmError(tools.ToolError):
    """A model call problem, described without any key or URL."""


def provider_name() -> str:
    p = (config.get("LLM_PROVIDER") or "anthropic").lower().replace("-", "_")
    if p not in ("anthropic", "openai_compatible"):
        raise LlmError("LLM_PROVIDER must be anthropic or openai_compatible")
    return p


def _is_local(url: str) -> bool:
    return urllib.parse.urlparse(url).hostname in ("127.0.0.1", "localhost", "::1")


def _post(url: str, headers: dict, payload: dict) -> dict:
    u = urllib.parse.urlparse(url)
    if not (u.scheme == "https" or (u.scheme == "http" and _is_local(url))):
        raise LlmError("LLM_BASE_URL must start with https:// (plain http is allowed only for localhost)")
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers={"content-type": "application/json", **headers})
    try:
        with urllib.request.urlopen(req, timeout=config.get_int("LLM_TIMEOUT_S", LLM_TIMEOUT_S), context=config.ssl_context()) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        detail = config.redact(e.read().decode("utf-8", "ignore"))[:300]
        e.close()
        raise LlmError(f"model call failed (HTTP {e.code}): {detail}")
    except Exception as e:
        raise LlmError(f"model call failed ({type(e).__name__})")


def check_key(key: str) -> None:
    if key.startswith("sk-ant-oat"):
        raise LlmError("LLM_API_KEY holds a login (OAuth) token from a chat app, which the API does not accept. "
                       "Create an API key in the provider's console (it starts with sk-ant-api) and put that in .env")


# ---------- Anthropic ----------

def call_anthropic(messages: list, system: str, use_tools: bool = True) -> dict:
    key, model = config.get("LLM_API_KEY"), config.get("LLM_MODEL")
    if not key or not model:
        raise LlmError("LLM_API_KEY and LLM_MODEL must be set in .env (or run with --demo for the scripted stand-in)")
    check_key(key)
    payload = {"model": model, "max_tokens": config.get_int("MAX_OUTPUT_TOKENS", 8000), "system": system,
               "messages": messages}
    if use_tools:
        payload["tools"] = tools.schemas()
    base = (config.get("LLM_BASE_URL") or ANTHROPIC_URL).rstrip("/")
    return _post(base + "/v1/messages", {"x-api-key": key, "anthropic-version": "2023-06-01"}, payload)


# ---------- OpenAI-compatible ----------

def to_openai_messages(messages: list, system: str) -> list:
    out = [{"role": "system", "content": system}]
    for m in messages:
        c = m["content"]
        if isinstance(c, str):
            out.append({"role": m["role"], "content": c})
            continue
        if m["role"] == "assistant":
            text = "".join(b.get("text", "") for b in c if b.get("type") == "text")
            calls = [{"id": b["id"], "type": "function",
                      "function": {"name": b["name"], "arguments": json.dumps(b.get("input") or {})}}
                     for b in c if b.get("type") == "tool_use"]
            msg = {"role": "assistant", "content": text or None}
            if calls:
                msg["tool_calls"] = calls
            out.append(msg)
        else:
            for b in c:  # tool results first, in order, then any plain text from the PM
                if b.get("type") == "tool_result":
                    out.append({"role": "tool", "tool_call_id": b["tool_use_id"], "content": str(b.get("content", ""))})
            text = "\n".join(b.get("text", "") for b in c if b.get("type") == "text")
            if text:
                out.append({"role": "user", "content": text})
    return out


def to_openai_tools(schemas: list) -> list:
    return [{"type": "function", "function": {"name": s["name"], "description": s["description"],
                                              "parameters": s["input_schema"]}} for s in schemas]


def from_openai_response(resp: dict) -> dict:
    try:
        choice = resp["choices"][0]
        msg = choice["message"]
    except (KeyError, IndexError, TypeError):
        raise LlmError("the model service answered in an unexpected format")
    blocks = []
    if msg.get("content"):
        blocks.append({"type": "text", "text": msg["content"]})
    for tc in msg.get("tool_calls") or []:
        fn = tc.get("function") or {}
        try:
            args = json.loads(fn.get("arguments") or "{}")
        except ValueError:
            args = {}
        blocks.append({"type": "tool_use", "id": tc.get("id") or f"call_{len(blocks)}", "name": fn.get("name", ""),
                       "input": args if isinstance(args, dict) else {}})
    finish = choice.get("finish_reason")
    stop = "max_tokens" if finish == "length" else "tool_use" if any(b["type"] == "tool_use" for b in blocks) else "end_turn"
    u = resp.get("usage") or {}
    return {"content": blocks, "stop_reason": stop,
            "usage": {"input_tokens": u.get("prompt_tokens", 0), "output_tokens": u.get("completion_tokens", 0)}}


def call_openai_compatible(messages: list, system: str, use_tools: bool = True) -> dict:
    key, model = config.get("LLM_API_KEY"), config.get("LLM_MODEL")
    base = (config.get("LLM_BASE_URL") or OPENAI_URL).rstrip("/")
    if not model:
        raise LlmError("LLM_MODEL must be set in .env (or run with --demo for the scripted stand-in)")
    if not key and not _is_local(base):
        raise LlmError("LLM_API_KEY must be set in .env (only a local server on localhost may run without one)")
    check_key(key)
    payload = {"model": model, config.get("LLM_TOKENS_PARAM", "max_tokens"): config.get_int("MAX_OUTPUT_TOKENS", 8000),
               "messages": to_openai_messages(messages, system)}
    if use_tools:
        payload["tools"] = to_openai_tools(tools.schemas())
    headers = {"authorization": f"Bearer {key}"} if key else {}
    return from_openai_response(_post(base + "/chat/completions", headers, payload))


def get_llm():
    """The model function for the configured provider: llm(messages, system, use_tools=True) -> response."""
    return call_anthropic if provider_name() == "anthropic" else call_openai_compatible
