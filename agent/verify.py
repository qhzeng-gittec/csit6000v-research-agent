"""Citation verifier: deterministic checks of an answer's citations against the corpus and the trace.

It does NOT judge whether a quote *supports* the claim (that needs an LLM judge, done in the
evaluation step). It checks three mechanical things:
  1. existence  - the cited text / line range is really in the cited file
  2. exactness  - a "verbatim" quote matches the source (after whitespace/quote normalisation)
  3. seen       - the model actually saw that text in a tool result (not recited from memory)
"""
from __future__ import annotations

import difflib
import re
from dataclasses import dataclass
from pathlib import Path

from .textnorm import normalize, normalize_with_map

QUOTE_RE = re.compile(r'[“"]([^"“”]{8,}?)[”"]\s*\(([^()\s]+)\)', re.S)
LINE_RE = re.compile(r"\[([^\[\]:\s]+):(\d+)(?:\s*[-–]\s*(\d+))?\]")
ELLIPSIS_RE = re.compile(r"\.\.\.|…")
READ_PREFIX = re.compile(r"^\s*\d+\t", re.M)
GREP_PREFIX = re.compile(r"^(?:[^\s:]+:)?\d+[:-]", re.M)
READ_LINE = re.compile(r"^\s*(\d+)\t")
GREP_FILE_LINE = re.compile(r"^([^\s:]+):(\d+)[:-]")
GREP_LINE = re.compile(r"^(\d+)[:-]")


@dataclass
class Issue:
    kind: str  # quote_not_found | quote_wrong_file | quote_unseen | unknown_file |
    #            line_out_of_range | line_unseen
    #            no_citation (only with require_cite, arm A7: a one-time nudge, see loop.py)
    # Citations are optional in the product: uncited sentences are shown as plain text and only
    # citations that ARE given must check out. A7 merely nudges an answer that has none at all.
    cited: str
    message: str
    hint: str = ""


class Corpus:
    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.files: dict[str, str] = {}
        for p in sorted(self.root.rglob("*")):
            if p.is_file():
                self.files[p.relative_to(self.root).as_posix()] = p.read_text(encoding="utf-8", errors="replace")
        self.norm = {k: normalize(v) for k, v in self.files.items()}

    def resolve(self, cited: str) -> str | None:
        c = cited.strip()
        if c.startswith("./"):
            c = c[2:]
        if c in self.files:
            return c
        base = c.rsplit("/", 1)[-1]
        hits = [k for k in self.files if k.rsplit("/", 1)[-1] == base]
        return hits[0] if len(hits) == 1 else None


# ---------------------------------------------------------------- what the model saw
def observed(tool_events: list[dict], corpus: Corpus) -> tuple[str, dict[str, set[int]]]:
    """Text and line numbers that appeared in successful read/bash results."""
    chunks: list[str] = []
    seen_lines: dict[str, set[int]] = {}
    for e in tool_events:
        if e.get("is_error") or e.get("name") not in ("read", "bash"):
            continue
        text = e.get("content", "")
        args = e.get("args", {}) or {}
        # keep a raw and a prefix-stripped copy: a safe superset of what was visible
        chunks.append(normalize(text))
        chunks.append(normalize(READ_PREFIX.sub("", GREP_PREFIX.sub("", text))))
        chunks.append(normalize(READ_PREFIX.sub("", text)))
        if e["name"] == "read":
            name = corpus.resolve(str(args.get("path", "")))
            if name:
                for line in text.splitlines():
                    m = READ_LINE.match(line)
                    if m:
                        seen_lines.setdefault(name, set()).add(int(m.group(1)))
        else:
            cmd = str(args.get("command", ""))
            single = [n for n in corpus.files if n in cmd]
            for line in text.splitlines():
                m = GREP_FILE_LINE.match(line)
                if m and corpus.resolve(m.group(1)):
                    seen_lines.setdefault(corpus.resolve(m.group(1)), set()).add(int(m.group(2)))
                elif len(single) == 1 and (m2 := GREP_LINE.match(line)):
                    seen_lines.setdefault(single[0], set()).add(int(m2.group(1)))
    return " ␞ ".join(chunks), seen_lines


# ---------------------------------------------------------------- hints for failed quotes
def _closest(corpus: Corpus, name: str | None, piece: str):
    """Locate where the quote most plausibly came from.

    Anchor on the longest matching blocks between the (normalised) file and the quote, then
    extend the region by what the quote has left on each side, snapped to word boundaries.
    Returns (coverage_ratio, file, first_line, last_line, region_text).
    """
    target = normalize(piece)
    best = (0.0, None, 0, 0, "")
    for fname in [name] if name else list(corpus.files):
        raw = corpus.files[fname]
        ntext, idx = normalize_with_map(raw)
        blocks = [b for b in difflib.SequenceMatcher(None, ntext, target, autojunk=False).get_matching_blocks() if b.size >= 8]
        if not blocks:
            continue
        anchor = max(blocks, key=lambda b: b.size)
        blocks = [b for b in blocks if abs((b.a - b.b) - (anchor.a - anchor.b)) <= 40]  # consistent alignment
        ratio = sum(b.size for b in blocks) / max(1, len(target))
        if ratio <= best[0]:
            continue
        first, last = blocks[0], blocks[-1]
        lo = max(0, first.a - first.b)
        hi = min(len(ntext), last.a + last.size + (len(target) - last.b - last.size))
        while lo > 0 and ntext[lo - 1] != " ":
            lo -= 1
        while hi < len(ntext) and ntext[hi] != " ":
            hi += 1
        l1 = raw.count("\n", 0, idx[lo]) + 1
        l2 = raw.count("\n", 0, idx[max(lo, hi - 1)]) + 1
        best = (ratio, fname, l1, l2, ntext[lo:hi].strip())
    return best


def _word_diffs(quote_norm: str, window_norm: str, limit: int = 3) -> list[str]:
    a, b = quote_norm.split(), window_norm.split()
    ops = difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes()
    out: list[str] = []
    for n, (tag, i1, i2, j1, j2) in enumerate(ops):
        if tag == "equal" or i1 == i2:  # extra source words are not an error
            continue
        qa = a[i1:i2]
        if n == 0:
            sb = b[max(j1, j2 - len(qa)) : j2]
        elif n == len(ops) - 1:
            sb = b[j1 : j1 + len(qa)]
        else:
            sb = b[j1:j2]
        q = " ".join(qa)
        out.append(f'your quote has "{q}" but the source has "{" ".join(sb)}"' if sb else f'"{q}" is not in the source')
    return out[:limit]


def _failed_quote_issue(corpus: Corpus, name: str, quote: str, cited: str) -> Issue:
    ratio, fname, lo, hi, window = _closest(corpus, name, quote)
    hint = ""
    if fname and ratio >= 0.6:
        diffs = "; ".join(_word_diffs(normalize(quote), window))
        text = window if len(window) <= 300 else window[:300] + "..."
        hint = f'closest source text ({fname} lines {lo}-{hi}): "{text}"' + (f" | differences: {diffs}" if diffs else "")
    return Issue("quote_not_found", cited, "this quote is not a verbatim substring of the source", hint)


# ---------------------------------------------------------------- main entry
def _check_quote(quote: str, cited_file: str, corpus: Corpus, seen_norm: str) -> list[Issue]:
    cited = f'"{quote}" ({cited_file})'
    name = corpus.resolve(cited_file)
    if name is None:
        return [Issue("unknown_file", cited, f"file {cited_file!r} is not in the corpus")]
    pieces = [p.strip() for p in (normalize(x) for x in ELLIPSIS_RE.split(quote)) if len(p.strip()) >= 4]
    if not pieces:
        return []
    src, pos = corpus.norm[name], 0
    for p in pieces:
        i = src.find(p, pos)
        if i < 0:
            for other, text in corpus.norm.items():
                if other != name and p in text:
                    return [Issue("quote_wrong_file", cited, f"this quote is not in {name}", f"it appears in {other}")]
            return [_failed_quote_issue(corpus, name, quote, cited)]
        pos = i + len(p)
    if any(p not in seen_norm for p in pieces):
        return [Issue("quote_unseen", cited, "the quote exists in the file but you never read that text in this session; read it first")]
    return []


def _check_line(fname: str, a: str, b: str | None, corpus: Corpus, seen_lines: dict[str, set[int]]) -> list[Issue]:
    cited = f"[{fname}:{a}" + (f"-{b}" if b else "") + "]"
    name = corpus.resolve(fname)
    if name is None:
        return [Issue("unknown_file", cited, f"file {fname!r} is not in the corpus")]
    n = len(corpus.files[name].splitlines())
    s, e = int(a), int(b or a)
    if s < 1 or e < s or e > n:
        return [Issue("line_out_of_range", cited, f"{name} has {n} lines")]
    if not any(i in seen_lines.get(name, set()) for i in range(s, e + 1)):
        return [Issue("line_unseen", cited, "you never read any of these lines in this session; read them first")]
    return []


def verify(answer: str, cite: str, corpus: Corpus, tool_events: list[dict]) -> list[Issue]:
    if cite == "none":
        return []
    seen_norm, seen_lines = observed(tool_events, corpus)
    issues: list[Issue] = []
    found = 0
    done: set[str] = set()
    if cite == "quote":
        for m in QUOTE_RE.finditer(answer):
            found += 1
            if m.group(0) in done:
                continue
            done.add(m.group(0))
            issues += _check_quote(m.group(1), m.group(2), corpus, seen_norm)
    elif cite == "line":
        for m in LINE_RE.finditer(answer):
            found += 1
            if m.group(0) in done:
                continue
            done.add(m.group(0))
            issues += _check_line(m.group(1), m.group(2), m.group(3), corpus, seen_lines)
    else:
        raise ValueError(f"unknown cite mode {cite!r}")
    return issues


def count_citations(answer: str, cite: str) -> int:
    """How many citations the answer gives (coverage metric only; never a reason to revise)."""
    if cite == "quote":
        return len(QUOTE_RE.findall(answer))
    if cite == "line":
        return len(LINE_RE.findall(answer))
    return 0


def format_feedback(issues: list[Issue], round_no: int, max_rounds: int) -> str:
    lines = [f'<verification round="{round_no}/{max_rounds}">',
             f"The automatic check found {len(issues)} problem(s) in your answer:"]
    for i, it in enumerate(issues, 1):
        lines.append(f"{i}. [{it.kind}] {it.cited}".rstrip())
        lines.append(f"   {it.message}")
        if it.hint:
            lines.append(f"   hint: {it.hint}")
    lines.append(
        "You are now in REVISION MODE. Fix only these problems by calling edit_draft(old, new): `old` must be an "
        "exact, unique substring of your previous answer (max 300 characters; for a longer quote replace only the "
        "wrong words). You may use read/bash to re-check the source. Do not rewrite the answer. Reply \"Done\" when finished."
    )
    lines.append("</verification>")
    return "\n".join(lines)
