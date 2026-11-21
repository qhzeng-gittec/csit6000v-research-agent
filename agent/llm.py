"""Thin OpenAI-compatible chat client. Model / endpoint come from env vars."""
from __future__ import annotations

import os
import time
from dataclasses import dataclass

from openai import BadRequestError, OpenAI


@dataclass
class LLMConfig:
    base_url: str
    api_key: str
    model: str
    temperature: float = 0.0
    # Cap per call (reasoning + answer). Small reasoning models can otherwise "think" until the
    # context limit (we saw 131k-token calls taking ~20 min with an empty answer).
    max_tokens: int = 16384

    @classmethod
    def from_env(cls) -> "LLMConfig":
        key = os.environ.get("LLM_API_KEY") or os.environ.get("DEEPSEEK_API_KEY")
        if not key:
            raise SystemExit("Set LLM_API_KEY (or DEEPSEEK_API_KEY) in the environment.")
        return cls(
            base_url=os.environ.get("LLM_BASE_URL", "https://api.deepseek.com"),
            api_key=key,
            model=os.environ.get("LLM_MODEL", "deepseek-flash"),
            temperature=float(os.environ.get("LLM_TEMPERATURE", "0")),
            max_tokens=int(os.environ.get("LLM_MAX_TOKENS", "16384")),
        )


@dataclass
class Reply:
    message: dict  # assistant message, ready to append to the history
    usage: dict
    latency_ms: int


def parse_usage(u) -> dict:
    """prompt/completion tokens plus prefix-cache hit/miss tokens when the server reports them.

    DeepSeek reports `prompt_cache_hit_tokens` / `prompt_cache_miss_tokens`; OpenAI-style servers
    report `prompt_tokens_details.cached_tokens`. Missing fields are simply omitted.
    """
    if not u:
        return {}
    d = {"prompt_tokens": u.prompt_tokens, "completion_tokens": u.completion_tokens}
    extra = getattr(u, "model_extra", None) or {}
    hit = extra.get("prompt_cache_hit_tokens")
    miss = extra.get("prompt_cache_miss_tokens")
    if hit is None:
        details = getattr(u, "prompt_tokens_details", None)
        hit = getattr(details, "cached_tokens", None) if details else None
    if hit is not None:
        d["cache_hit_tokens"] = hit
        d["cache_miss_tokens"] = miss if miss is not None else u.prompt_tokens - hit
    return d


class LLM:
    def __init__(self, cfg: LLMConfig):
        self.cfg = cfg
        timeout = float(os.environ.get("LLM_TIMEOUT_S", "120"))
        self.client = OpenAI(base_url=cfg.base_url, api_key=cfg.api_key, max_retries=3, timeout=timeout)

    def chat(self, messages: list[dict], tools: list[dict] | None = None,
             reasoning_budget: int | None = None) -> Reply:
        """reasoning_budget: cap on thinking tokens (OpenRouter `reasoning.max_tokens`); used only when
        retrying an empty reply. Providers that reject the field get the plain request."""
        kwargs = dict(model=self.cfg.model, messages=messages, temperature=self.cfg.temperature,
                      max_tokens=self.cfg.max_tokens)
        if tools:
            kwargs["tools"] = tools
        start = time.monotonic()
        if reasoning_budget:
            try:
                resp = self.client.chat.completions.create(
                    **kwargs, extra_body={"reasoning": {"max_tokens": reasoning_budget}})
            except BadRequestError:
                resp = self.client.chat.completions.create(**kwargs)
        else:
            resp = self.client.chat.completions.create(**kwargs)
        latency = int((time.monotonic() - start) * 1000)
        m = resp.choices[0].message
        message: dict = {"role": "assistant", "content": m.content or ""}
        if m.tool_calls:
            message["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                }
                for tc in m.tool_calls
            ]
        usage = parse_usage(resp.usage)
        usage["finish_reason"] = resp.choices[0].finish_reason  # "length" = hit max_tokens
        return Reply(message=message, usage=usage, latency_ms=latency)
