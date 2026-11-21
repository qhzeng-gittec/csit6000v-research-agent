"""Evidence-first answers: the model writes verbatim excerpts first, then an answer that may only
use them. Only the <answer> part is the deliverable (and the only part that is scored); the
excerpts are shown to the user separately, as footnotes, and are checked by the ledger.
"""
from __future__ import annotations

import re

ANSWER_RE = re.compile(r"<answer>\s*(.*?)\s*(?:</answer>|\Z)", re.S | re.I)
EVIDENCE_RE = re.compile(r"<evidence>\s*(.*?)\s*</evidence>", re.S | re.I)
MARK_RE = re.compile(r"\s*\[E\d+(?:\s*[,;]\s*E?\d+)*\]")


def split(text: str) -> tuple[str | None, str | None]:
    """(evidence block, answer block); either is None when the tag is missing."""
    ev = EVIDENCE_RE.search(text)
    an = ANSWER_RE.search(text)
    return (ev.group(1) if ev else None), (an.group(1) if an else None)


def deliverable(text: str) -> str:
    """What the user reads as the answer: the <answer> body without [E1] markers.

    Without an <answer> tag the whole text is the answer (format failure, nothing hidden)."""
    _, ans = split(text)
    if ans is None:
        return text.strip()
    return MARK_RE.sub("", ans).strip()


def stats(text: str) -> dict:
    """Format/coverage numbers for the report (no effect on the answer)."""
    ev, ans = split(text)
    n_ev = len(re.findall(r"^\s*\[E\d+\]", ev or "", re.M))
    if ans is None:
        return {"ev_format_ok": False, "ev_items": n_ev, "ev_unmarked_share": None}
    sents = [s for s in re.split(r"(?<=[.!?])\s+|\n+", ans) if len(s.strip()) > 15]
    unmarked = [s for s in sents if not re.search(r"\[E\d+", s)]
    return {"ev_format_ok": ev is not None, "ev_items": n_ev,
            "ev_unmarked_share": round(len(unmarked) / len(sents), 3) if sents else 0.0}


_CITED_QUOTE = re.compile(r'\s*[“"][^"“”]{8,}?[”"]\s*\([^()\s]+\)')
_BARE_QUOTE = re.compile(r'\s*[“"][^"“”\n]{20,}?[”"]')


def strip_quotes(text: str) -> str:
    """Dilution check: the answer with every verbatim quote removed, so only the model's own words are judged.

    Removes `"quote" (file)` citations and any bare quoted span of 20+ characters (same rule for every arm),
    then drops lines left with fewer than 25 letters (e.g. a bare 'The document says:')."""
    out = _BARE_QUOTE.sub("", _CITED_QUOTE.sub("", text))
    keep = [ln for ln in out.split("\n") if not ln.strip() or len(re.findall(r"[A-Za-z]", ln)) >= 25]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(keep)).strip()
