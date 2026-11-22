#!/usr/bin/env bash
# Runs inside the TACC job once the service is ready: preflight, then the benchmark runs.
set -euo pipefail
cd "$TACC_WORKDIR"
source ./run.env
export LLM_BASE_URL="$QWEN_BASE_URL" LLM_API_KEY=EMPTY LLM_MODEL=qwen3.8-27b
export LLM_MAX_TOKENS LLM_EXTRA_BODY LLM_EMPTY_RETRY_BODY LLM_TIMEOUT_S
# Same as the course's `qwen-python` (a shell function, so not visible in this child process).
python=("$QWEN_PROJECT_ROOT/runtime.sh" "$QWEN_PROJECT_ROOT/vllm-env/bin/python")
out="$TACC_USERDIR/scholar-agent/runs"

bash "${python[@]}" -u preflight.py
bash "${python[@]}" -u -m agent.bench run --exp "$EXP" --bench facts --ids "$IDS" --reps 1 \
    --arms "$ARMS" --workers "$WORKERS" --out "$out"

mkdir -p "$TACC_USERDIR/scholar-agent/results"
tar -czf "$TACC_USERDIR/scholar-agent/results/$EXP.tar.gz" -C "$out" "$EXP"
echo "RESULT_FILE=scholar-agent/results/$EXP.tar.gz"
