"""Judge-free summary of an experiment: what can be read from meta.json and trace.jsonl alone.

    python3 scripts/run_stats.py runs/<exp> [ids-file]

Per arm: run status, model calls, revisions, quote validity (verifier), tokens, and speed.
Standard library only; with an ids file only those items are counted.
"""
import collections
import json
import sys
from pathlib import Path


def mean(values):
    values = [v for v in values if v is not None]
    return round(sum(values) / len(values), 2) if values else None


def main() -> None:
    exp = Path(sys.argv[1])
    ids = set(Path(sys.argv[2]).read_text(encoding="utf-8").split()) if len(sys.argv) > 2 else None
    runs, calls = collections.defaultdict(list), collections.defaultdict(list)
    for run_dir in sorted(exp.glob("*/*__*")):
        if not (run_dir / "meta.json").exists():
            continue
        meta = json.loads((run_dir / "meta.json").read_text(encoding="utf-8"))
        if ids is not None and meta["id"] not in ids:
            continue
        meta["chars"] = len((run_dir / "answer.md").read_text(encoding="utf-8"))
        runs[meta["arm"]].append(meta)
        for line in (run_dir / "trace.jsonl").open(encoding="utf-8"):
            event = json.loads(line)
            if event["type"] == "assistant":
                usage = event.get("usage") or {}
                calls[meta["arm"]].append((event.get("latency_ms", 0), usage.get("completion_tokens", 0), usage.get("prompt_tokens", 0)))
    for arm, metas in sorted(runs.items()):
        cited = [m for m in metas if m.get("final_issues") is not None]
        seconds = sum(c[0] for c in calls[arm]) / 1000
        print(f"{arm}: runs={len(metas)} status={dict(collections.Counter(m['status'] for m in metas))}")
        print(f"   model_calls_per_run={mean([m.get('steps') for m in metas])}"
              f" revised={mean([1.0 if m.get('revisions') else 0.0 for m in metas])}"
              f" quotes_valid_first_draft={mean([1.0 if m['first_draft_issues'] == 0 else 0.0 for m in cited])}"
              f" quotes_valid_final={mean([1.0 if m['final_issues'] == 0 else 0.0 for m in cited])}"
              f" quotes_per_answer={mean([m.get('citations') for m in cited])} answer_chars={mean([m['chars'] for m in metas])}")
        print(f"   input_tokens_per_run={mean([m.get('prompt_tokens') for m in metas])}"
              f" output_tokens_per_run={mean([m.get('completion_tokens') for m in metas])}"
              f" seconds_per_run={mean([m.get('wall_s') for m in metas])}"
              f" seconds_per_call={round(seconds / max(1, len(calls[arm])), 2)}"
              f" output_tokens_per_second={round(sum(c[1] for c in calls[arm]) / max(1e-9, seconds), 1)}"
              f" largest_prompt={max([c[2] for c in calls[arm]] or [0])}")


if __name__ == "__main__":
    main()
