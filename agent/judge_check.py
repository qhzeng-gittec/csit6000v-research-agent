"""Judge calibration (run on the DEV split): does the FACTS sentence judge penalise the file name?

For every answer the judge labels
  orig  - the answer as delivered,
  neut  - the same answer with every `doc.txt` mention replaced by "the document" and citation
          markers like "(doc.txt)" dropped (same content, no file name),
  orig2 - the original again (noise floor: how much the judge disagrees with itself).
A judge without the artifact gives orig and neut the same unsupported count (up to the noise floor).
Two direct counts on the orig labels:
  blame_file     - unsupported/contradictory sentences whose rationale mentions the file / its name;
  verbatim_only  - unsupported sentences that consist only of quotes found word for word in the document.

    python -m agent.judge_check --exp facts-files30 --arms A0,A8 --notes J2
"""
from __future__ import annotations

import argparse
import json
import re
import statistics as st
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd

from . import bench
from .evidence import deliverable
from .llm import LLM

BAD = ("unsupported", "contradictory")


def neutralize(text: str) -> str:
    text = re.sub(r"\s*\(\s*`?doc\.txt`?[^)]*\)", "", text)  # (doc.txt), (doc.txt, lines 3-5)
    return re.sub(r"`?doc\.txt`?", "the document", text)


def _norm(s: str) -> str:
    s = s.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    return re.sub(r"\s+", " ", s).strip().lower()


def verbatim_only(sentence: str, doc: str) -> bool:
    quotes = re.findall(r'"([^"]{15,})"', sentence.replace("“", '"').replace("”", '"'))
    if not quotes:
        return False
    d = _norm(doc)
    if not all(_norm(q).strip(" .,;:") in d for q in quotes):
        return False
    rest = re.sub(r'"[^"]{15,}"', "", sentence.replace("“", '"').replace("”", '"'))
    rest = re.sub(r"\(?`?doc\.txt`?\)?|the document (states|says|notes)|according to|as stated", "", rest, flags=re.I)
    return len(re.findall(r"[A-Za-z]", rest)) <= 25


def blames_file(rationale: str) -> bool:
    return bool(re.search(r"doc\.txt|file ?name|the file\b|source file|which document", rationale, re.I))


def parse_rows(text: str) -> list[dict]:
    rows = []
    for line in text.splitlines():
        line = line.strip().strip(",")
        if line.startswith("{"):
            try:
                o = json.loads(line)
            except json.JSONDecodeError:
                continue
            rows.append({"sentence": str(o.get("sentence", "")), "label": str(o.get("label", "")).strip().lower(),
                         "rationale": str(o.get("rationale", ""))})
    return rows


def run_one(run_dir: Path, note_key: str, kind: str, judge: LLM, tpl: str, out: Path) -> dict | None:
    cache = out / note_key / f"{run_dir.name}__{kind}.json"
    if cache.exists():
        return json.loads(cache.read_text(encoding="utf-8"))
    ex = json.loads((run_dir / "example.json").read_text(encoding="utf-8"))
    answer = deliverable((run_dir / "answer.md").read_text(encoding="utf-8"))
    if not answer.strip():
        return None
    text = neutralize(answer) if kind == "neut" else answer
    prompt = bench._fill_official(bench.with_judge_note(tpl, bench.JUDGE_NOTES[note_key]), ex, text)
    rows = parse_rows(judge.chat([{"role": "user", "content": prompt}]).message["content"])
    rec = {"run": run_dir.name, "arm": run_dir.name.split("__")[1], "note": note_key, "kind": kind, "rows": rows,
           "unsup": sum(r["label"] in BAD for r in rows),
           "blame_file": sum(r["label"] in BAD and blames_file(r["rationale"]) for r in rows),
           "verbatim_only": sum(r["label"] == "unsupported" and verbatim_only(r["sentence"], ex["doc"]) for r in rows)}
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(rec, ensure_ascii=False, indent=1), encoding="utf-8")
    return rec


def report(recs: list[dict]) -> pd.DataFrame:
    by = {(r["note"], r["run"], r["kind"]): r for r in recs}
    out = []
    for note in sorted({r["note"] for r in recs}):
        for arm in sorted({r["arm"] for r in recs}) + ["all"]:
            runs = sorted({r["run"] for r in recs if r["note"] == note and (arm == "all" or r["arm"] == arm)})
            trip = [(by.get((note, x, "orig")), by.get((note, x, "neut")), by.get((note, x, "orig2"))) for x in runs]
            trip = [t for t in trip if all(t)]
            if not trip:
                continue
            o, n, o2 = zip(*trip)
            out.append({
                "judge": note, "arm": arm, "answers": len(trip),
                "unsup/ans orig": round(st.mean(r["unsup"] for r in o), 2),
                "unsup/ans neut": round(st.mean(r["unsup"] for r in n), 2),
                "neut-orig": round(st.mean(b["unsup"] - a["unsup"] for a, b in zip(o, n)), 2),
                "noise orig2-orig": round(st.mean(b["unsup"] - a["unsup"] for a, b in zip(o, o2)), 2),
                "accurate flips neut": sum((a["unsup"] == 0) != (b["unsup"] == 0) for a, b in zip(o, n)),
                "accurate flips noise": sum((a["unsup"] == 0) != (b["unsup"] == 0) for a, b in zip(o, o2)),
                "blame_file": sum(r["blame_file"] for r in o + o2),
                "verbatim_only": sum(r["verbatim_only"] for r in o + o2),
            })
    return pd.DataFrame(out)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--exp", required=True)
    p.add_argument("--arms", default="A0,A8")
    p.add_argument("--notes", default="J0,J1")
    p.add_argument("--rep", type=int, default=0)
    p.add_argument("--workers", type=int, default=8)
    p.add_argument("--out", default="runs")
    a = p.parse_args()
    root = Path(a.out) / a.exp
    dirs = sorted(d for d in (root / "facts").glob(f"*__*__r{a.rep}")
                  if d.name.split("__")[1] in a.arms.split(",") and (d / "answer.md").exists())
    pr = pd.read_csv(bench.DATA / "facts_evaluation_prompts.csv")
    tpl = bench._clean_prompt(pr[pr.evaluation_method == "json"].evaluation_prompt.iloc[0])
    judge = LLM(bench._judge_cfg())
    jobs = [(d, n, k) for n in a.notes.split(",") for d in dirs for k in ("orig", "neut", "orig2")]

    def safe(job):
        try:
            return run_one(*job, judge, tpl, root / "judgecheck")
        except Exception as e:  # noqa: BLE001 - rerun to retry
            print(f"failed {job[0].name} {job[1]} {job[2]}: {type(e).__name__}: {e}"[:200], flush=True)
            return None

    with ThreadPoolExecutor(a.workers) as pool:
        recs = [r for r in pool.map(safe, jobs) if r]
    df = report(recs)
    print(df.to_string(index=False))
    df.to_csv(root / "judgecheck" / "summary.csv", index=False)


if __name__ == "__main__":
    main()
