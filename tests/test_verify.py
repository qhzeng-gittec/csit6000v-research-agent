import pytest

from agent.tools import Tools
from agent.verify import Corpus, verify

P = (
    "PrefixMix stores K prefix caches, one per source domain. At inference time it computes a\n"
    "mixing weight for each cache using a lightweight router with 2.1M parameters. The router\n"
    "is trained for 3 epochs with a learning rate of 2e-4 and a batch size of 64.\n"
)
GOOD = ("mixing weight for each cache using a lightweight router with 2.1M parameters. "
        "The router is trained for 3 epochs")
BAD = ("the mixing weight for each cache using a lightweight router with 2.1M parameters. "
       "The router is trained for 3 epochs")


@pytest.fixture
def env(tmp_path):
    (tmp_path / "p.txt").write_text(P, encoding="utf-8")
    (tmp_path / "q.txt").write_text("Unrelated sentence that only lives in the other file, honestly.\n", encoding="utf-8")
    tools = Tools(tmp_path)
    r = tools.read("p.txt")
    ev = [{"type": "tool", "name": "read", "args": {"path": "p.txt"}, "content": r.text, "is_error": False}]
    return Corpus(tmp_path), ev


def test_cite_none_never_flags(env):
    c, ev = env
    assert verify("anything", "none", c, ev) == []


def test_exact_quote_spanning_lines_passes(env):
    c, ev = env
    assert verify(f'"{GOOD}" (p.txt)', "quote", c, ev) == []


def test_misquote_is_caught_with_word_level_hint(env):
    c, ev = env
    issues = verify(f'"{BAD}" (p.txt)', "quote", c, ev)
    assert [i.kind for i in issues] == ["quote_not_found"]
    assert 'has "the" but the source has "a"' in issues[0].hint
    assert "p.txt lines" in issues[0].hint


def test_quote_never_read_is_flagged_unseen(env):
    c, _ = env
    issues = verify(f'"{GOOD}" (p.txt)', "quote", c, [])
    assert [i.kind for i in issues] == ["quote_unseen"]


def test_quote_seen_via_grep_output(env):
    c, _ = env
    ev = [{"type": "tool", "name": "bash", "args": {"command": "grep -n router p.txt"},
           "content": "2:mixing weight for each cache using a lightweight router with 2.1M parameters. The router\n"
                      "3:is trained for 3 epochs with a learning rate of 2e-4 and a batch size of 64.",
           "is_error": False}]
    assert verify(f'"{GOOD}" (p.txt)', "quote", c, ev) == []


def test_ellipsis_quote_pieces_checked_in_order(env):
    c, ev = env
    assert verify('"mixing weight for each cache ... learning rate of 2e-4" (p.txt)', "quote", c, ev) == []
    bad = verify('"learning rate of 2e-4 ... mixing weight for each cache" (p.txt)', "quote", c, ev)
    assert bad and bad[0].kind == "quote_not_found"


def test_quote_attributed_to_wrong_file(env):
    c, ev = env
    issues = verify('"Unrelated sentence that only lives in the other file" (p.txt)', "quote", c, ev)
    assert issues[0].kind == "quote_wrong_file" and "q.txt" in issues[0].hint


def test_curly_quotes_and_whitespace_are_normalised(env):
    c, ev = env
    ans = "“mixing   weight for each cache using a lightweight router” (p.txt)"
    assert verify(ans, "quote", c, ev) == []


def test_uncited_answer_is_allowed(env):
    # citations are optional in the product: no citation is not an issue, only bad citations are
    c, ev = env
    assert verify("The learning rate is 2e-4.", "quote", c, ev) == []
    assert verify("The learning rate is 2e-4.", "line", c, ev) == []


def test_count_citations():
    from agent.verify import count_citations
    assert count_citations(f'x "{GOOD}" (p.txt) y "{GOOD}" (p.txt)', "quote") == 2
    assert count_citations("a [p.txt:1-2] b [p.txt:3]", "line") == 2
    assert count_citations("no cites", "quote") == 0


def test_line_citations(env):
    c, ev = env
    assert verify("lr is 2e-4 [p.txt:2-3]", "line", c, ev) == []
    assert verify("x [p.txt:2-99]", "line", c, ev)[0].kind == "line_out_of_range"
    assert verify("x [nope.txt:1]", "line", c, ev)[0].kind == "unknown_file"
    assert verify("x [p.txt:2]", "line", c, [])[0].kind == "line_unseen"
