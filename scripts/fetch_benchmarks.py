"""Download the official benchmark files used in the evaluation (~27 MB in total).

    python scripts/fetch_benchmarks.py [--out data/benchmarks]

Sources (Hugging Face, no login needed):
  Salesforce/FaithEval-{unanswerable,inconsistent,counterfactual}-v1.0
  google/FACTS-grounding-public   (CC-BY-4.0)
Files that already exist with the expected size are skipped.
"""
import argparse
import sys
import urllib.request
from pathlib import Path

BASE = "https://huggingface.co/datasets/{repo}/resolve/main/{file}"
FILES = [
    ("Salesforce/FaithEval-unanswerable-v1.0", "data/test-00000-of-00001.parquet", "faitheval_unanswerable.parquet", 3178294),
    ("Salesforce/FaithEval-inconsistent-v1.0", "data/test-00000-of-00001.parquet", "faitheval_inconsistent.parquet", 2650076),
    ("Salesforce/FaithEval-counterfactual-v1.0", "data/test-00000-of-00001.parquet", "faitheval_counterfactual.parquet", 1637656),
    ("google/FACTS-grounding-public", "examples.csv", "facts_examples.csv", 19719340),
    ("google/FACTS-grounding-public", "evaluation_prompts.csv", "facts_evaluation_prompts.csv", 12851),
]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/benchmarks")
    out = Path(ap.parse_args().out)
    out.mkdir(parents=True, exist_ok=True)
    for repo, remote, local, size in FILES:
        dest = out / local
        if dest.exists() and dest.stat().st_size == size:
            print(f"skip   {local} (already present)")
            continue
        print(f"fetch  {local}  <- {repo}/{remote}")
        with urllib.request.urlopen(BASE.format(repo=repo, file=remote), timeout=120) as r, dest.open("wb") as fh:
            while chunk := r.read(1 << 20):
                fh.write(chunk)
        got = dest.stat().st_size
        if got != size:
            sys.exit(f"size mismatch for {local}: expected {size}, got {got}")
    print(f"done -> {out}")


if __name__ == "__main__":
    main()
