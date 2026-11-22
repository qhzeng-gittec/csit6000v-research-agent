# scholar-agent: a citation-verifiable document QA agent

A small tool-calling agent that answers questions about documents it must read itself, quotes the
source word for word, and has every quote checked by a program before the answer is accepted.
It is a self-contained system built for the CSIT6000V course project.

**Main result** (FACTS Grounding, 100 held-out items; details in [RESULTS_FACTS.md](RESULTS_FACTS.md)):

| step | correct (accurate AND eligible) | unsupported sentences / answer | quotes that exist in the document |
|---|---|---|---|
| plain agent (A0) | 0.27 | 2.16 | - |
| + writing rules (A9) | 0.43 | 1.04 | - |
| + verbatim quotes (A8) | 0.51 | 0.82 | 0.68 |
| + quote verifier, full system (A10) | **0.57** | **0.78** | **1.00** |

Whole system vs plain agent: +0.30 correct [95% CI +0.19, +0.41] at the same answer length.

## How it works

```
question ──► model ──tool call──► read / bash (read-only) ──► result appended ──┐
               ▲                                                               │
               └───────────────────────────────────────────────────────────────┘
               no tool call = draft answer
                     │
                     ▼
               verifier: is every "quote" (file) in the file, word for word,
               and in a tool result the model actually saw?
                 ├─ yes ─► answer
                 └─ no ──► <verification> message; model may only patch the flagged
                           spots with edit_draft(old, new); max 2 rounds
```

| part | file | what it does |
|---|---|---|
| loop | `agent/loop.py` | "no tool call = finished"; bounded revision rounds; collapse guard (a revision that shrinks the answer below 60% is rejected); empty-reply guard (nudge at most 2 times, reasoning capped on retry, else status `empty`) |
| tools | `agent/tools.py` | `read(path, offset, limit)` with line numbers, read-only `bash` (ls, grep, sed -n, ...), `edit_draft` only during revision; outputs capped at 8,000 chars |
| prompts | `agent/prompts.py` | citation mode (`none` / `quote`) and writing rules (`STRICT`, `STRICT_PLUS`) |
| verifier | `agent/verify.py` | deterministic quote checks: exists, exact, seen in a tool result |
| trace | `agent/trace.py` | every model call, tool call and verdict in `trace.jsonl` |
| evaluation | `agent/bench.py` | runs arms on benchmark items, scores with the FACTS judge, paired bootstrap CIs |

The agent can only read: `bash` accepts a fixed list of read-only commands (ls, grep, find, head,
tail, wc, nl, cat, sed) without redirection or command substitution, and each run works on its own copy
of the document inside the container.

## Repository layout

```
agent/            agent, verifier, benchmark runner (agent/bench.py), judge calibration (agent/judge_check.py)
tests/            104 unit tests (no API key needed)
scripts/          fetch_benchmarks.py (downloads FACTS + FaithEval), run_stats.py (judge-free run summary)
splits/           facts_dev30.txt, facts_test100.txt: the exact item ids used; demo1.txt: one item for the demo;
                  facts_tacc25.txt: the first 25 test ids, used for the runs on TACC
tacc/             one job for the course cluster: starts the Qwen service, runs the agent, stops the service
runs/             our runs: answers, traces, scores (facts-test100 = main results, facts-files30 = dev,
                  tacc-facts25* and tacc-check = runs on TACC, openrouter-facts25 = the same 25 items of
                  facts-test100, scored again with the judge used for the TACC runs)
RESULTS_FACTS.md  all results, method, failure case, limitations
```

# Getting Started Instructions

### Prerequisites
- Linux or macOS with Docker and Docker Compose v2 (tested with Docker 27).
- Python 3.9+ on the host, only for downloading the data (standard library only).
- An OpenAI-compatible API key for the agent model. We used `qwen/qwen3.8-27b` on OpenRouter.
- For scoring: an OpenAI-compatible key for the judge model (we used `gpt-6.2-sol`).
- Without any key for the agent model: the course cluster TACC, where the agent uses the course's
  Qwen3.8-27B service (Check 3 below). This needs the `tcloud` SDK instead of Docker.

Keys are read from environment variables and are never written into the image; see `.env.example`.

### Setup (about 3 minutes)
```bash
git clone https://github.com/qhzeng-gittec/csit6000v-research-agent && cd csit6000v-research-agent
docker compose build
python3 scripts/fetch_benchmarks.py          # ~27 MB from Hugging Face into data/benchmarks/
```

### Check 1: unit tests (no API key, a few seconds)
```bash
docker compose run --rm --entrypoint python agent -m pytest -q tests
```
Expected: `104 passed`. The tests cover the loop (including the empty-reply guard), tools, verifier,
`edit_draft`, scoring logic, and that `splits/*.txt` equal the sampled splits.

### Check 2: one FACTS item end to end with the full system (~1 minute)
```bash
export LLM_API_KEY=<your key> LLM_BASE_URL=https://openrouter.ai/api/v1 LLM_MODEL=qwen/qwen3.8-27b
docker compose run --rm --entrypoint python agent -m agent.bench run --exp demo --bench facts   --ids splits/demo1.txt --reps 1 --arms A10 --workers 1
cat runs/demo/facts/facts0028__A10__r0/answer.md
cat runs/demo/facts/facts0028__A10__r0/meta.json
```
The item asks "How did the Interim Final Rule change the Head Start rules that govern child safety?"
about a long regulation. Expected (wording varies between runs):
```
1 runs, 1 workers -> runs/demo
[1/1] errors=0 last: facts facts0028 A10 r0 answered

According to `doc.txt`, before November 30, 2021, the Head Start rules governing child safety
(45 C.F.R. § 1302.47(b)(5)) required only that "[a]ll staff and consultants follow appropriate
practices to keep children safe during all activities," ... "(doc.txt)
...
meta.json: "status": "answered", "first_draft_issues": 1, "final_issues": 0, "revisions": 1 or 2
```
`runs/demo/facts/facts0028__A10__r0/trace.jsonl` shows the whole run: `grep`/`read` tool calls, a
`verdict` with `ok: false` (a quote that is not in the document), the `<verification>` message sent back,
the model's `edit_draft` patch, and a final `verdict` with `ok: true`. In our run the first draft had one
failed quote and the final answer has none. 30 of the 100 A10 test runs went through this path; to open
one of ours:
```bash
grep -l '"revisions": 1' runs/facts-test100/facts/*__A10__r0/meta.json | head -1
```

### Check 3: the same item on TACC with the course Qwen service (no API key, about 15 minutes)
On the course cluster the agent uses the Qwen3.8-27B model served by vLLM. One job starts the model,
runs the agent against it and stops the model again, so no service address has to be copied by hand.
Prerequisites: the `tcloud` SDK configured for your account, and the course environment registered once
with `bash setup-sdk-account.sh` from the course package `qwen27b-student-release`.
```bash
python3 scripts/fetch_benchmarks.py                      # if not done in Setup
bash tacc/make_job.sh tacc-demo splits/demo1.txt A10 1   # writes the job folder build/tacc-demo
cd build/tacc-demo && tcloud submit                       # prints the job id
tcloud ps -j <job id>                                     # PD = queued, R = running
tcloud cat slurm_log/scholar-agent-<job id>.log
tcloud download scholar-agent/results/tacc-demo.tar.gz ./tacc-demo.tar.gz
```
Expected at the end of the log, in this order:
```
SERVICE_READY after 390s
PREFLIGHT OK
1 runs, 1 workers -> .../scholar-agent/runs/tacc-demo
[1/1] errors=0 last: facts facts0028 A10 r0 answered
RESULT_FILE=scholar-agent/results/tacc-demo.tar.gz
```
The model takes 5 to 7 minutes to start (about 20 minutes the very first time, while vLLM fills the
compile cache in your user directory); the run itself takes about 2 minutes. The archive has the same
layout as `runs/<exp>/`: `answer.md`, `trace.jsonl` and `meta.json` for every run.

What the job does (`tacc/job.sh`):
- It takes the course launcher `serve.sh`, binds it to the node's loopback address and adds
  `--enable-auto-tool-choice --tool-call-parser qwen3_xml`. The stock course service has tool calling
  switched off, and this model writes tool calls in the Qwen3 XML format.
- `tacc/service_supervisor.py`, taken from the course package `cinecontext-qwen-e2e`, starts the service
  and the client and stops the service when the client exits, so the GPUs are released.
- The client waits until the service answers, runs `tacc/preflight.py` (one request must come back as a
  structured tool call) and then `agent.bench run` with the course Python environment. That environment
  has no pandas, so `agent.bench run` works without it; scoring is done on your own machine.

# Detailed Instructions

### Configurations (arms)
All arms: same model, temperature 0, at most 30 steps, document given as the file `doc.txt`
(wrapped at 100 characters), the same task text as FACTS ("refer only to the document ...").

| arm | citation | writing rules (`agent/prompts.py`) | verifier sends failed quotes back | role |
|---|---|---|---|---|
| A0 | none | none | - | plain agent; also the baseline answer for the eligibility rubric |
| A9 | none | STRICT + STRICT_PLUS (4 rules) | - | + rules |
| A8 | verbatim quotes | STRICT + STRICT_PLUS | no (logged only) | + quotes |
| **A10** | verbatim quotes | STRICT + STRICT_PLUS | **yes** (max 2 rounds) | full system |

Definitions in `agent/bench.py: ARMS`.

### Option A: re-score our answers (judge only; 2 judge calls per answer, 400 answers)
`runs/facts-test100/` contains every answer and trace behind the tables. Delete the cached scores and
score again with your judge:
```bash
export JUDGE_API_KEY=<key> JUDGE_BASE_URL=<OpenAI-compatible URL> JUDGE_MODEL=<model>
find runs/facts-test100/facts -name score_official.json -delete
docker compose run --rm -e LLM_TIMEOUT_S=600 --entrypoint python agent \
  -m agent.bench score --exp facts-test100 --variant official --workers 6
```
If your judge thinks before it answers, give it room with `JUDGE_MAX_TOKENS` (default 16384; we needed
65536 for `deepseek-flash`). If it rejects the `temperature` parameter, set `JUDGE_TEMPERATURE` to an empty
value (needed for `claude-haiku-5-5`). A judge output that is cut off or has no labels is reported as `score failed`
and scored again on the next `score` run; it is never counted as accurate.

### Option B: rerun the agent and score (~1 hour, about 5M input + 1M output tokens)
```bash
export LLM_API_KEY=<key> LLM_BASE_URL=https://openrouter.ai/api/v1 LLM_MODEL=qwen/qwen3.8-27b
export JUDGE_API_KEY=<key> JUDGE_BASE_URL=<URL> JUDGE_MODEL=<model>
docker compose run --rm -e LLM_TIMEOUT_S=400 --entrypoint python agent \
  -m agent.bench run --exp my-test --bench facts --ids splits/facts_test100.txt \
  --reps 1 --arms A0,A9,A8,A10 --workers 6
docker compose run --rm -e LLM_TIMEOUT_S=600 --entrypoint python agent \
  -m agent.bench score --exp my-test --variant official --workers 6
```
Runs resume: a finished run is skipped, a failed one is retried. Use a new `--exp` name for a fresh run.

### Option C: rerun on TACC with the course Qwen service (no agent API key)
One job runs both arms of the headline comparison on the first 25 test items (50 runs, about 22 minutes
including model start-up; the partition allows at most one hour per job):
```bash
bash tacc/make_job.sh tacc-facts25-think splits/facts_tacc25.txt A0,A10 4
cd build/tacc-facts25-think && tcloud submit
tcloud download scholar-agent/results/tacc-facts25-think.tar.gz ./tacc-facts25-think.tar.gz
tar -xzf tacc-facts25-think.tar.gz -C runs                      # in the repository root
python3 scripts/run_stats.py runs/tacc-facts25-think            # judge-free numbers, table below
```
Runs are stored in your TACC user directory as they finish, so a job that hits the time limit can simply
be submitted again and continues where it stopped. Scoring works as in Option A, on your own machine.
We scored the TACC runs with `claude-haiku-5-5`:
```bash
export JUDGE_API_KEY=<key> JUDGE_BASE_URL=https://api.anthropic.com/v1/ JUDGE_MODEL=claude-haiku-5-5
export JUDGE_TEMPERATURE= JUDGE_MAX_TOKENS=32000   # this judge rejects `temperature` and thinks first
docker compose run --rm -e LLM_TIMEOUT_S=600 --entrypoint python agent \
  -m agent.bench score --exp tacc-facts25-think --variant official --workers 8
```

Settings on TACC (`tacc/make_job.sh`): the model thinks by default, as in our OpenRouter runs;
`LLM_MAX_TOKENS=8192` leaves room for the prompt in the 32K context; the retry of an empty reply switches
thinking off (`LLM_EMPTY_RETRY_BODY`), because the reasoning cap used on OpenRouter does not exist in vLLM.
To run with thinking off, as the course client does:
`LLM_MAX_TOKENS=4096 LLM_EXTRA_BODY='{"chat_template_kwargs":{"enable_thinking":false}}' bash tacc/make_job.sh tacc-facts25 ...`.

Our TACC runs are in `runs/tacc-facts25-think/` and `runs/tacc-facts25/`. Numbers that need no judge
(`scripts/run_stats.py`), next to the OpenRouter runs of the same 25 items:

| where the model ran | arm | runs that ended with an answer | model calls / run | answers revised | answers whose quotes all exist | output tokens / run | seconds / run |
|---|---|---|---|---|---|---|---|
| OpenRouter (from `runs/facts-test100`) | A0 | 25 / 25 | 3.0 | - | - | 1907 | 11.7 |
| | A10 | 25 / 25 | 3.7 | 24% | 100% | 3162 | 18.6 |
| TACC, thinking on (default) | A0 | 25 / 25 | 3.2 | - | - | 1987 | 48.3 |
| | A10 | 24 / 25 (1 empty) | 4.1 | 24% | 100% | 3093 | 71.4 |
| TACC, thinking off | A0 | 25 / 25 | 3.6 | - | - | 630 | 22.9 |
| | A10 | 21 / 25 (3 out of steps, 1 unresolved) | 7.6 | 24% | 88% | 1029 | 38.3 |

With thinking on, the system behaves on TACC as it does on OpenRouter: the same share of answers is sent
back by the verifier and every quote in the final answers exists in the document. With thinking off the
4-bit model is faster per call but gets stuck in repeated tool calls; see RESULTS_FACTS.md, Section 7.
TACC serves about 28 to 43 output tokens per second per request (4 requests in parallel), OpenRouter about 165.

Judge scores for the same three sets of answers (judge `claude-haiku-5-5`, 25 items, paired bootstrap CI):

| answers from | correct, A0 | correct, A10 | A10 - A0 [95% CI] |
|---|---|---|---|
| OpenRouter | 0.48 | 0.80 | +0.32 [+0.16, +0.52] |
| TACC, thinking on | 0.76 | 0.72 | -0.04 [-0.28, +0.20] |
| TACC, thinking off | 0.76 | 0.84 | +0.08 [-0.08, +0.24] |

A second judge confirms the gain on the OpenRouter answers. On TACC the plain agent already scores 0.76
on these items, and 25 items cannot separate the two arms there; what carries over to TACC is the
verifier's guarantee about quotes. Details and the open question in RESULTS_FACTS.md, Section 7.

### Comparisons (paired bootstrap CI)
```bash
for p in "A0 A9" "A9 A8" "A8 A10" "A0 A10"; do set -- $p
  docker compose run --rm --entrypoint python agent -m agent.bench compare --exp facts-test100 \
    --variant official --a $1 --b $2 --metrics correct,unsup_rate,unsup_sents,answer_chars
done
```

### Where each result comes from

| result | file written | in RESULTS_FACTS.md |
|---|---|---|
| per-arm table (correct, eligible, unsupported sentences, chars, quote validity, tokens) | `runs/<exp>/summary_official.csv` (`acc` = correct; `cite_valid_final` = quotes that exist) | Section 2, Section 3 |
| paired differences with CIs | `runs/<exp>/compare_<a>_vs_<b>_official.csv` | Section 2 |
| per-answer scores and judge labels | `runs/<exp>/facts/<item>__<arm>__r0/score_official.json` | Sections 2, 5 |
| revision counts | `meta.json` per run (`revisions`, `first_draft_issues`, `final_issues`) | Section 3 |
| empty-answer fix | `trace.jsonl` notes `empty_reply`; tests in `tests/test_loop.py` | Section 4 |
| judge noise floor (same answer judged twice) | `python -m agent.judge_check --exp facts-files30 --arms A0,A8 --notes J2` | Section 6 |
| runs on TACC: status, revisions, quote validity, tokens, time | `python3 scripts/run_stats.py runs/tacc-facts25-think` (and `runs/tacc-facts25`) | Section 7 |
| judge scores of the TACC runs and of the same items on OpenRouter | `summary_official.csv` and `compare_A0_vs_A10_official.csv` in `runs/tacc-facts25-think`, `runs/tacc-facts25`, `runs/openrouter-facts25` | Section 7 |

### Dev split
Every method choice was made on `splits/facts_dev30.txt` (30 items x 2 runs) before the test split
was run once. To rerun it: `--exp my-dev --ids splits/facts_dev30.txt --reps 2`.

### Expected variation and known limitations
- Neither the agent nor the judge is deterministic. Expect about ±0.05 on `correct` per arm. The
  ordering A0 < A9 < A8, A10 and the gains of the rules and of the whole system should reproduce; the
  size of the two smaller steps (+0.08 quotes, +0.06 verifier) can change between reruns.
- With a different judge model the absolute numbers move; compare arms, not levels.
- One judge, 100 public items; not the official multi-judge FACTS score.
- The verifier proves that quotes are real; it cannot prove that a quote supports the sentence around
  it. That remaining gap is the main source of errors (RESULTS_FACTS.md, Section 5).
- FaithEval loaders exist in `agent/bench.py` but FaithEval is not part of the reported evaluation.
- TACC: 25 items and two arms only; the model there has 4-bit weights and a 32K context. A request whose
  prompt plus `LLM_MAX_TOKENS` exceeds 32K is rejected by the service and recorded as an `error` run
  (none occurred; the largest prompt was 14K tokens). With thinking off the model can loop on a repeated
  tool call until the step limit (RESULTS_FACTS.md, Section 7).
