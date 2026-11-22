"""Grounding judge (arm C3): a small model flags statements in the draft the document does not support.

A "draft evidence looks suspicious" check: the judge NOMINATES spans,
the program only accepts spans that really occur in the draft (so the model can fix them with
edit_draft), and any judge failure means "pass" (keep the draft) rather than a forced revision.
Unlike verify.py this is a semantic check, so it can be wrong; it is bounded by max_revisions.
"""
from __future__ import annotations

import json
import re

from .llm import LLM
from .textnorm import normalize
from .verify import Issue

MAX_FLAGS = 5

PROMPT = """You are a strict fact-checker. Compare the RESPONSE against the DOCUMENT.

Flag only statements in the RESPONSE that make a factual claim the DOCUMENT does not support
(the information is absent from the document, goes beyond it, or contradicts it). Do NOT flag:
- statements that are supported or are reasonable paraphrases/summaries of the document;
- statements that say the document lacks some information;
- transitions, headings, or restatements of the question.

Return ONLY a JSON array (no prose). Each item:
{{"text": "<the offending text, copied EXACTLY from the RESPONSE, at most 250 characters>",
  "problem": "unsupported" | "contradicted",
  "reason": "<one short sentence: what the document actually says, or that it says nothing about this>"}}
Return [] if every claim is supported. Flag at most {k} items, most serious first.

DOCUMENT:
<<<
{doc}
>>>

RESPONSE:
<<<
{answer}
>>>"""


def _parse(text: str) -> list[dict]:
    m = re.search(r"\[.*\]", text, re.S)
    if not m:
        return []
    try:
        items = json.loads(m.group(0))
    except json.JSONDecodeError:
        return []
    return [i for i in items if isinstance(i, dict) and isinstance(i.get("text"), str)]


class Grounder:
    def __init__(self, judge: LLM, doc: str):
        self.judge, self.doc = judge, doc
        self.calls = 0
        self.failures = 0

    def __call__(self, draft: str) -> list[Issue]:
        self.calls += 1
        try:
            reply = self.judge.chat([{"role": "user", "content": PROMPT.format(k=MAX_FLAGS, doc=self.doc, answer=draft)}])
            items = _parse(reply.message["content"])
        except Exception:  # noqa: BLE001 - a broken judge must never block or rewrite an answer
            self.failures += 1
            return []
        nd, out, seen = normalize(draft), [], set()
        for it in items[:MAX_FLAGS]:
            span = it["text"].strip().strip('"')
            if len(span) < 8 or normalize(span) not in nd or span in seen:
                continue  # the program only accepts spans that really are in the draft
            seen.add(span)
            kind = "contradicted_claim" if it.get("problem") == "contradicted" else "unsupported_claim"
            out.append(Issue(kind, f'"{span}"',
                             "a fact-checker says the document does not support this statement; delete it or "
                             "rewrite it to say only what the document says (you may add a verbatim quote)",
                             str(it.get("reason", ""))[:300]))
        return out
