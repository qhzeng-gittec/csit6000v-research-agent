"""LLM client config: extra request fields reach every request. No network."""
from types import SimpleNamespace

from agent.llm import LLM, LLMConfig


def _resp():
    msg = SimpleNamespace(content="ok", tool_calls=None)
    return SimpleNamespace(choices=[SimpleNamespace(message=msg, finish_reason="stop")], usage=None)


def test_extra_body_from_env(monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "k")
    monkeypatch.setenv("LLM_EXTRA_BODY", '{"chat_template_kwargs": {"enable_thinking": false}}')
    assert LLMConfig.from_env().extra_body == {"chat_template_kwargs": {"enable_thinking": False}}
    monkeypatch.delenv("LLM_EXTRA_BODY")
    assert LLMConfig.from_env().extra_body is None


def test_extra_body_is_sent_with_every_call():
    llm = LLM(LLMConfig("http://x/v1", "k", "m", extra_body={"a": 1}))
    seen = []
    llm.client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(
        create=lambda **kw: seen.append(kw.get("extra_body")) or _resp())))
    llm.chat([{"role": "user", "content": "hi"}])
    llm.chat([{"role": "user", "content": "hi"}], reasoning_budget=100)
    assert seen == [{"a": 1}, {"a": 1, "reasoning": {"max_tokens": 100}}]


def test_retry_body_replaces_the_default_reasoning_cap():
    llm = LLM(LLMConfig("http://x/v1", "k", "m", retry_body={"chat_template_kwargs": {"enable_thinking": False}}))
    seen = []
    llm.client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(
        create=lambda **kw: seen.append(kw.get("extra_body")) or _resp())))
    llm.chat([{"role": "user", "content": "hi"}])
    llm.chat([{"role": "user", "content": "hi"}], reasoning_budget=100)
    assert seen == [None, {"chat_template_kwargs": {"enable_thinking": False}}]


def test_temperature_is_left_out_when_the_setting_is_empty(monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "k")
    monkeypatch.setenv("LLM_TEMPERATURE", "")
    cfg = LLMConfig.from_env()
    assert cfg.temperature is None
    seen = []
    llm = LLM(cfg)
    llm.client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(
        create=lambda **kw: seen.append(kw) or _resp())))
    llm.chat([{"role": "user", "content": "hi"}])
    assert "temperature" not in seen[0]
    monkeypatch.delenv("LLM_TEMPERATURE")
    assert LLMConfig.from_env().temperature == 0.0


def test_no_extra_body_by_default():
    llm = LLM(LLMConfig("http://x/v1", "k", "m"))
    seen = []
    llm.client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(
        create=lambda **kw: seen.append(kw.get("extra_body")) or _resp())))
    llm.chat([{"role": "user", "content": "hi"}])
    assert seen == [None]
