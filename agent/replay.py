"""Offline replay: re-run the verifier on a saved run's FIRST draft. No model call needed.

    python -m agent.replay runs/smoke/q1-quote
"""
from __future__ import annotations

import argparse
import json
import os
from dataclasses import asdict
from pathlib import Path

from .trace import read_trace
from .verify import Corpus, verify


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("run_dir")
    ap.add_argument("--corpus", default=os.environ.get("CORPUS_DIR", "/corpus"))
    ap.add_argument("--cite", default=None, help="override the cite mode stored in meta.json")
    args = ap.parse_args()

    run = Path(args.run_dir)
    cite = args.cite or json.loads((run / "meta.json").read_text(encoding="utf-8"))["cite"]
    tool_events: list[dict] = []
    draft = None
    for e in read_trace(run / "trace.jsonl"):
        if e["type"] == "tool":
            tool_events.append(e)
        elif e["type"] == "assistant" and not e.get("tool_calls"):
            draft = e["content"]
            break
    if draft is None:
        raise SystemExit("no draft answer found in trace")
    issues = verify(draft, cite, Corpus(args.corpus), tool_events)
    print(json.dumps([asdict(i) for i in issues], indent=2, ensure_ascii=False) if issues else "OK: no issues")


if __name__ == "__main__":
    main()
