from agent.bench import (answer_line, norm, parse_verdict, score_rule, task_text, wrap_doc, Example,
                         _clean_prompt)
from agent.tools import MAX_OUTPUT_CHARS, Tools


def test_norm_follows_faitheval_convention():
    assert norm("The  Answer_is: UNKNOWN!") == "answer is unknown"


def test_answer_line_extraction():
    assert answer_line("blah\nAnswer: unknown\n> quote") == "unknown"
    assert answer_line("**Answer:** B") == "B"
    assert answer_line("no such line") is None


def test_unanswerable_strict_vs_loose():
    assert score_rule("faith_unans", "Answer: unknown\n\"x\" (doc.txt)", {})["correct"]
    r = score_rule("faith_unans", "Answer: He did not say", {})
    assert not r["correct"] and r["correct_loose"]  # 'not' is why strict is the primary number
    assert not score_rule("faith_unans", "Answer: Buyantu", {})["correct_loose"]


def test_quotes_after_answer_line_do_not_leak_into_the_match():
    ans = 'Answer: Hulu\n\n> "the study is inconclusive, the result is unknown" (doc.txt)'
    assert not score_rule("faith_unans", ans, {})["correct"]


def test_inconsistent_conflict():
    assert score_rule("faith_incons", "Answer: conflict", {})["correct"]
    assert not score_rule("faith_incons", "Answer: Sky", {})["correct"]
    assert score_rule("faith_incons", "Answer: the document contradicts itself", {})["correct_loose"] is False
    assert score_rule("faith_incons", "Answer: contradictory sources", {})["correct_loose"]


def test_counterfactual_letter():
    gold = {"answerKey": "D"}
    assert score_rule("faith_cf", "Answer: D", gold)["correct"]
    assert score_rule("faith_cf", "Answer: (d) Planetary gravity", gold)["correct"]
    assert not score_rule("faith_cf", "Answer: C", gold)["correct"]
    r = score_rule("faith_cf", "I think it is D", gold)  # no `Answer:` line -> flagged and not credited
    assert not r["correct"] and not r["format_ok"]


def test_parse_verdict_takes_last():
    assert parse_verdict("Inaccurate claims... finally: Accurate") is True
    assert parse_verdict("... so the response is Inaccurate") is False
    assert parse_verdict("no verdict") is None


def test_clean_facts_prompt_cell():
    assert _clean_prompt('"line1\\nline2"') == "line1\nline2"


def test_wrap_doc_keeps_paragraphs_and_width():
    out = wrap_doc("word " * 60 + "\n\nshort", width=40)
    assert max(len(line) for line in out.splitlines()) <= 40 and "\n\nshort" in out


def test_task_text_differs_by_mode():
    ex = Example("faith_cf", "x", "Q?", "doc", {"answerKey": "A"}, ["A. one", "B. two"])
    assert "doc.txt" in task_text(ex, inline=False) and "document above" in task_text(ex, inline=True)
    assert "A. one" in task_text(ex, inline=False)


def test_read_cuts_on_line_boundary_and_hints_next_offset(tmp_path):
    (tmp_path / "big.txt").write_text("\n".join("x" * 99 for _ in range(300)), encoding="utf-8")
    r = Tools(tmp_path).read("big.txt")
    assert r.truncated and len(r.text) <= MAX_OUTPUT_CHARS + 200
    shown = [l for l in r.text.splitlines() if "\t" in l]
    assert all(len(l.split("\t", 1)[1]) == 99 for l in shown)  # no half-cut line
    last = int(shown[-1].split("\t")[0])
    assert f"offset={last + 1}" in r.text


def test_evidence_deliverable_hides_excerpts_and_markers():
    from agent.evidence import deliverable, stats
    raw = ('<evidence>\n[E1] "Borrow books from the library." (doc.txt)\n</evidence>\n'
           '<answer>\nBorrow books from the library instead of buying them [E1]. '
           'The document does not mention investing.\n</answer>')
    assert deliverable(raw) == ("Borrow books from the library instead of buying them. "
                                "The document does not mention investing.")
    st = stats(raw)
    assert st["ev_format_ok"] and st["ev_items"] == 1 and st["ev_unmarked_share"] == 0.5


def test_evidence_deliverable_without_tags_is_the_whole_text():
    from agent.evidence import deliverable, stats
    assert deliverable("  plain answer  ") == "plain answer"
    assert stats("plain answer")["ev_format_ok"] is False


def test_evidence_prompt_styles():
    import pytest
    from agent import bench
    from agent.prompts import system_prompt
    p = system_prompt("quote", "files", "evidence")
    assert "<evidence>" in p and "Support every factual claim with a verbatim quote" not in p
    assert "Do not add background knowledge" in system_prompt("quote", "files", "evidence_strict")
    with pytest.raises(ValueError):
        system_prompt("none", "files", "evidence")


def test_strict_plus_style_stacks_on_strict():
    from agent.prompts import system_prompt
    p = system_prompt("quote", "files", "inline_strict_plus")
    assert "Do not add background knowledge" in p and "Do not expand abbreviations" in p
    assert "verbatim quote" in p


def test_held_out_ids_reads_run_dirs(tmp_path):
    from agent.bench import held_out_ids
    for name in ("facts0002__A0__r0", "facts0002__A8__r1", "LEAP__5_1__A0__r0"):
        (tmp_path / "dev" / "facts" / name).mkdir(parents=True)
    assert held_out_ids(tmp_path, ["dev"]) == {"facts0002", "LEAP__5_1"}
    assert held_out_ids(tmp_path, []) == set()


def test_strip_quotes_keeps_only_own_words():
    from agent.evidence import strip_quotes
    text = ('Borrow books from the library to save money. "Borrow books and movies from the library" (doc.txt)\n'
            '- The document says: "Instead of paying for a fitness club membership, exercise outdoors." (doc.txt)\n'
            'It also lists "a short one" as a tip.')
    out = strip_quotes(text)
    assert out == 'Borrow books from the library to save money.\nIt also lists "a short one" as a tip.'


def test_plain_style_has_rules_but_no_citation():
    import pytest
    from agent import bench
    from agent.prompts import system_prompt
    p = system_prompt("none", "files", "plain_strict_plus")
    assert "Do not expand abbreviations" in p and "verbatim quote" not in p and "edit_draft" not in p
    with pytest.raises(ValueError):
        system_prompt("quote", "files", "plain_strict_plus")
    with pytest.raises(ValueError):
        system_prompt("none", "files", "inline_strict")


def test_official_protocol_pieces():
    from agent.bench import FILE_NOTE, _fill_official, agent_request, parse_rubric
    ex = {"question": "Q?", "doc": "D"}
    filled = _fill_official("{{user_request}}|{{context_document}}|{{response}}", ex, "R")
    assert filled == f"{agent_request(ex)}|{FILE_NOTE}D|R" and "doc.txt" in agent_request(ex)
    assert parse_rubric('... "Minor Issue(s)" ... final: {"Instruction Following": "Major Issue(s)"}') == "Major Issue(s)"
    assert parse_rubric("no verdict") is None


def test_official_score_is_all_or_nothing(monkeypatch):
    from agent import bench
    monkeypatch.setattr(bench, "JUDGE_NOTE", "J0")  # toy template has no note anchor

    class J:
        def __init__(self, outs): self.outs = list(outs)
        def chat(self, messages):
            from agent.llm import Reply
            return Reply({"role": "assistant", "content": self.outs.pop(0)}, {}, 1)

    ok = '{"sentence": "a", "label": "supported"}\n{"sentence": "b", "label": "no_rad"}'
    bad = '{"sentence": "a", "label": "supported"}\n{"sentence": "b", "label": "unsupported"}'
    ex = {"question": "Q", "doc": "D"}
    s = bench.score_facts_official(ex, "R", J([ok, '"No Issues"']), "{{response}}", "{{response_a}}", "B")
    assert s["accurate"] and s["eligible"] and s["correct"]
    s = bench.score_facts_official(ex, "R", J([bad, '"No Issues"']), "{{response}}", "{{response_a}}", "B")
    assert not s["accurate"] and not s["correct"]
    s = bench.score_facts_official(ex, "R", J([ok, '"Major Issue(s)"']), "{{response}}", "{{response_a}}", "B")
    assert s["accurate"] and not s["eligible"] and not s["correct"]
    # the baseline arm itself: one judge call only (sentences), counted eligible
    s = bench.score_facts_official(ex, "R", J([ok]), "{{response}}", "{{response_a}}", None)
    assert s["correct"] and s["eligibility_verdict"] == "self"


def test_judge_note_is_inserted_before_the_input_section():
    from agent import bench
    tpl = "rules\n**Now, please analyze the following context and response:**\n{{response}}"
    out = bench.with_judge_note(tpl, bench.JUDGE_NOTES["J2"])
    assert out.index("Note on the setting") < out.index("**Now, please analyze")
    assert bench.with_judge_note(tpl, "") == tpl


def test_neutralize_removes_file_name_but_keeps_content():
    from agent.judge_check import neutralize
    s = 'According to `doc.txt`, X rose "by 5%" (doc.txt, lines 3-5).'
    assert neutralize(s) == 'According to the document, X rose "by 5%".'


def test_split_files_reproduce_the_sampled_splits():
    """The shipped split files equal what --n/--seed/--exclude picked (needs the downloaded data)."""
    import pytest
    from agent import bench
    if not (bench.DATA / "facts_examples.csv").exists():
        pytest.skip("benchmark data not downloaded")
    dev = [ex.id for ex in bench.pick_examples("facts", 30, 1, set())]
    test = [ex.id for ex in bench.pick_examples("facts", 100, 2, set(dev))]
    assert [ex.id for ex in bench.examples_by_id("facts", "splits/facts_dev30.txt")] == sorted(dev)
    assert [ex.id for ex in bench.examples_by_id("facts", "splits/facts_test100.txt")] == sorted(test)


def test_official_score_rejects_cut_off_or_empty_judge_output(monkeypatch):
    import pytest
    from agent import bench
    from agent.llm import Reply
    monkeypatch.setattr(bench, "JUDGE_NOTE", "J0")

    class J:
        def __init__(self, content, finish): self.reply = Reply({"role": "assistant", "content": content}, {"finish_reason": finish}, 1)
        def chat(self, messages): return self.reply

    ex = {"question": "Q", "doc": "D"}
    for content, finish in (("", "length"), ('{"sentence": "a", "label": "supported"}', "length"), ("no labels here", "stop")):
        with pytest.raises(RuntimeError):
            bench.score_facts_official(ex, "R", J(content, finish), "{{response}}", "{{response_a}}", None)
    # an empty answer is still scored here; score_one marks it incorrect afterwards
    assert bench.score_facts_official(ex, "", J("", "stop"), "{{response}}", "{{response_a}}", None)["accurate"]


def test_named_judge_scores_are_kept_next_to_the_default_ones(tmp_path, monkeypatch):
    import json
    from agent import bench
    from agent.llm import Reply
    monkeypatch.setattr(bench, "JUDGE_NOTE", "J0")
    run_dir = tmp_path / "facts" / "facts0001__A0__r0"
    run_dir.mkdir(parents=True)
    (run_dir / "meta.json").write_text(json.dumps({"arm": "A0", "status": "answered"}))
    (run_dir / "example.json").write_text(json.dumps({"bench": "facts", "id": "facts0001", "question": "Q", "doc": "D"}))
    (run_dir / "answer.md").write_text("An answer.")
    (run_dir / "score_official.json").write_text(json.dumps({"kept": True}))

    class J:
        def chat(self, messages):
            return Reply({"role": "assistant", "content": '{"sentence": "a", "label": "unsupported"}'}, {"finish_reason": "stop"}, 1)

    row = bench.score_one(run_dir, J(), ("", "{{response}}", "{{response_a}}"), "official", "second")
    assert row["correct"] is False
    assert json.loads((run_dir / "score_official_second.json").read_text())["sent_unsupported"] == 1
    assert json.loads((run_dir / "score_official.json").read_text()) == {"kept": True}
