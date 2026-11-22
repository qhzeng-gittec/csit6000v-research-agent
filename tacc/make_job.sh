#!/usr/bin/env bash
# Assemble a self-contained tcloud job folder: Qwen service + agent.bench in one job.
#
#   bash tacc/make_job.sh <exp> <ids-file> <arms> [workers]
#   cd build/<exp> && tcloud submit
#
# Optional environment: JOB_TIME (default and partition maximum 01:00:00), LLM_MAX_TOKENS (8192),
# LLM_EXTRA_BODY (none), LLM_EMPTY_RETRY_BODY (thinking off), LLM_TIMEOUT_S (600).
set -euo pipefail
root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
exp=${1:?experiment name, e.g. tacc-demo}
ids=${2:?split file, e.g. splits/demo1.txt}
arms=${3:?arms, e.g. A0,A10}
workers=${4:-4}
data="$root/data/benchmarks/facts_examples.csv"
test -f "$data" || { echo 'Missing data: run python3 scripts/fetch_benchmarks.py first.' >&2; exit 1; }
test -f "$root/$ids" || { echo "Missing split file: $ids" >&2; exit 1; }
# 32K context on the course service: 8192 output tokens leave room for the prompt. The model thinks by
# default, as in our OpenRouter runs; only the retry of an empty reply switches thinking off.
retry=${LLM_EMPTY_RETRY_BODY:-}
[[ -n "$retry" ]] || retry='{"chat_template_kwargs":{"enable_thinking":false}}'

job="$root/build/$exp"
rm -rf -- "$job"
mkdir -p "$job/data/benchmarks"
cp -R "$root/agent" "$root/splits" "$job/"
find "$job" -name __pycache__ -type d -prune -exec rm -rf {} +
cp "$data" "$job/data/benchmarks/"
cp "$root"/tacc/{job.sh,service_supervisor.py,client.py,client.sh,preflight.py} "$job/"
sed "s/time=01:00:00/time=${JOB_TIME:-01:00:00}/" "$root/tacc/tuxiv.conf" > "$job/tuxiv.conf"
{
    printf 'EXP=%q\nIDS=%q\nARMS=%q\nWORKERS=%q\n' "$exp" "$ids" "$arms" "$workers"
    printf 'LLM_MAX_TOKENS=%q\n' "${LLM_MAX_TOKENS:-8192}"
    printf 'LLM_EXTRA_BODY=%q\n' "${LLM_EXTRA_BODY:-}"
    printf 'LLM_EMPTY_RETRY_BODY=%q\n' "$retry"
    printf 'LLM_TIMEOUT_S=%q\n' "${LLM_TIMEOUT_S:-600}"
} > "$job/run.env"
echo "Job folder ready: $job"
echo "Next: cd $job && tcloud submit"
