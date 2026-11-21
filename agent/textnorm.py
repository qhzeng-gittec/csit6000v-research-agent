"""Text normalisation shared by the verifier and edit_draft.

Normalisation: curly quotes/dashes -> ASCII, whitespace runs -> one space, ends stripped.
`normalize_with_map` also returns, for every normalised char, its index in the original
string so a match found in normalised text can be mapped back to the original span.
"""
from __future__ import annotations

_TRANS = {
    "‘": "'", "’": "'", "“": '"', "”": '"',
    "–": "-", "—": "-", " ": " ",
}


def normalize_with_map(s: str) -> tuple[str, list[int]]:
    out: list[str] = []
    idx: list[int] = []
    prev_space = False
    for i, ch in enumerate(s):
        ch = _TRANS.get(ch, ch)
        if ch.isspace():
            if out and not prev_space:
                out.append(" ")
                idx.append(i)
                prev_space = True
            continue
        out.append(ch)
        idx.append(i)
        prev_space = False
    if out and out[-1] == " ":
        out.pop()
        idx.pop()
    return "".join(out), idx


def normalize(s: str) -> str:
    return normalize_with_map(s)[0]
