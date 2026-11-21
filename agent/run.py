"""CLI: python -m agent.run --question "..." [--cite none|line|quote] [--style ...] [--no-gate]"""
from __future__ import annotations

import argparse
import json
import os
import time
from dataclasses import asdict
from pathlib import Path

from .llm import LLM, LLMConfig
from .loop import run_agent
from .prompts import CITE, STYLES, system_prompt
from .tools import Tools
from .trace import Trace
from .verify import Corpus


def main() -> None:
    ap = argparse.ArgumentParser(description="Minimal read-only paper QA agent")
    ap.add_argument("--question", required=True)
    ap.add_argument("--corpus", default=os.environ.get("CORPUS_DIR", "/corpus"))
    ap.add_argument("--out", default="runs/adhoc", help="parent directory for the run folder")
    ap.add_argument("--cite", choices=sorted(CITE), default="none")
    ap.add_argument("--gate", action=argparse.BooleanOptionalAction, default=True,
                    help="send failed citation checks back for local revision (default on)")
    ap.add_argument("--style", choices=STYLES, default="inline",
                    help="writing rules: inline_strict_plus = the 4 rules of arms A8/A10 (with --cite quote), "
                         "plain_strict_plus = the same rules without citations (arm A9)")
    ap.add_argument("--max-revisions", type=int, default=2)
    ap.add_argument("--max-steps", type=int, default=20)
    ap.add_argument("--run-id", default=None)
    args = ap.parse_args()

    cfg = LLMConfig.from_env()
    run_id = args.run_id or time.strftime("%Y%m%d-%H%M%S")
    run_dir = Path(args.out) / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    trace = Trace(run_dir / "trace.jsonl")

    t0 = time.monotonic()
    result = run_agent(
        question=args.question,
        llm=LLM(cfg),
        tools=Tools(args.corpus),
        trace=trace,
        system=system_prompt(args.cite, "files", args.style),
        max_steps=args.max_steps,
        cite=args.cite,
        corpus=Corpus(args.corpus),
        gate=args.gate,
        max_revisions=args.max_revisions,
    )
    wall_s = round(time.monotonic() - t0, 2)
    trace.log("final", answer=result.answer, status=result.status)
    trace.close()

    meta = {
        "question": args.question,
        "cite": args.cite,
        "style": args.style,
        "gate": args.gate,
        "model": cfg.model,
        "base_url": cfg.base_url,
        "temperature": cfg.temperature,
        "max_steps": args.max_steps,
        "max_revisions": args.max_revisions,
        "wall_s": wall_s,
        **{k: v for k, v in asdict(result).items() if k != "answer"},
    }
    (run_dir / "meta.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
    (run_dir / "answer.md").write_text(result.answer, encoding="utf-8")

    print(result.answer)
    hit = f" cache_hit={result.cache_hit_tokens}" if result.cache_hit_tokens else ""
    print(f"\n--- status={result.status} steps={result.steps} revisions={result.revisions} edits={result.edits} "
          f"tokens={result.prompt_tokens}+{result.completion_tokens}{hit} wall={wall_s}s trace={run_dir / 'trace.jsonl'}")


if __name__ == "__main__":
    main()
