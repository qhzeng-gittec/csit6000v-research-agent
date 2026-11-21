"""Loop tests with a scripted model: no network, deterministic."""
import json

import pytest

from agent.llm import Reply
from agent.loop import run_agent
from agent.prompts import system_prompt
from agent.tools import Tools
from agent.trace import Trace, read_trace
from agent.verify import Corpus

P = (
    "PrefixMix stores K prefix caches, one per source domain. At inference time it computes a\n"
    "mixing weight for each cache using a lightweight router with 2.1M parameters. The router\n"
    "is trained for 3 epochs with a learning rate of 2e-4 and a batch size of 64.\n"
)
BAD = '"the mixing weight for each cache using a lightweight router" (p.txt)'
GOOD = '"a mixing weight for each cache using a lightweight router" (p.txt)'


def say(content="", *calls):
    msg = {"role": "assistant", "content": content}
    if calls:
        msg["tool_calls"] = [
            {"id": f"c{i}", "type": "function", "function": {"name": n, "arguments": json.dumps(a)}}
            for i, (n, a) in enumerate(calls)
        ]
    return Reply(msg, {"prompt_tokens": 100, "completion_tokens": 10, "cache_hit_tokens": 80}, 1)


class FakeLLM:
    def __init__(self, script):
        self.script, self.tool_lists, self.histories = list(script), [], []

    def chat(self, messages, tools=None, reasoning_budget=None):
        self.budgets = getattr(self, "budgets", []) + [reasoning_budget]
        self.tool_lists.append(json.dumps(tools, sort_keys=True))
        self.histories.append([json.dumps(m, sort_keys=True) for m in messages])
        return self.script.pop(0)


@pytest.fixture
def setup(tmp_path):
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    (corpus / "p.txt").write_text(P, encoding="utf-8")
    return corpus, tmp_path / "trace.jsonl"


def go(setup, script, **kw):
    corpus, tpath = setup
    llm = FakeLLM(script)
    trace = Trace(tpath)
    res = run_agent("q?", llm, Tools(corpus), trace, system_prompt("quote"), cite="quote",
                    corpus=Corpus(corpus), **kw)
    trace.close()
    return res, llm, read_trace(tpath)


READ = ("read", {"path": "p.txt"})


def test_misquote_is_fixed_by_local_edit(setup):
    res, llm, events = go(setup, [
        say("", READ),
        say(f"The router uses a mixing weight. {BAD}"),
        say("", ("edit_draft", {"old": "the mixing weight", "new": "a mixing weight"})),
        say("Done"),
    ])
    assert res.status == "answered" and res.revisions == 1 and res.edits == 1
    assert res.answer == f"The router uses a mixing weight. {GOOD}"
    assert (res.first_draft_issues, res.final_issues) == (1, 0)
    assert res.cache_hit_tokens == 320
    assert [e["ok"] for e in events if e["type"] == "verdict"] == [False, True]


def test_tool_list_and_history_prefix_never_change(setup):
    _, llm, _ = go(setup, [
        say("", READ),
        say(BAD),
        say("", ("edit_draft", {"old": "the mixing weight", "new": "a mixing weight"})),
        say("Done"),
    ])
    assert len(set(llm.tool_lists)) == 1                      # tool list fixed for the whole run
    for prev, nxt in zip(llm.histories, llm.histories[1:]):   # history is append-only
        assert nxt[: len(prev)] == prev


def test_gate_off_reports_issue_but_does_not_revise(setup):
    res, _, events = go(setup, [say("", READ), say(BAD)], gate=False)
    assert res.status == "answered" and res.revisions == 0 and res.answer == BAD
    assert (res.first_draft_issues, res.final_issues) == (1, 1)
    assert [e["type"] for e in events].count("verdict") == 1


def test_edit_draft_refused_before_revision_mode(setup):
    res, _, events = go(setup, [
        say("", READ),
        say("", ("edit_draft", {"old": "x", "new": "y"})),
        say(GOOD),
    ])
    refused = [e for e in events if e["type"] == "tool" and e["name"] == "edit_draft"][0]
    assert refused["is_error"] and "revision mode" in refused["content"]
    assert res.status == "answered" and res.revisions == 0


def test_unresolved_after_max_revisions(setup):
    res, _, _ = go(setup, [say("", READ), say(BAD), say("Done"), say("Done")], max_revisions=2)
    assert res.status == "unresolved" and res.revisions == 2 and res.final_issues == 1
    assert res.answer == BAD  # the unfixed draft is returned, flagged as unresolved


def test_answer_without_reading_is_flagged_unseen(setup):
    res, _, events = go(setup, [say(GOOD)], gate=False)
    assert res.first_draft_issues == 1
    assert [i["kind"] for e in events if e["type"] == "verdict" for i in e["issues"]] == ["quote_unseen"]


def test_require_cite_nudges_an_uncited_answer_once(setup):
    plain = "The router has 2.1M parameters and is trained for 3 epochs."
    quoted = plain + ' "a lightweight router with 2.1M parameters" (p.txt)'
    res, _, events = go(setup, [
        say("", READ),
        say(plain),
        say("", ("edit_draft", {"old": plain, "new": quoted})),
        say("Done"),
    ], gate=False, require_cite=True)
    assert res.revisions == 1 and res.answer == quoted and res.citations == 1
    fb = [e for e in events if e.get("note") == "verification"]
    assert len(fb) == 1 and "no_citation" in fb[0]["content"]


def test_require_cite_never_nudges_twice_and_ignores_bad_quotes_without_gate(setup):
    plain = "The router has 2.1M parameters."
    res, _, _ = go(setup, [say("", READ), say(plain), say("Done")], gate=False, require_cite=True)
    assert res.revisions == 1 and res.status == "answered" and res.answer == plain
    res, _, _ = go(setup, [say("", READ), say(BAD)], gate=False, require_cite=True)
    assert res.revisions == 0 and res.final_issues == 1  # failed quote: logged, not sent back


def test_empty_reply_is_sent_back_then_answered(setup):
    res, llm, tr = go(setup, [say("", READ), say(""), say("PrefixMix uses " + GOOD + ".")], gate=False)
    assert res.status == "answered" and "PrefixMix" in res.answer and res.steps == 3
    assert [e["note"] for e in tr if e.get("note") == "empty_reply"] == ["empty_reply"]
    assert llm.budgets == [None, None, 4000]  # only the retry caps the thinking budget


def test_persistent_empty_reply_ends_as_empty_not_answered(setup):
    res, _, tr = go(setup, [say("", READ), say(""), say("  "), say("")], gate=False)
    assert res.status == "empty" and res.answer == ""
    assert sum(e.get("note") == "empty_reply" for e in tr) == 2  # bounded: MAX_EMPTY_RETRIES
