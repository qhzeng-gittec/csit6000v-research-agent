"""Preflight on TACC: one request with the agent's tool list must come back as a structured tool call."""
import json
import sys

from agent.llm import LLM, LLMConfig
from agent.tools import Tools

tools = Tools(".")
reply = LLM(LLMConfig.from_env()).chat(
    [{"role": "system", "content": "Inspect files with the tools before you answer."},
     {"role": "user", "content": "Use the bash tool to list the files in the working directory."}],
    tools.schemas())
print(json.dumps({"message": reply.message, "usage": reply.usage, "latency_ms": reply.latency_ms}, ensure_ascii=False))
calls = reply.message.get("tool_calls") or []
if not calls or calls[0]["function"]["name"] not in tools.ALL:
    sys.exit("PREFLIGHT FAILED: the reply has no structured tool call (is tool calling enabled on the service?)")
result = tools.call(calls[0]["function"]["name"], json.loads(calls[0]["function"]["arguments"]))
print("tool result:", result.text[:300].replace("\n", " | "))
if result.is_error:
    sys.exit("PREFLIGHT FAILED: the tool call did not run")
print("PREFLIGHT OK")
