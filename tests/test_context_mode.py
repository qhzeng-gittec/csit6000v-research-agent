"""Benchmark protocol: document in the prompt, quote citations, verifier gate (B0/C1/C2)."""
import json

import pandas as pd
import pytest

from agent.bench import gate_summary, paired, parse_run_name, parse_sentence_labels
from agent.llm import Reply
from agent.loop import run_agent
from agent.prompts import system_prompt
from agent.tools import Tools
from agent.trace import Trace, read_trace
from agent.verify import Corpus, verify

DOC = "The router is trained for 3 epochs with a learning rate of 2e-4 and a batch size of 64."


# ---------------------------------------------------------------- citations are optional
@pytest.mark.parametrize("ans", [
    "I read the whole document; it never names the carbohydrate.\n\nAnswer: unknown",
    "Answer: 3 epochs",
    "Many claims. " * 60,
])
def test_uncited_answers_are_never_sent_back(tmp_path, ans):
    (tmp_path / "doc.txt").write_text(DOC, encoding="utf-8")
    assert verify(ans, "quote", Corpus(tmp_path), []) == []


def test_given_citations_must_still_check_out(tmp_path):
    (tmp_path / "doc.txt").write_text(DOC, encoding="utf-8")
    seen = [{"type": "tool", "name": "read", "args": {"path": "doc.txt"}, "content": DOC, "is_error": False}]
    ans = 'Uncited sentence. Cited one: "trained for 5 epochs" (doc.txt)'
    assert [i.kind for i in verify(ans, "quote", Corpus(tmp_path), seen)] == ["quote_not_found"]


# ---------------------------------------------------------------- tool filter
def test_enabled_filter_controls_schemas_and_calls(tmp_path):
    t = Tools(tmp_path, enabled=("edit_draft",))
    assert [s["function"]["name"] for s in t.schemas()] == ["edit_draft"]
    assert t.call("bash", {"command": "ls"}).is_error
    assert Tools(tmp_path, enabled=()).schemas() == []


def test_system_prompt_modes():
    ctx = system_prompt("quote", "context")
    assert "user\nmessage" in ctx or "user message" in ctx.replace("\n", " ")
    assert "bash" not in ctx and "edit_draft" in ctx and "needs no citation" in ctx
    assert "edit_draft" not in system_prompt("none", "context")


# ---------------------------------------------------------------- loop in context mode
def say(content="", *calls):
    msg = {"role": "assistant", "content": content}
    if calls:
        msg["tool_calls"] = [{"id": f"c{i}", "type": "function", "function": {"name": n, "arguments": json.dumps(a)}}
                             for i, (n, a) in enumerate(calls)]
    return Reply(msg, {"prompt_tokens": 100, "completion_tokens": 10}, 1)


class FakeLLM:
    def __init__(self, script):
        self.script, self.tools = list(script), []

    def chat(self, messages, tools=None):
        self.tools.append(tools)
        return self.script.pop(0)


def go(tmp_path, script, gate, enabled=("edit_draft",)):
    (tmp_path / "doc.txt").write_text(DOC, encoding="utf-8")
    seed = [{"type": "tool", "name": "read", "args": {"path": "doc.txt"}, "content": DOC, "is_error": False}]
    llm, trace = FakeLLM(script), Trace(tmp_path / "t.jsonl")
    res = run_agent("q", llm, Tools(tmp_path, enabled=enabled), trace, system_prompt("quote", "context"),
                    cite="quote", corpus=Corpus(tmp_path), gate=gate, seed_events=seed)
    trace.close()
    return res, llm, read_trace(tmp_path / "t.jsonl")


GOOD = '"trained for 3 epochs with a learning rate of 2e-4" (doc.txt)'
BAD = '"trained for 5 epochs with a learning rate of 2e-4" (doc.txt)'


def test_document_in_prompt_counts_as_read(tmp_path):
    res, _, _ = go(tmp_path, [say(f"Answer: 2e-4 {GOOD}")], gate=True)
    assert res.status == "answered" and res.first_draft_issues == 0


def test_c1_logs_but_does_not_revise(tmp_path):
    res, llm, ev = go(tmp_path, [say(f"Answer: 2e-4 {BAD}")], gate=False)
    assert res.revisions == 0 and res.first_draft_issues == 1 and res.answer.endswith(BAD)
    assert [e["type"] for e in ev].count("verdict") == 1


def test_c2_revises_locally_with_only_edit_draft_offered(tmp_path):
    res, llm, _ = go(tmp_path, [
        say(f"Answer: 2e-4 {BAD}"),
        say("", ("edit_draft", {"old": "5 epochs", "new": "3 epochs"})),
        say("Done"),
    ], gate=True)
    assert res.status == "answered" and res.revisions == 1 and res.final_issues == 0
    assert res.answer == f"Answer: 2e-4 {GOOD}"
    names = [[t["function"]["name"] for t in ts] for ts in llm.tools]
    assert names == [["edit_draft"]] * 3  # identical tool list on every call


def test_b0_sends_no_tools(tmp_path):
    (tmp_path / "doc.txt").write_text(DOC, encoding="utf-8")
    llm, trace = FakeLLM([say("Answer: 2e-4")]), Trace(tmp_path / "t.jsonl")
    res = run_agent("q", llm, Tools(tmp_path, enabled=()), trace, system_prompt("none", "context"),
                    cite="none", corpus=Corpus(tmp_path), gate=False)
    trace.close()
    assert res.steps == 1 and not llm.tools[0]  # [] or None -> no tools parameter sent


# ---------------------------------------------------------------- C3: grounding judge
class JudgeLLM:
    def __init__(self, outputs):
        self.outputs, self.calls = list(outputs), 0

    def chat(self, messages, tools=None):
        self.calls += 1
        out = self.outputs.pop(0)
        if isinstance(out, Exception):
            raise out
        return Reply({"role": "assistant", "content": out}, {}, 1)


def test_grounder_keeps_only_spans_that_are_in_the_draft():
    from agent.ground import Grounder
    draft = "The router uses 3 epochs. It was invented in 1999 by Turing."
    judge = JudgeLLM(['Sure: [{"text": "It was invented in 1999 by Turing.", "problem": "unsupported", '
                      '"reason": "no date in doc"}, {"text": "a span the model never wrote", "problem": "unsupported"}]'])
    issues = Grounder(judge, DOC)(draft)
    assert [(i.kind, i.cited) for i in issues] == [("unsupported_claim", '"It was invented in 1999 by Turing."')]
    assert issues[0].hint == "no date in doc"


def test_grounder_failure_means_pass():
    from agent.ground import Grounder
    g = Grounder(JudgeLLM([RuntimeError("boom"), "not json"]), DOC)
    assert g("anything at all here") == [] and g("anything at all here") == []
    assert g.failures == 1


def test_c3_loop_removes_flagged_claim_with_edit_draft(tmp_path):
    from agent.ground import Grounder
    (tmp_path / "doc.txt").write_text(DOC, encoding="utf-8")
    first = ("Training uses 3 epochs, a learning rate of 2e-4 and a batch size of 64. "
             "It also uses 8 GPUs for training.")
    judge = JudgeLLM(['[{"text": "It also uses 8 GPUs for training.", "problem": "unsupported", "reason": "no GPUs"}]',
                      "[]"])
    llm, trace = FakeLLM([say(first), say("", ("edit_draft", {"old": " It also uses 8 GPUs for training.", "new": ""})),
                          say("Done")]), Trace(tmp_path / "t.jsonl")
    seed = [{"type": "tool", "name": "read", "args": {"path": "doc.txt"}, "content": DOC, "is_error": False}]
    res = run_agent("q", llm, Tools(tmp_path, enabled=("edit_draft",)), trace, system_prompt("quote", "context"),
                    cite="quote", corpus=Corpus(tmp_path), gate=True, seed_events=seed, grounder=Grounder(judge, DOC))
    trace.close()
    assert res.answer == "Training uses 3 epochs, a learning rate of 2e-4 and a batch size of 64."
    assert res.status == "answered"
    assert (res.first_draft_issues, res.final_issues, judge.calls) == (1, 0, 2)


def test_collapse_guard_keeps_first_draft(tmp_path):
    from agent.ground import Grounder
    (tmp_path / "doc.txt").write_text(DOC, encoding="utf-8")
    first = "Short true part. " + "A very long unsupported paragraph that goes on and on. " * 3
    junk = "A very long unsupported paragraph that goes on and on. " * 3
    judge = JudgeLLM([f'[{{"text": "{junk.strip()[:200]}", "problem": "unsupported"}}]', "[]"])
    llm, trace = FakeLLM([say(first), say("", ("edit_draft", {"old": junk.strip()[:200], "new": ""})), say("Done")]), \
        Trace(tmp_path / "t.jsonl")
    seed = [{"type": "tool", "name": "read", "args": {"path": "doc.txt"}, "content": DOC, "is_error": False}]
    res = run_agent("q", llm, Tools(tmp_path, enabled=("edit_draft",)), trace, system_prompt("quote", "context"),
                    cite="quote", corpus=Corpus(tmp_path), gate=True, seed_events=seed, grounder=Grounder(judge, DOC))
    trace.close()
    assert res.status == "collapse_reverted" and res.answer == first


# ---------------------------------------------------------------- scoring helpers
def test_parse_sentence_labels():
    out = "\n".join([
        '{"sentence": "a", "label": "supported", "rationale": "x", "excerpt": "y"}',
        '{"sentence": "b", "label": "unsupported", "rationale": "x", "excerpt": null}',
        "not json at all",
        '{"sentence": "c", "label": "contradictory", "rationale": "x", "excerpt": "z"},',
        '{"sentence": "d", "label": "no_rad", "rationale": "x", "excerpt": null}',
    ])
    c = parse_sentence_labels(out)
    assert (c["supported"], c["unsupported"], c["contradictory"], c["no_rad"]) == (1, 1, 1, 1)
    assert c["unsup_rate"] == pytest.approx(2 / 3)
    assert parse_sentence_labels("Hello!")["unsup_rate"] is None


def test_parse_run_name_with_and_without_rep():
    assert parse_run_name("abc__C2__r1") == ("abc", "C2", 1)
    assert parse_run_name("abc__A0") == ("abc", "A0", 0)
    assert parse_run_name("LEAP__5_10315__C2__r1") == ("LEAP__5_10315", "C2", 1)  # id contains "__"
    assert parse_run_name("LEAP__5_10315__B0") == ("LEAP__5_10315", "B0", 0)


def test_paired_difference_averages_reps_and_counts_flips():
    df = pd.DataFrame([
        # item x: C1 wrong both reps, C2 right both reps -> +1
        ("b", "x", "C1", 0, False), ("b", "x", "C1", 1, False), ("b", "x", "C2", 0, True), ("b", "x", "C2", 1, True),
        # item y: both right -> 0
        ("b", "y", "C1", 0, True), ("b", "y", "C2", 0, True),
        # item z: C1 right, C2 right once of two -> -0.5
        ("b", "z", "C1", 0, True), ("b", "z", "C1", 1, True), ("b", "z", "C2", 0, True), ("b", "z", "C2", 1, False),
        # item w only in C1 -> dropped from the pairing
        ("b", "w", "C1", 0, True),
    ], columns=["bench", "id", "arm", "rep", "correct"])
    r = paired(df, "b", "correct", "C1", "C2")
    assert r["items"] == 3 and r["items_b_higher"] == 1 and r["items_b_lower"] == 1
    assert r["diff_b_minus_a"] == pytest.approx(round(0.5 / 3, 3))
    assert r["ci95_lo"] <= r["diff_b_minus_a"] <= r["ci95_hi"]


def test_gate_summary_counts_flips_only_within_runs():
    cols = ["bench", "arm", "revisions", "correct_first", "correct", "first_draft_valid", "final_valid",
            "unsup_rate_first", "unsup_rate"]
    df = pd.DataFrame([
        ("f", "C2", 1, False, True, False, True, 0.5, 0.1),   # fixed by the gate
        ("f", "C2", 1, True, False, False, True, 0.0, 0.2),   # broken by the gate
        ("f", "C2", 0, True, True, True, True, 0.0, 0.0),     # untouched
        ("f", "C1", 0, False, False, False, False, 0.9, 0.9),  # other arm ignored
    ], columns=cols)
    r = gate_summary(df, "C2").iloc[0]
    assert (r.runs, r.revised, r.fixed, r.broken) == (3, 2, 1, 1)
    assert r.cite_valid_first == pytest.approx(1 / 3, abs=1e-3) and r.cite_valid_final == 1.0
    assert r.unsup_first_on_revised == 0.25 and r.unsup_final_on_revised == 0.15 and r.unsup_diff == -0.1
