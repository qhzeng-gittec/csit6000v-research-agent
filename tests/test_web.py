"""Web UI on saved runs and on a scripted model: no network, no key."""
import json
import threading
import urllib.error
import urllib.request
from pathlib import Path

import pytest

from agent.llm import Reply
from agent.textnorm import normalize
from web import server

RUN = "facts-test100/facts/facts0028__A10__r0"
DOC = "The committee meets on the first Monday of every month.\nThe annual budget of the committee is 12,000 dollars.\n"
BAD = '"the committee meets every second Tuesday" (doc.txt)'
GOOD = '"The committee meets on the first Monday of every month" (doc.txt)'


@pytest.fixture
def base():
    httpd = server.Server(("127.0.0.1", 0), server.Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{httpd.server_address[1]}"
    httpd.shutdown()


def get(url):
    return json.load(urllib.request.urlopen(url))


def stream(url):
    with urllib.request.urlopen(url) as resp:
        return [json.loads(line[6:]) for line in resp.read().decode().splitlines() if line.startswith("data: ")]


def post(url, body):
    req = urllib.request.Request(url, json.dumps(body).encode(), {"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req))


def test_result_marks_every_quote_and_locates_it_in_the_document():
    r = server.result(Path("runs") / RUN)
    doc = server.opening(Path("runs") / RUN, RUN)["doc"]
    assert r["meta"]["status"] == "answered" and r["quotes"] and r["read"] == [[1, 49]]
    for q in r["quotes"]:
        assert q["ok"] and r["answer"][q["start"]] in '"“'
        (a, b), = q["spans"]
        assert normalize(doc[a:b]) == normalize(r["answer"][q["text"][0]:q["text"][1]])


def test_saved_run_refuses_paths_outside_runs():
    assert server.saved_run(RUN) is not None
    assert server.saved_run("../agent") is None and server.saved_run("nope") is None


def test_saved_runs_open_and_replay_without_a_key(base, monkeypatch):
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    assert get(base + "/api/config")["ready"] is False
    row = next(r for r in get(base + "/api/runs") if r["run"] == RUN)
    assert row["full"] and row["revisions"] == 1 and row["title"].startswith("How did the Interim Final Rule")
    events = get(f"{base}/api/run?run={RUN}")
    assert events[0]["type"] == "open" and events[0]["question"] == row["title"] and events[-1]["type"] == "done"
    assert any(e["type"] == "verdict" and not e["ok"] for e in events)
    assert [e["type"] for e in stream(f"{base}/api/replay?run={RUN}&delay=0")] == [e["type"] for e in events]
    for path in ("/", "/app.js", "/app.css"):
        assert urllib.request.urlopen(base + path).status == 200
    with pytest.raises(urllib.error.HTTPError) as refused:
        post(base + "/api/ask", {"question": "When?", "document": DOC})
    assert refused.value.code == 400


def test_a_new_question_streams_every_step_and_is_saved(base, monkeypatch, tmp_path):
    def say(content="", *calls):
        msg = {"role": "assistant", "content": content}
        if calls:
            msg["tool_calls"] = [{"id": f"c{i}", "type": "function", "function": {"name": n, "arguments": json.dumps(a)}}
                                 for i, (n, a) in enumerate(calls)]
        return Reply(msg, {"prompt_tokens": 100, "completion_tokens": 10}, 1)

    script = [say("", ("read", {"path": "doc.txt"})), say(f"It meets monthly: {BAD}."),
              say("", ("edit_draft", {"old": BAD, "new": GOOD})), say("Done")]

    class Scripted:
        def __init__(self, cfg):
            pass

        def chat(self, messages, tools=None, reasoning_budget=None):
            return script.pop(0)

    monkeypatch.setenv("LLM_API_KEY", "test")
    monkeypatch.setattr(server, "LLM", Scripted)
    monkeypatch.setattr(server, "RUNS", tmp_path)
    monkeypatch.setattr(server, "TITLES", {})
    run = post(base + "/api/ask", {"question": "When does it meet?", "document": DOC, "doc_name": "rules.txt"})["run"]
    events = stream(f"{base}/api/live?run={run}")
    assert events[0]["type"] == "open" and events[0]["doc_name"] == "rules.txt"
    assert [e["ok"] for e in events if e["type"] == "verdict"] == [False, True]
    done = events[-1]
    assert done["type"] == "done" and done["meta"]["status"] == "answered" and done["meta"]["revisions"] == 1
    assert [q["ok"] for q in done["quotes"]] == [True] and done["read"] == [[1, 2]]
    saved = get(base + "/api/runs")
    assert [(r["run"], r["title"], r["full"]) for r in saved] == [(f"web/{run}", "When does it meet?", True)]
