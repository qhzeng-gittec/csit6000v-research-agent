"""In-memory draft answer + the edit_draft operation (local replacement instead of a full rewrite).

The agent has no write access to the corpus; edit_draft only changes this in-memory string.
Matching is two-level: exact first, then normalised (whitespace / quote style), mapped back
to the original span. `old` must match exactly one place, otherwise a structured error is returned.
"""
from __future__ import annotations

import difflib

from .textnorm import normalize_with_map

MAX_OLD_CHARS = 300


def _positions(hay: str, needle: str) -> list[int]:
    out, i = [], hay.find(needle)
    while i != -1:
        out.append(i)
        i = hay.find(needle, i + 1)
    return out


class Draft:
    def __init__(self) -> None:
        self.text: str | None = None
        self.active = False  # becomes True after the first failed verification
        self.edits = 0

    def set(self, text: str) -> None:
        self.text = text

    def activate(self) -> None:
        self.active = True

    def edit(self, old: str, new: str) -> tuple[bool, str]:
        if not self.active or self.text is None:
            return False, ("error: edit_draft is only available in revision mode, after a <verification> "
                           "message. Give your answer first.")
        if not old:
            return False, "error: `old` must not be empty"
        if len(old) > MAX_OLD_CHARS:
            return False, f"error: `old` is {len(old)} chars; the limit is {MAX_OLD_CHARS}. Replace it in smaller pieces."
        text = self.text
        n = text.count(old)
        how = "exact"
        if n == 1:
            start = text.index(old)
            end = start + len(old)
        elif n > 1:
            return False, f"error: `old` matches {n} places in the draft; lengthen it with surrounding words so it is unique."
        else:
            ntext, idx = normalize_with_map(text)
            nold, _ = normalize_with_map(old)
            hits = _positions(ntext, nold) if nold else []
            if len(hits) > 1:
                return False, f"error: `old` matches {len(hits)} places (after normalising whitespace); make it unique."
            if not hits:
                return False, "error: `old` was not found in the draft." + self._nearest(text, old)
            how = "normalized"
            start = idx[hits[0]]
            end = idx[hits[0] + len(nold) - 1] + 1
        self.text = text[:start] + new + text[end:]
        self.edits += 1
        lo, hi = max(0, start - 40), min(len(self.text), start + len(new) + 40)
        return True, f'ok ({how} match): replaced 1 occurrence. Now reads: "...{self.text[lo:hi]}..."'

    @staticmethod
    def _nearest(text: str, old: str) -> str:
        m = difflib.SequenceMatcher(None, text, old, autojunk=False).find_longest_match(0, len(text), 0, len(old))
        if m.size < 8:
            return ""
        return f' Longest matching fragment is near: "...{text[max(0, m.a - 40): m.a + m.size + 40]}..."'
