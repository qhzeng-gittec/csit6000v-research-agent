"""Benchmark adapter, batch runner, scorer and paired comparison for FaithEval and FACTS Grounding.

    python -m agent.bench run     --exp main --n 100 --reps 2 --arms B0,C1,C2
    python -m agent.bench score   --exp main
    python -m agent.bench compare --exp main --a C1 --b C2

Benchmark arms follow the benchmarks' own protocol: the WHOLE document is pasted into the prompt.
Same model, same input; only the citation requirement and the verifier gate change:
    B0  no citation requirement                         (official setting)
    C1  verbatim-quote citations, verifier LOGS only     (no revision)
    C2  verbatim-quote citations, verifier GATE          (failed checks -> local edit_draft revision)
C2 vs C1 isolates the evidence ledger / verifier gate; C1 vs B0 isolates the citation requirement.

Product arms (document read through tools, used for the self-built paper set) are also available:
    A0 tools, no citation | A1 tools + line citations + gate | A2 tools + quote citations + gate

Scoring:
    faith_unans   strict: final `Answer:` contains "unknown"      (FaithEval convention)
    faith_incons  strict: final `Answer:` contains "conflict"     (FaithEval convention)
    faith_cf      chosen option letter == answerKey               (our reading; the repo documents no rule)
    facts         one LLM judge with the official response-level prompt (Accurate) AND an eligibility check,
                  plus the official sentence-level prompt -> unsupported-sentence rate.
                  "FACTS-style" numbers, NOT the official leaderboard score (that uses three judges).
"""
from __future__ import annotations

import argparse
import json
import os
import random
import re
import string
import textwrap
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

from .evidence import deliverable, stats as ev_stats, strip_quotes
from .llm import LLM, LLMConfig
from .loop import run_agent
from .prompts import system_prompt
from .tools import Tools
from .trace import Trace, read_trace

BENCHES = ("faith_unans", "faith_incons", "faith_cf", "facts")
ARMS = {
    "B0": dict(mode="context", cite="none", gate=False),
    "C1": dict(mode="context", cite="quote", gate=False),
    "C2": dict(mode="context", cite="quote", gate=True),
    # C2 + a small-model grounding judge that flags unsupported statements (original project's design)
    "C3": dict(mode="context", cite="quote", gate=True, ground=True),
    "A0": dict(mode="files", cite="none", gate=True),
    "A1": dict(mode="files", cite="line", gate=True),
    "A2": dict(mode="files", cite="quote", gate=True),
    # evidence-first: verbatim excerpts block, then an answer that marks which excerpt each sentence uses.
    # Only the <answer> body is delivered and scored (see agent/evidence.py).
    "A4": dict(mode="files", cite="quote", gate=False, style="evidence"),
    "A5": dict(mode="files", cite="quote", gate=False, style="evidence_strict"),
    # verbatim quotes (failed quotes only logged) + "state only what the document says"
    "A6": dict(mode="files", cite="quote", gate=False, style="inline_strict"),
    # A6 + one nudge when the answer has no quote at all (failed quotes are still only logged)
    "A7": dict(mode="files", cite="quote", gate=False, style="inline_strict", require_cite=True),
    # A6 + three rules derived from A6's remaining unsupported sentences on the dev split
    "A8": dict(mode="files", cite="quote", gate=False, style="inline_strict_plus"),
    # ablation of A8: the same 4 writing rules, no citation request at all
    "A9": dict(mode="files", cite="none", gate=False, style="plain_strict_plus"),
    # A8 + the verifier: quotes not found in what the agent read are sent back for revision (edit_draft)
    "A10": dict(mode="files", cite="quote", gate=True, style="inline_strict_plus"),
}
DATA = Path(os.environ.get("BENCH_DATA", "data/benchmarks"))


# ===================================================================== examples
@dataclass
class Example:
    bench: str
    id: str
    question: str  # the raw question / user request
    doc: str
    gold: dict = field(default_factory=dict)
    options: list[str] = field(default_factory=list)  # "A. text" lines, counterfactual only


def _pick(n: int, total: int, seed: int) -> list[int]:
    return sorted(random.Random(seed).sample(range(total), min(n, total)))


def load(bench: str, n: int, seed: int = 0, data: Path = DATA) -> list[Example]:
    if bench in ("faith_unans", "faith_incons"):
        name = "unanswerable" if bench == "faith_unans" else "inconsistent"
        df = pd.read_parquet(data / f"faitheval_{name}.parquet")
        return [Example(bench, str(df.qid[i])[:10], df.question[i], df.context[i],
                        {"answers": [str(a) for a in df.answers[i]]}) for i in _pick(n, len(df), seed)]
    if bench == "faith_cf":
        df = pd.read_parquet(data / "faitheval_counterfactual.parquet")
        out = []
        for i in _pick(n, len(df), seed):
            ch = df.choices[i]
            opts = [f"{lab}. {txt}" for lab, txt in zip(ch["label"], ch["text"])]
            out.append(Example(bench, str(df.id[i]), df.question[i], df.context[i],
                               {"answerKey": str(df.answerKey[i])}, opts))
        return out
    if bench == "facts":
        df = pd.read_csv(data / "facts_examples.csv")
        return [Example(bench, f"facts{i:04d}", df.user_request[i], df.context_document[i]) for i in _pick(n, len(df), seed)]
    raise ValueError(f"unknown bench {bench!r}; choose from {BENCHES}")


def task_text(ex: Example, inline: bool) -> str:
    where = "the document above" if inline else "the document in the file `doc.txt`"
    if ex.bench == "faith_unans":
        return (f"Question: {ex.question}\n\nAnswer the question using only {where}. If there is no information "
                f"available from the document, the answer should be 'unknown'.\n"
                "Begin your final answer with a line of the form `Answer: <short answer>`.")
    if ex.bench == "faith_incons":
        return (f"Question: {ex.question}\n\nAnswer the question using only {where}. If there is conflicting "
                f"information or multiple answers in the document, the answer should be 'conflict'.\n"
                "Begin your final answer with a line of the form `Answer: <short answer>`.")
    if ex.bench == "faith_cf":
        return (f"Question: {ex.question}\n\nOptions:\n" + "\n".join(ex.options) +
                f"\n\nAnswer using only {where}, even if it contradicts what you know: pick the option the "
                "document supports.\nBegin your final answer with a line of the form `Answer: <letter>`.")
    return f"{ex.question}\n\nIn your answer, refer only to {where}. Do not employ any outside knowledge."


def context_message(ex: Example) -> str:
    return f"Document (doc.txt):\n<<<\n{ex.doc}\n>>>\n\n{task_text(ex, inline=True)}"


def wrap_doc(text: str, width: int = 100) -> str:
    lines: list[str] = []
    for para in text.splitlines():
        lines.extend(textwrap.wrap(para, width, break_long_words=False, break_on_hyphens=False) or [""])
    return "\n".join(lines) + "\n"


def parse_run_name(name: str) -> tuple[str, str, int]:
    """`<id>__<arm>__r<rep>` (or legacy `<id>__<arm>`). Split from the RIGHT: some dataset ids
    themselves contain `__` (e.g. FaithEval's `LEAP__5_10315`)."""
    parts = name.split("__")
    if len(parts) >= 3 and parts[-1].startswith("r") and parts[-1][1:].isdigit():
        return "__".join(parts[:-2]), parts[-2], int(parts[-1][1:])
    return "__".join(parts[:-1]), parts[-1], 0


# ===================================================================== running
def run_one(ex: Example, arm: str, rep: int, cfg: LLMConfig, out_root: Path, max_steps: int, max_revisions: int) -> Path:
    spec = ARMS[arm]
    run_dir = out_root / ex.bench / f"{ex.id}__{arm}__r{rep}"
    meta_path = run_dir / "meta.json"
    if meta_path.exists():
        status = json.loads(meta_path.read_text(encoding="utf-8")).get("status")
        legacy_empty = (status == "answered" and not (run_dir / "answer.md").read_text(encoding="utf-8").strip())
        if status != "error" and not legacy_empty:  # legacy_empty: recorded before the empty-reply check existed
            return run_dir  # resume: already done
    run_dir.mkdir(parents=True, exist_ok=True)
    for stale in ("trace.jsonl", "score.json", "score_first.json", "score_official.json", "score_noquote.json"):
        (run_dir / stale).unlink(missing_ok=True)
    (run_dir / "example.json").write_text(json.dumps(asdict(ex), ensure_ascii=False), encoding="utf-8")
    corpus = run_dir / "corpus"
    corpus.mkdir(exist_ok=True)
    meta: dict = {"bench": ex.bench, "id": ex.id, "arm": arm, "rep": rep, **spec, "model": cfg.model,
                  "base_url": cfg.base_url, "temperature": cfg.temperature, "max_steps": max_steps,
                  "max_revisions": max_revisions}
    trace = Trace(run_dir / "trace.jsonl")
    t0 = time.monotonic()
    try:
        if spec["mode"] == "context":
            (corpus / "doc.txt").write_text(ex.doc, encoding="utf-8")
            question = context_message(ex)
            tools = Tools(corpus, enabled=("edit_draft",) if spec["cite"] != "none" else ())
            seed = [{"type": "tool", "name": "read", "args": {"path": "doc.txt"}, "content": ex.doc, "is_error": False}]
        else:
            (corpus / "doc.txt").write_text(wrap_doc(ex.doc), encoding="utf-8")
            question = task_text(ex, inline=False)
            tools, seed = Tools(corpus), None
        from .verify import Corpus  # local import keeps module import cheap for scoring-only use
        grounder = None
        if spec.get("ground"):
            from .ground import Grounder
            gcfg = _ground_cfg()
            grounder = Grounder(LLM(gcfg), ex.doc)
            meta["ground_model"] = gcfg.model
        res = run_agent(question, LLM(cfg), tools, trace, system_prompt(spec["cite"], spec["mode"], spec.get("style", "inline")),
                        max_steps=max_steps, cite=spec["cite"], corpus=Corpus(corpus), gate=spec["gate"],
                        max_revisions=max_revisions, seed_events=seed, grounder=grounder,
                        require_cite=spec.get("require_cite", False))
        answer = res.answer
        meta.update({k: v for k, v in asdict(res).items() if k != "answer"})
        if grounder:
            meta.update(ground_calls=grounder.calls, ground_failures=grounder.failures)
    except Exception as e:  # noqa: BLE001 - one bad call must not kill the batch
        answer = ""
        meta.update(status="error", error=f"{type(e).__name__}: {e}"[:500])
    meta["wall_s"] = round(time.monotonic() - t0, 2)
    trace.log("final", answer=answer, status=meta["status"])
    trace.close()
    (run_dir / "answer.md").write_text(answer, encoding="utf-8")
    meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
    return run_dir


def held_out_ids(out: Path, exps: list[str]) -> set[str]:
    """Example ids already used by other experiments (e.g. the dev split), to keep a test split clean."""
    return {parse_run_name(p.name)[0] for e in exps for p in (out / e).glob("*/*__*")}


def examples_by_id(bench: str, ids_file: str) -> list[Example]:
    """The examples listed in a split file (one id per line, e.g. splits/facts_test100.txt)."""
    want = {x.strip() for x in Path(ids_file).read_text(encoding="utf-8").split() if x.strip()}
    out = [ex for ex in load(bench, 10**9) if ex.id in want]
    if len(out) != len(want):
        raise SystemExit(f"{ids_file}: {len(want) - len(out)} ids not found in {bench}")
    return out


def pick_examples(bench: str, n: int, seed: int, exclude: set[str]) -> list[Example]:
    """n examples of `bench` whose ids are not in `exclude` (deterministic for a given seed)."""
    pool = load(bench, n + len(exclude), seed)
    return [ex for ex in pool if ex.id not in exclude][:n]


def cmd_run(a: argparse.Namespace) -> None:
    cfg = LLMConfig.from_env()
    out = Path(a.out) / a.exp
    out.mkdir(parents=True, exist_ok=True)
    arms = a.arms.split(",")
    for arm in arms:
        if arm not in ARMS:
            raise SystemExit(f"unknown arm {arm!r}; choose from {sorted(ARMS)}")
    excl = held_out_ids(Path(a.out), a.exclude)
    pick = (lambda b: examples_by_id(b, a.ids)) if a.ids else (lambda b: pick_examples(b, a.n, a.seed, excl))
    jobs = [(ex, arm, rep) for b in a.bench for ex in pick(b) for rep in range(a.reps) for arm in arms]
    (out / "exp.json").write_text(json.dumps({
        "model": cfg.model, "base_url": cfg.base_url, "temperature": cfg.temperature, "benches": a.bench,
        "n": a.n, "seed": a.seed, "exclude": a.exclude, "ids": a.ids, "reps": a.reps, "arms": {k: ARMS[k] for k in arms},
        "max_steps": a.max_steps, "max_revisions": a.max_revisions, "started": time.strftime("%Y-%m-%d %H:%M:%S"),
    }, indent=2), encoding="utf-8")
    print(f"{len(jobs)} runs, {a.workers} workers -> {out}", flush=True)
    done = errors = 0
    with ThreadPoolExecutor(a.workers) as pool:
        futs = {pool.submit(run_one, ex, arm, rep, cfg, out, a.max_steps, a.max_revisions): (ex, arm, rep)
                for ex, arm, rep in jobs}
        for f in as_completed(futs):
            ex, arm, rep = futs[f]
            m = json.loads((f.result() / "meta.json").read_text(encoding="utf-8"))
            done += 1
            errors += m["status"] == "error"
            if done % 25 == 0 or m["status"] == "error" or done == len(jobs):
                print(f"[{done}/{len(jobs)}] errors={errors} last: {ex.bench} {ex.id} {arm} r{rep} {m['status']}"
                      + (f" {m.get('error', '')[:120]}" if m["status"] == "error" else ""), flush=True)


# ===================================================================== scoring
def norm(s: str) -> str:
    s = s.lower().replace("_", " ")
    s = "".join(ch for ch in s if ch not in string.punctuation)
    s = re.sub(r"\b(a|an|the)\b", " ", s)
    return " ".join(s.split())


ABSTAIN_STRICT, ABSTAIN_LOOSE = ["unknown"], ["unknown", "no answer", "no information", "not", "unclear"]
CONFLICT_STRICT = ["conflict"]
CONFLICT_LOOSE = ["conflict", "multiple answers", "disagreement", "inconsistent", "contradictory",
                  "contradiction", "inconsistency", "two answers", "2 answers", "conflicting"]
ANSWER_LINE = re.compile(r"(?im)^[\s*>_#-]*answer\s*:\s*\**\s*(.+)$")


def answer_line(text: str) -> str | None:
    m = ANSWER_LINE.search(text)
    return m.group(1).strip() if m else None


def _any(text: str, keys: list[str]) -> bool:
    n = norm(text)
    return any(k in n for k in keys)


def score_rule(bench: str, answer: str, gold: dict) -> dict:
    line = answer_line(answer)
    probe = line if line is not None else answer
    out = {"format_ok": line is not None}
    if bench == "faith_unans":
        out.update(correct=_any(probe, ABSTAIN_STRICT), correct_loose=_any(probe, ABSTAIN_LOOSE))
    elif bench == "faith_incons":
        out.update(correct=_any(probe, CONFLICT_STRICT), correct_loose=_any(probe, CONFLICT_LOOSE))
    elif bench == "faith_cf":
        m = re.match(r"\(?\**\s*([A-Ea-e])\b", probe.strip())
        out.update(correct=bool(m) and m.group(1).upper() == gold["answerKey"], correct_loose=None)
    return out


def _clean_prompt(p: str) -> str:
    p = p.strip()
    if len(p) > 1 and p[0] == p[-1] == '"':
        p = p[1:-1]
    return p.replace("\\n", "\n")


def _judge_cfg() -> LLMConfig:
    key = os.environ.get("JUDGE_API_KEY") or os.environ.get("DEEPSEEK_API_KEY")
    if not key:
        raise SystemExit("Set JUDGE_API_KEY (or DEEPSEEK_API_KEY) for the FACTS judge.")
    return LLMConfig(base_url=os.environ.get("JUDGE_BASE_URL", "https://api.deepseek.com"), api_key=key,
                     model=os.environ.get("JUDGE_MODEL", "deepseek-flash"), temperature=0.0)


def _ground_cfg() -> LLMConfig:
    """The in-loop grounding judge (arm C3). Keep it different from the scoring judge (JUDGE_*),
    otherwise the gate is simply the evaluator in disguise."""
    key = os.environ.get("GROUND_API_KEY") or os.environ.get("DEEPSEEK_API_KEY")
    if not key:
        raise SystemExit("Set GROUND_API_KEY (or DEEPSEEK_API_KEY) for the C3 grounding judge.")
    return LLMConfig(base_url=os.environ.get("GROUND_BASE_URL", "https://api.deepseek.com"), api_key=key,
                     model=os.environ.get("GROUND_MODEL", "deepseek-flash"), temperature=0.0, max_tokens=4096)


ELIGIBLE = ("You are checking whether a response is eligible for grounding evaluation.\n\nUser request:\n{q}\n\n"
            "Response:\n{r}\n\nDoes the response make a genuine attempt to address the user's request? It may point "
            "out that the document lacks some requested information, but it must not be a blanket refusal or "
            "off-topic. Reply with exactly one word: Eligible or Ineligible.")


def parse_verdict(text: str) -> bool | None:
    hits = re.findall(r"\b(Inaccurate|Accurate)\b", text)
    return hits[-1] == "Accurate" if hits else None


SENT_LABELS = ("supported", "unsupported", "contradictory", "no_rad")


def parse_sentence_labels(text: str) -> dict:
    """Count labels in the sentence-level judge output (one JSON object per line)."""
    counts = dict.fromkeys(SENT_LABELS, 0)
    bad: list[str] = []  # unsupported/contradictory sentences, for error analysis only
    for line in text.splitlines():
        line = line.strip().strip(",")
        if not line.startswith("{"):
            continue
        sentence = ""
        try:
            obj = json.loads(line)
            label = str(obj.get("label", "")).strip().lower()
            sentence = str(obj.get("sentence", ""))
        except json.JSONDecodeError:
            m = re.search(r'"label"\s*:\s*"(\w+)"', line)
            label = m.group(1).lower() if m else ""
        if label in counts:
            counts[label] += 1
            if label in ("unsupported", "contradictory") and sentence:
                bad.append(sentence[:400])
    graded = counts["supported"] + counts["unsupported"] + counts["contradictory"]
    counts["unsup_rate"] = (counts["unsupported"] + counts["contradictory"]) / graded if graded else None
    counts["bad"] = bad
    return counts


def _fill(tpl: str, ex: dict, answer: str) -> str:
    return (tpl.replace("{{user_request}}", ex["question"]).replace("{{context_document}}", ex["doc"])
            .replace("{{response}}", answer))


def score_facts(ex: dict, answer: str, judge: LLM, tpl_resp: str, tpl_sent: str) -> dict:
    acc = parse_verdict(judge.chat([{"role": "user", "content": _fill(tpl_resp, ex, answer)}]).message["content"])
    el = judge.chat([{"role": "user", "content": ELIGIBLE.format(q=ex["question"], r=answer)}]).message["content"].lower()
    eligible = "ineligible" not in el and "eligible" in el
    sent = parse_sentence_labels(judge.chat([{"role": "user", "content": _fill(tpl_sent, ex, answer)}]).message["content"])
    return {"accurate": acc, "eligible": eligible, "correct": bool(acc) and eligible, "correct_loose": None,
            "format_ok": True, **{f"sent_{k}": v for k, v in sent.items()}}


# ---- official-style protocol (FACTS Grounding paper, arXiv 2501.03200) -----------------------------
# * accuracy: sentence-level JSON template; a response is accurate only if NO sentence is
#   unsupported/contradictory (all-or-nothing);
# * eligibility: the instruction-following rubric, test response vs a baseline response; ineligible
#   only on "Major Issue(s)"; ineligible responses count as inaccurate;
# * score = share of responses that are eligible AND accurate (the paper averages 3 judges; we have 1).
# The judge sees what the agent saw: the request including "refer only to doc.txt", and the
# document labelled as that file (otherwise "According to doc.txt, ..." is marked unsupported).
FILE_NOTE = "[This document was given to the assistant as the file `doc.txt`.]\n\n"
BASELINE_ARM = "A0"  # eligibility reference: the plain agent's answer (same agent, same files mode). The baseline
#                      arm is not compared with itself and counts as eligible, which can only favour A0
#                      (conservative for "X beats A0" claims).


# Clarifications inserted into the sentence-level judge template, tuned on the DEV split with
# `python -m agent.judge_check` (does the judge's verdict change when "doc.txt" is replaced by "the document"?).
JUDGE_NOTES = {
    "J0": "",
    "J1": ("**Note on the setting:** The assistant was given the Context as a file named `doc.txt`, and the user "
           "asked it to rely only on that file. So `doc.txt`, \"the document\", \"the file\" and citation markers such "
           "as \"(doc.txt)\" all refer to the Context above. Such references are not claims to verify and never make "
           "a sentence unsupported by themselves; judge only what the sentence says about the content. A passage in "
           "quotation marks that the response attributes to the document is supported when it appears in the Context "
           "word for word (ignore differences in whitespace, quotation-mark style and capitalisation).\n\n"),
    # J2 = J1 without the quote clause (that clause could favour quoting arms). Only the setting mismatch:
    # the agent read doc.txt through a tool that shows line numbers; the judge's Context has neither.
    "J2": ("**Note on the setting:** The assistant read the Context as a file named `doc.txt` through a tool that "
           "shows line numbers. So `doc.txt`, \"the document\", \"the file\", citation markers such as \"(doc.txt)\" "
           "and line references such as \"(lines 25-53)\" all refer to the Context above. These references are not "
           "claims to verify and never make a sentence unsupported by themselves; judge only what the sentence says "
           "about the content.\n\n"),
}
JUDGE_NOTE = "J2"  # used by `score --variant official`; frozen after the dev-split check (judge_check: J0/J1/J2)
_NOTE_ANCHOR = "**Now, please analyze the following context and response:**"


def with_judge_note(tpl: str, note: str) -> str:
    if not note:
        return tpl
    assert _NOTE_ANCHOR in tpl, "judge template changed: note anchor not found"
    return tpl.replace(_NOTE_ANCHOR, note + _NOTE_ANCHOR)


def agent_request(ex: dict) -> str:
    return f"{ex['question']}\n\nIn your answer, refer only to the document in the file `doc.txt`. Do not employ any outside knowledge."


def _fill_official(tpl: str, ex: dict, answer: str) -> str:
    return (tpl.replace("{{user_request}}", agent_request(ex)).replace("{{context_document}}", FILE_NOTE + ex["doc"])
            .replace("{{response}}", answer))


def parse_rubric(text: str) -> str | None:
    hits = re.findall(r"(No Issues|Minor Issue\(s\)|Major Issue\(s\))", text)
    return hits[-1] if hits else None


def official_eligibility(ex: dict, answer: str, judge: LLM, tpl_elig: str, baseline: str) -> tuple[str | None, bool]:
    full_prompt = FILE_NOTE + ex["doc"] + "\n\n" + agent_request(ex)
    el = judge.chat([{"role": "user", "content": tpl_elig.replace("{{full_prompt}}", full_prompt)
                      .replace("{{response_a}}", answer).replace("{{response_b}}", baseline)}]).message["content"]
    verdict = parse_rubric(el)
    return verdict, verdict != "Major Issue(s)"  # unparseable -> eligible (the paper disqualifies only on Major)


def score_facts_official(ex: dict, answer: str, judge: LLM, tpl_sent: str, tpl_elig: str, baseline: str | None) -> dict:
    """baseline=None: this IS the baseline response -> no eligibility call, counted eligible."""
    sent = parse_sentence_labels(judge.chat([{"role": "user", "content": _fill_official(with_judge_note(tpl_sent, JUDGE_NOTES[JUDGE_NOTE]), ex, answer)}])
                                 .message["content"])
    accurate = (sent["unsupported"] + sent["contradictory"]) == 0
    verdict, eligible = official_eligibility(ex, answer, judge, tpl_elig, baseline) if baseline is not None else ("self", True)
    return {"accurate": accurate, "eligible": eligible, "eligibility_verdict": verdict,
            "correct": accurate and eligible, "correct_loose": None, "format_ok": True,
            **{f"sent_{k}": v for k, v in sent.items()}}


def first_draft(run_dir: Path) -> str | None:
    """The answer as it was BEFORE any verifier-driven revision (round-0 verdict draft)."""
    for e in read_trace(run_dir / "trace.jsonl"):
        if e["type"] == "verdict" and e.get("round") == 0:
            return e["draft"]
    return None


def _score_text(ex: dict, text: str, judge: LLM | None, tpls, cache: Path) -> dict:
    cached = json.loads(cache.read_text(encoding="utf-8")) if cache.exists() else None
    if cached and (ex["bench"] != "facts" or "sent_unsup_rate" in cached):
        return cached
    sc = score_facts(ex, text, judge, *tpls[:2]) if ex["bench"] == "facts" else score_rule(ex["bench"], text, ex["gold"])
    cache.write_text(json.dumps(sc), encoding="utf-8")
    return sc


def all_supported(sc: dict) -> bool | None:
    """FACTS: every graded sentence is supported (the original project's second metric)."""
    if sc.get("sent_unsup_rate") is None:
        return None
    return sc["sent_unsup_rate"] == 0


# scoring variants: "" = legacy protocol; noquote = legacy on quote-stripped answers; official = see above
VARIANTS = {"": None, "noquote": strip_quotes, "official": None}


def score_one(run_dir: Path, judge: LLM | None, tpls: tuple[str, str] | None, variant: str = "") -> dict:
    meta = json.loads((run_dir / "meta.json").read_text(encoding="utf-8"))
    ex = json.loads((run_dir / "example.json").read_text(encoding="utf-8"))
    raw = (run_dir / "answer.md").read_text(encoding="utf-8")
    answer = deliverable(raw)  # evidence-first arms: score only the <answer> body (no-op for other arms)
    if VARIANTS[variant]:
        answer = VARIANTS[variant](answer)
    if meta["status"] == "error":
        sc = sc_first = {"correct": False, "correct_loose": None, "format_ok": False}
    elif variant == "official":
        cache = run_dir / "score_official.json"
        sc = json.loads(cache.read_text(encoding="utf-8")) if cache.exists() else None
        if sc is not None and sc.get("judge_note", "J0") != JUDGE_NOTE:
            sc = None  # scored with another judge note: redo
        baseline = None
        if meta["arm"] != BASELINE_ARM:
            base_dir = run_dir.parent / f"{ex['id']}__{BASELINE_ARM}__r0"
            baseline = deliverable((base_dir / "answer.md").read_text(encoding="utf-8"))
        if sc is None:
            sc = score_facts_official(ex, answer, judge, tpls[1], tpls[2], baseline)
        elif sc.get("eligibility_baseline") != BASELINE_ARM:  # baseline changed: redo eligibility only
            sc["eligibility_verdict"], sc["eligible"] = (official_eligibility(ex, answer, judge, tpls[2], baseline)
                                                         if baseline is not None else ("self", True))
            sc["correct"] = sc["accurate"] and sc["eligible"]
        sc["eligibility_baseline"] = BASELINE_ARM
        sc["judge_note"] = JUDGE_NOTE
        if not answer.strip():  # e.g. output hit the token limit: no answer is never correct (nor "self"-eligible)
            sc.update(accurate=False, eligible=False, eligibility_verdict="empty", correct=False)
        cache.write_text(json.dumps(sc), encoding="utf-8")
        sc_first = sc
    elif variant:  # a variant re-scores the final answer only
        sc = sc_first = _score_text(ex, answer, judge, tpls, run_dir / f"score_{variant}.json")
    else:
        sc = _score_text(ex, answer, judge, tpls, run_dir / "score.json")
        # Within-run gate effect: score the pre-revision draft too (identical when nothing was revised).
        draft = first_draft(run_dir) if meta.get("revisions") else None
        sc_first = (_score_text(ex, deliverable(draft), judge, tpls, run_dir / "score_first.json")
                    if draft is not None else sc)
    first, final = meta.get("first_draft_issues"), meta.get("final_issues")
    _, _, rep = parse_run_name(run_dir.name)
    return {
        "bench": ex["bench"], "id": ex["id"], "arm": meta["arm"], "rep": rep, "status": meta["status"],
        "correct": sc["correct"], "correct_loose": sc.get("correct_loose"), "format_ok": sc["format_ok"],
        "unsup_rate": sc.get("sent_unsup_rate"), "all_supported": all_supported(sc),
        "eligible": sc.get("eligible"),
        "unsup_sents": (sc["sent_unsupported"] + sc["sent_contradictory"]) if "sent_unsupported" in sc else None,
        "correct_first": sc_first["correct"], "unsup_rate_first": sc_first.get("sent_unsup_rate"),
        "all_supported_first": all_supported(sc_first), "answer_chars": len(answer),
        "steps": meta.get("steps"), "revisions": meta.get("revisions"), "citations": meta.get("citations"),
        "first_draft_valid": None if first is None else first == 0,
        "final_valid": None if final is None else final == 0,
        "prompt_tokens": meta.get("prompt_tokens"), "completion_tokens": meta.get("completion_tokens"),
        "cache_hit_tokens": meta.get("cache_hit_tokens"), "wall_s": meta.get("wall_s"),
        **(ev_stats(raw) if meta.get("style", "inline").startswith("evidence") else {}),
    }


def _mean(s: pd.Series):
    s = s.dropna()
    return round(float(s.astype(float).mean()), 3) if len(s) else None


def cmd_score(a: argparse.Namespace) -> None:
    out = Path(a.out) / a.exp
    dirs = sorted(p for p in out.glob("*/*__*") if (p / "meta.json").exists())
    if a.arms:
        dirs = [p for p in dirs if p.name.split("__")[1] in a.arms.split(",")]
    facts = [p for p in dirs if p.parent.name == "facts"]
    tpls, judge = None, None
    if facts:
        pr = pd.read_csv(DATA / "facts_evaluation_prompts.csv")
        tpls = (_clean_prompt(pr[pr.evaluation_method == "response_level"].evaluation_prompt.iloc[0]),
                _clean_prompt(pr[pr.evaluation_method == "json"].evaluation_prompt.iloc[0]),
                _clean_prompt(pr[pr.evaluation_method == "ineligible_responses_filter_with_context"].evaluation_prompt.iloc[0]))
        judge = LLM(_judge_cfg())
    def safe(d: Path):
        try:
            return score_one(d, judge, tpls, a.variant)
        except Exception as e:  # noqa: BLE001 - one slow judge call must not lose the whole batch
            print(f"score failed (rerun `score` to retry): {d.name}: {type(e).__name__}: {e}"[:300], flush=True)
            return None

    with ThreadPoolExecutor(a.workers) as pool:
        rows = [r for r in pool.map(safe, dirs) if r is not None]
    if len(rows) < len(dirs):
        print(f"WARNING: {len(dirs) - len(rows)} runs not scored; summary covers {len(rows)} runs", flush=True)
    df = pd.DataFrame(rows)
    sfx = f"_{a.variant}" if a.variant else ""
    df.to_csv(out / f"scores{sfx}.csv", index=False)
    g = df.groupby(["bench", "arm"])
    summary = pd.DataFrame({
        "n_runs": g.size(),
        "acc": g.correct.apply(_mean),
        "acc_loose": g.correct_loose.apply(_mean),
        "unsup_rate": g.unsup_rate.apply(_mean),
        "all_sup": g.all_supported.apply(_mean),
        "eligible": g.eligible.apply(_mean),
        "unsup_sents": g.unsup_sents.apply(_mean),
        "chars": g.answer_chars.mean().round(0),
        "format_ok": g.format_ok.apply(_mean),
        "errors": g.status.apply(lambda s: int((s == "error").sum())),
        "revised": g.revisions.apply(lambda s: _mean(s.dropna().gt(0))),
        "cites": g.citations.apply(_mean),
        "uncited": g.citations.apply(lambda s: _mean(s.dropna().eq(0))),
        "cite_valid_1st": g.first_draft_valid.apply(_mean),
        "cite_valid_final": g.final_valid.apply(_mean),
        "tok_in": g.prompt_tokens.mean().round(0),
        "tok_out": g.completion_tokens.mean().round(0),
        "cache_hit": (g.cache_hit_tokens.sum() / g.prompt_tokens.sum()).round(2),
        "wall_s": g.wall_s.mean().round(1),
    }).reset_index()
    if "ev_format_ok" in df:  # evidence-first arms only
        ev = df.groupby(["bench", "arm"]).agg(ev_format_ok=("ev_format_ok", _mean), ev_items=("ev_items", _mean),
                                              ev_unmarked=("ev_unmarked_share", _mean)).reset_index()
        summary = summary.merge(ev, on=["bench", "arm"], how="left")
    summary.to_csv(out / f"summary{sfx}.csv", index=False)
    with pd.option_context("display.width", 250, "display.max_columns", 30):
        print(summary.to_string(index=False))
    print(f"\nwrote {out / f'scores{sfx}.csv'} and {out / f'summary{sfx}.csv'}")


# ===================================================================== paired comparison
def paired(df: pd.DataFrame, bench: str, metric: str, a: str, b: str, boots: int = 10000, seed: int = 0) -> dict | None:
    """Per-item paired difference b - a (reps averaged per item first) with a bootstrap 95% CI over items."""
    sub = df[(df.bench == bench) & (df.arm.isin([a, b]))][["id", "arm", metric]].dropna()
    if sub.empty:
        return None
    piv = sub.assign(v=sub[metric].astype(float)).groupby(["id", "arm"]).v.mean().unstack("arm")
    if a not in piv or b not in piv:
        return None
    piv = piv[[a, b]].dropna()
    if piv.empty:
        return None
    d = (piv[b] - piv[a]).to_numpy()
    rng = np.random.default_rng(seed)
    bs = d[rng.integers(0, len(d), (boots, len(d)))].mean(axis=1)
    lo, hi = np.percentile(bs, [2.5, 97.5])
    return {"bench": bench, "metric": metric, "a": a, "b": b, "items": len(d),
            "mean_a": round(float(piv[a].mean()), 3), "mean_b": round(float(piv[b].mean()), 3),
            "diff_b_minus_a": round(float(d.mean()), 3), "ci95_lo": round(float(lo), 3), "ci95_hi": round(float(hi), 3),
            "items_b_higher": int((d > 0).sum()), "items_b_lower": int((d < 0).sum())}


def cmd_compare(a: argparse.Namespace) -> None:
    out = Path(a.out) / a.exp
    sfx = f"_{a.variant}" if a.variant else ""
    df = pd.read_csv(out / f"scores{sfx}.csv")
    rows = []
    for bench in sorted(df.bench.unique()):
        for metric in a.metrics.split(","):
            r = paired(df, bench, metric, a.a, a.b)
            if r:
                rows.append(r)
    res = pd.DataFrame(rows)
    res.to_csv(out / f"compare_{a.a}_vs_{a.b}{sfx}.csv", index=False)
    with pd.option_context("display.width", 250, "display.max_columns", 30):
        print(res.to_string(index=False))
    print("\nnote: for unsup_rate LOWER is better; for every other metric higher is better.")


# ===================================================================== within-run gate effect
def _boot_ci(d: np.ndarray, boots: int = 10000, seed: int = 0) -> tuple[float, float]:
    if len(d) == 0:
        return (float("nan"), float("nan"))
    bs = d[np.random.default_rng(seed).integers(0, len(d), (boots, len(d)))].mean(axis=1)
    lo, hi = np.percentile(bs, [2.5, 97.5])
    return round(float(lo), 3), round(float(hi), 3)


def _bool(s: pd.Series) -> pd.Series:
    return s.map(lambda v: v if isinstance(v, bool) else str(v).strip().lower() == "true")


def gate_summary(df: pd.DataFrame, arm: str = "C2") -> pd.DataFrame:
    """Same run, before vs after the verifier gate. No sampling noise between the two: the only
    difference is the revision. Effects can only appear on revised runs, so they are reported there."""
    rows = []
    for bench, sub in df[df.arm == arm].groupby("bench"):
        rev = sub[sub.revisions.fillna(0) > 0]
        c0, c1 = _bool(sub.correct_first), _bool(sub.correct)
        row = {"bench": bench, "runs": len(sub), "revised": len(rev),
               "acc_first": round(float(c0.mean()), 3), "acc_final": round(float(c1.mean()), 3),
               "fixed": int((~c0 & c1).sum()), "broken": int((c0 & ~c1).sum()),
               "cite_valid_first": round(float(_bool(sub.first_draft_valid).mean()), 3),
               "cite_valid_final": round(float(_bool(sub.final_valid).mean()), 3)}
        if "all_supported" in sub and sub.all_supported.notna().any():
            a0 = sub.all_supported_first.dropna().map(lambda v: str(v).lower() == "true")
            a1 = sub.all_supported.dropna().map(lambda v: str(v).lower() == "true")
            row.update(all_sup_first=round(float(a0.mean()), 3), all_sup_final=round(float(a1.mean()), 3))
        u = rev[["unsup_rate_first", "unsup_rate"]].dropna()
        if len(u):
            d = (u.unsup_rate - u.unsup_rate_first).to_numpy(dtype=float)
            row.update(unsup_first_on_revised=round(float(u.unsup_rate_first.mean()), 3),
                       unsup_final_on_revised=round(float(u.unsup_rate.mean()), 3),
                       unsup_diff=round(float(d.mean()), 3), unsup_ci95=_boot_ci(d))
        rows.append(row)
    return pd.DataFrame(rows)


def cmd_gate(a: argparse.Namespace) -> None:
    out = Path(a.out) / a.exp
    res = gate_summary(pd.read_csv(out / "scores.csv"), a.arm)
    res.to_csv(out / f"gate_{a.arm}.csv", index=False)
    with pd.option_context("display.width", 250, "display.max_columns", 30):
        print(res.to_string(index=False))
    print("\nfixed/broken = runs whose correctness flipped between the first draft and the final answer.")


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--exp", required=True)
    r.add_argument("--bench", nargs="+", default=list(BENCHES), choices=BENCHES)
    r.add_argument("--n", type=int, default=8, help="examples per benchmark")
    r.add_argument("--seed", type=int, default=0)
    r.add_argument("--reps", type=int, default=1, help="repeat every (example, arm) this many times")
    r.add_argument("--arms", default="B0,C1,C2")
    r.add_argument("--exclude", nargs="*", default=[], help="skip examples used by these experiments (dev split)")
    r.add_argument("--ids", default="", help="split file with one example id per line (overrides --n/--seed/--exclude)")
    r.add_argument("--workers", type=int, default=4)
    r.add_argument("--max-steps", type=int, default=30)
    r.add_argument("--max-revisions", type=int, default=2)
    r.add_argument("--out", default="runs")
    r.set_defaults(fn=cmd_run)
    s = sub.add_parser("score")
    s.add_argument("--exp", required=True)
    s.add_argument("--workers", type=int, default=4)
    s.add_argument("--arms", default="", help="comma list; score only these arms (default: all)")
    s.add_argument("--out", default="runs")
    s.add_argument("--variant", default="", choices=sorted(VARIANTS),
                   help="noquote: delete every verbatim quote from the answer before judging (dilution check)")
    s.set_defaults(fn=cmd_score)
    c = sub.add_parser("compare")
    c.add_argument("--exp", required=True)
    c.add_argument("--a", default="C1")
    c.add_argument("--b", default="C2")
    c.add_argument("--metrics", default="correct,unsup_rate,final_valid")
    c.add_argument("--out", default="runs")
    c.add_argument("--variant", default="", choices=sorted(VARIANTS))
    c.set_defaults(fn=cmd_compare)
    gt = sub.add_parser("gate", help="first draft vs final answer within the same runs")
    gt.add_argument("--exp", required=True)
    gt.add_argument("--arm", default="C2")
    gt.add_argument("--out", default="runs")
    gt.set_defaults(fn=cmd_gate)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
