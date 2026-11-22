#!/usr/bin/env bash
# One TACC job: start the course Qwen service with tool calling enabled, run agent.bench against it,
# then stop the service. Adapted from the course package cinecontext-qwen-e2e.
set -euo pipefail
umask 077
: "${TACC_WORKDIR:?Submit with tcloud submit}"
: "${TACC_USERDIR:?Submit with tcloud submit}"
: "${SLURM_JOB_ID:?Submit with tcloud submit}"
: "${CONDA_PREFIX:?SDK must activate the shared proxy environment}"
printf 'SDK_BOOTSTRAP=%s\n' "$CONDA_PREFIX"
source /mnt/home/public/course-envs/CSIT6000V/project/activate.sh
trap 'rm -rf -- "$QWEN_RUN_DIR"' EXIT
trap 'exit 143' TERM
trap 'exit 130' INT
export QWEN_CACHE_HOME="$TACC_USERDIR/CSIT6000V-project-cache"
mkdir -p -m 700 "$QWEN_CACHE_HOME"
hostname
port=$((20000 + SLURM_JOB_ID % 20000))
nvidia-smi --query-gpu=index,uuid,memory.free,memory.total --format=csv
mapfile -t visible_gpus < <(nvidia-smi --query-gpu=index --format=csv,noheader)
if [[ ${#visible_gpus[@]} -ne 2 ]]; then
    echo 'Expected exactly two GPU devices in the Slurm job'
    exit 1
fi
export CUDA_VISIBLE_DEVICES="${visible_gpus[0]},${visible_gpus[1]}"
# Course launcher, bound to this node only, plus tool calling: the model's chat template
# writes tool calls in the Qwen3 XML format, which vLLM parses with `qwen3_xml`.
sed -e "s/--host 0.0.0.0/--host 127.0.0.1/" -e '/^export CUDA_VISIBLE_DEVICES=/d' -e "s/--port 8000/--port $port/" \
    -e "s/--enable-prefix-caching/--enable-prefix-caching --enable-auto-tool-choice --tool-call-parser qwen3_xml/" \
    "$QWEN_PROJECT_ROOT/serve.sh" > "$QWEN_RUN_DIR/serve-agent.sh"
grep -q -- '--tool-call-parser qwen3_xml' "$QWEN_RUN_DIR/serve-agent.sh" || {
    echo 'The course serve.sh changed: could not add the tool-calling flags.' >&2
    exit 1
}
export QWEN_BASE_URL="http://127.0.0.1:$port/v1"
export no_proxy="${no_proxy:+$no_proxy,}127.0.0.1,localhost"
export NO_PROXY="$no_proxy"
/usr/bin/python3 -u "$TACC_WORKDIR/service_supervisor.py" \
    "$QWEN_RUN_DIR/serve-agent.sh" "$TACC_WORKDIR/client.py" &
supervisor_pid=$!
forward_stop() {
    kill -"$1" "$supervisor_pid" 2>/dev/null || true
    wait "$supervisor_pid" || true
    exit "$2"
}
trap 'forward_stop TERM 143' TERM
trap 'forward_stop INT 130' INT
wait "$supervisor_pid"
