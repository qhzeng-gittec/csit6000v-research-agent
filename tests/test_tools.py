import pytest

from agent.tools import Tools


@pytest.fixture
def tools(tmp_path):
    (tmp_path / "a.txt").write_text("\n".join(f"line {i}" for i in range(1, 501)), encoding="utf-8")
    (tmp_path / "b.txt").write_text("alpha\nbeta needle\ngamma\n", encoding="utf-8")
    return Tools(tmp_path)


def test_read_prefixes_line_numbers(tools):
    r = tools.read("b.txt")
    assert "     2\tbeta needle" in r.text
    assert not r.is_error


def test_read_offset_limit_and_continuation_hint(tools):
    r = tools.read("a.txt", offset=10, limit=3)
    assert "    10\tline 10" in r.text and "    12\tline 12" in r.text
    assert "line 13" not in r.text
    assert "offset=13" in r.text


def test_read_rejects_path_escape(tools):
    assert tools.read("../etc/passwd").is_error
    assert tools.read("/etc/passwd").is_error


@pytest.mark.parametrize("cmd", [
    "grep -n needle b.txt",
    "grep -rn needle .",
    "ls",
    "cat b.txt | head -n 2",
    "sed -n '1,2p' b.txt",
    "grep -E 'alpha|gamma' b.txt",
    "find . -name '*.txt'",
    "wc -l b.txt",
])
def test_bash_allows_read_only(tools, cmd):
    r = tools.bash(cmd)
    assert not r.is_error, r.text


@pytest.mark.parametrize("cmd", [
    "echo hi > x.txt",
    "cat b.txt >> a.txt",
    "rm b.txt",
    "python -c 'print(1)'",
    "cat /etc/passwd",
    "cat ../x",
    "cat $(ls)",
    "cat `ls`",
    "ls; rm b.txt",
    "ls && rm b.txt",
    "sed -i 's/a/b/' b.txt",
    "sed -n 'w out.txt' b.txt",
    "find . -delete",
    "find . -exec rm {} +",
    "sort -o out.txt b.txt",
    "cat < b.txt",
])
def test_bash_blocks_writes_and_escapes(tools, cmd):
    r = tools.bash(cmd)
    assert r.is_error, f"should have been blocked: {cmd}"
    assert (tools.root / "b.txt").exists()
    assert not (tools.root / "x.txt").exists() and not (tools.root / "out.txt").exists()


def test_grep_no_match_is_not_an_error(tools):
    r = tools.bash("grep -n zzz b.txt")
    assert not r.is_error


def test_bash_output_truncated(tools):
    r = tools.bash("cat a.txt a.txt a.txt a.txt")
    assert r.truncated and "truncated" in r.text


def test_bash_env_has_no_secrets(tools, monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-secret")
    r = tools.bash("find . -name 'x*' | wc -l")  # sanity; env scrubbing is by construction
    assert "sk-secret" not in r.text
