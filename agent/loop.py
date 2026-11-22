"""The whole agent: call the model; if it asks for tools run them; if it doesn't, it is done.

With a citation mode on, a reply without tool calls is a *draft*. The verifier checks it; if it
fails and the gate is on, a <verification> message is APPENDED to the history (tools and system
prompt never change) and the model fixes the draft with edit_draft.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Callable

from .llm import LLM
from .tools import ToolResult, Tools
from .trace import Trace
from .verify import Corpus, Issue, count_citations, format_feedback, verify

COLLAPSE_RATIO = 0.6
# Empty reply (seen with thinking models: the whole output budget went to reasoning, finish_reason=length).
# Treated as a "said but did nothing" ending: send it back with a bounded nudge.
MAX_EMPTY_RETRIES = 2
EMPTY_MSG = ("Your last reply contained no answer text: the whole output budget went into planning. Write your "
             "final answer now, directly, using only what you have already read. Do not count words or sentences; "
             "when a length is requested, an approximate length is fine.")
EMPTY_RETRY_REASONING = 4000  # thinking-token cap for the retry only (observed: word-by-word counting loops)
NO_CITATION_MSG = ('Your answer contains no verbatim quote. For the key factual statements, insert a short quote '
                   'copied exactly from the file right after the statement, as "exact text" (file), using '
                   'edit_draft(old=the statement, new=the statement plus the quote).')  # a revision that shrinks the answer below 60% of the first draft is rejected


@dataclass
class AgentResult:
    answer: str
    status: str  # answered | unresolved | budget_exhausted | collapse_reverted | empty
    steps: int
    prompt_tokens: int
    completion_tokens: int
    cache_hit_tokens: int
    revisions: int
    edits: int
    first_draft_issues: int | None  # None when no citation check ran
    final_issues: int | None
    citations: int | None = None  # citations in the final answer (coverage; optional in the product)


def run_agent(
    question: str,
    llm: LLM,
    tools: Tools,
    trace: Trace,
    system: str,
    max_steps: int = 20,
    cite: str = "none",
    corpus: Corpus | None = None,
    gate: bool = True,
    max_revisions: int = 2,
    seed_events: list[dict] | None = None,
    grounder: Callable[[str], list[Issue]] | None = None,
    require_cite: bool = False,
) -> AgentResult:
    """seed_events: text the model has already seen before the loop starts (e.g. a document pasted
    into the prompt), in the same shape as tool events, so the verifier counts it as read.
    grounder: optional semantic check (arm C3) whose issues are added to the citation issues.
    require_cite: an answer with no quote at all is sent back ONCE for quotes (arm A7). With gate=False
    this is the only thing sent back; failed quotes are still only logged."""
    messages: list[dict] = [
        {"role": "system", "content": system},
        {"role": "user", "content": question},
    ]
    trace.log("system", content=system)
    trace.log("user", content=question)
    tool_events: list[dict] = list(seed_events or [])
    p_tok = c_tok = hit_tok = revisions = 0
    empty_retries = 0
    first_issues: int | None = None
    final_issues: int | None = None

    def ask(step: int, with_tools: bool) -> dict:
        nonlocal p_tok, c_tok, hit_tok
        if empty_retries:  # retrying an empty reply: cap the thinking budget
            reply = llm.chat(messages, tools.schemas() if with_tools else None, reasoning_budget=EMPTY_RETRY_REASONING)
        else:
            reply = llm.chat(messages, tools.schemas() if with_tools else None)
        p_tok += reply.usage.get("prompt_tokens", 0)
        c_tok += reply.usage.get("completion_tokens", 0)
        hit_tok += reply.usage.get("cache_hit_tokens", 0)
        trace.log("assistant", step=step, usage=reply.usage, latency_ms=reply.latency_ms, **reply.message)
        messages.append(reply.message)
        return reply.message

    first_draft: list[str] = []
    nudged = False

    def check(draft: str) -> list[Issue]:
        issues = verify(draft, cite, corpus, tool_events)
        if require_cite and not nudged and count_citations(draft, cite) == 0:
            issues.append(Issue("no_citation", "", NO_CITATION_MSG))
        return issues + (grounder(draft) if grounder else [])

    def result(answer: str, status: str, step: int) -> AgentResult:
        if revisions and first_draft and len(answer) < COLLAPSE_RATIO * len(first_draft[0]):
            # collapse guard: local fixes must not gut the answer
            trace.log("collapse_reverted", kept_chars=len(first_draft[0]), rejected_chars=len(answer))
            answer, status = first_draft[0], "collapse_reverted"
        n = count_citations(answer, cite) if cite != "none" else None
        return AgentResult(answer, status, step, p_tok, c_tok, hit_tok, revisions, tools.draft.edits,
                           first_issues, final_issues, n)

    for step in range(1, max_steps + 1):
        msg = ask(step, with_tools=True)
        calls = msg.get("tool_calls")
        if calls:
            for tc in calls:
                name = tc["function"]["name"]
                try:
                    args = json.loads(tc["function"]["arguments"] or "{}")
                    res = tools.call(name, args)
                except json.JSONDecodeError as e:
                    args = {}
                    res = ToolResult(f"error: arguments are not valid JSON: {e}", is_error=True)
                event = dict(step=step, tool_call_id=tc["id"], name=name, args=args, content=res.text,
                             truncated=res.truncated, is_error=res.is_error, duration_ms=res.duration_ms)
                trace.log("tool", **event)
                tool_events.append({"type": "tool", **event})
                messages.append({"role": "tool", "tool_call_id": tc["id"], "content": res.text})
            continue

        # no tool call: the model considers itself finished
        if not tools.draft.active and not (msg.get("content") or "").strip():
            if empty_retries < MAX_EMPTY_RETRIES and step < max_steps:
                empty_retries += 1
                trace.log("user", content=EMPTY_MSG, note="empty_reply", retry=empty_retries)
                messages.append({"role": "user", "content": EMPTY_MSG})
                continue
            return result("", "empty", step)  # never recorded as "answered"
        draft = tools.draft.text if tools.draft.active else msg["content"]
        tools.draft.set(draft)
        if cite == "none" or corpus is None:
            return result(draft, "answered", step)

        if not first_draft:
            first_draft.append(draft)
        issues = check(draft)
        first_issues = len(issues) if first_issues is None else first_issues
        final_issues = len(issues)
        trace.log("verdict", round=revisions, ok=not issues, issues=[asdict(i) for i in issues], draft=draft,
                  citations=count_citations(draft, cite))
        blocking = issues if gate else [i for i in issues if i.kind == "no_citation"]
        if not blocking:
            return result(draft, "answered", step)
        if revisions >= max_revisions:
            return result(draft, "unresolved", step)
        revisions += 1
        nudged = nudged or any(i.kind == "no_citation" for i in blocking)
        tools.draft.activate()
        feedback = format_feedback(blocking, revisions, max_revisions)
        trace.log("user", content=feedback, note="verification")
        messages.append({"role": "user", "content": feedback})

    # step budget exhausted
    if tools.draft.text is not None:
        draft = tools.draft.text
        if cite != "none" and corpus is not None:  # record the state of the draft we actually return
            issues = check(draft)
            final_issues = len(issues)
            trace.log("verdict", round=revisions, ok=not issues, issues=[asdict(i) for i in issues], draft=draft,
                      citations=count_citations(draft, cite), note="budget_exhausted")
        return result(draft, "budget_exhausted", max_steps)
    forced = "Step budget exhausted. Give your final answer now, using only what you have already read."
    messages.append({"role": "user", "content": forced})
    trace.log("user", content=forced, note="budget_exhausted")
    msg = ask(max_steps + 1, with_tools=False)
    tools.draft.set(msg["content"])
    return result(msg["content"], "budget_exhausted", max_steps + 1)
