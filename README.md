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
tests/            109 unit tests (no API key needed)
web/              local web interface: `python -m web.server` (Check 4)
scripts/          fetch_benchmarks.py (downloads FACTS + FaithEval), run_stats.py (judge-free run summary)
splits/           facts_dev30.txt, facts_test100.txt: the exact item ids used; demo1.txt: one item for the demo
tacc/             one job for the course cluster: starts the Qwen service, runs the agent, stops the service
runs/             our runs: answers, traces, scores (facts-test100 = main results, facts-files30 = dev,
                  tacc-facts100 = the same 100 test items run on TACC). Score files without a judge name
                  come from the main judge; files ending in `_haiku` come from the second judge,
                  `claude-haiku-5-5`
RESULTS_FACTS.md  all results, method, failure case, limitations
```

# Getting Started Instructions

### Prerequisites
- Linux or macOS with Docker and Docker Compose v2 (tested with Docker 27).
- Python 3.9+ on the host, only for downloading the data (standard library only).
- An OpenAI-compatible API key for the agent model. We used `qwen/qwen3.8-27b` on OpenRouter.
- For scoring: an OpenAI-compatible key for the judge model (we used `gpt-6.2-sol`, and
  `claude-haiku-5-5` as a second judge).
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
Expected: `109 passed`. The tests cover the loop (including the empty-reply guard), tools, verifier,
`edit_draft`, scoring logic, the web interface with a scripted model, and that `splits/*.txt` equal the
sampled splits.

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

### Check 4: the web interface on your own machine (no API key, about 1 minute)
The interface shows on one screen what the system does: the agent's steps as they happen, the answer
with every quote marked as found or not found by the verifier, and the document with the quoted passages
highlighted. It runs on localhost only.
```bash
docker compose build                 # once; the image contains web/
docker compose run --rm -p 8000:8000 --entrypoint python agent -m web.server --host 0.0.0.0
```
Then open http://127.0.0.1:8000. Without Docker: `pip install -r requirements.txt` and `python -m web.server`.

Without a model key the page opens the runs saved under `runs/`. On the start page choose
"Verifier at work". Expected, in this order: the tool calls (`Read lines 1 to 49 of doc.txt`), a red step
"Verifier found 1 problem" that shows the quote which is not in the document, "Sent back to the model,
revision round 1", "Edited the draft", a green step "Verifier passed", and then the answer under the line
"All 3 quotes found word for word in the document". Click a green quote: the document on the right
scrolls to the passage and highlights it. The buttons above the answer (Plain, Rules, Quotes, Full system)
open the other configurations of the same question, and the menu in the sidebar switches between the
OpenRouter runs and the TACC runs.

To ask your own question, start the server with the settings of the agent model, attach a text or
Markdown file and type a question:
```bash
export LLM_API_KEY=<your key> LLM_BASE_URL=https://openrouter.ai/api/v1 LLM_MODEL=qwen/qwen3.8-27b
docker compose run --rm -p 8000:8000 --entrypoint python agent -m web.server --host 0.0.0.0
```
"Full system" answers with verified quotes; "Plain agent" is the same agent without quotes and without
the verifier. Every question is saved under `runs/web/` and listed in the sidebar under "Your questions".

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
If your judge thinks before it answers, give it room with `JUDGE_MAX_TOKENS` (default 16384; we used
32000 for `claude-haiku-5-5`). If it rejects the `temperature` parameter, set `JUDGE_TEMPERATURE` to an empty
value (also needed for `claude-haiku-5-5`). A judge output that is cut off or has no labels is reported as `score failed`
and scored again on the next `score` run; it is never counted as accurate.

To keep our scores and put yours next to them, do not delete anything and give your judge a name:
`--judge mine` (for `score` and `compare`) writes `score_official_mine.json` per answer and
`*_official_mine.csv` per experiment. Our second judge is stored this way, as `--judge haiku`.

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
Both arms of the headline comparison on all 100 test items are 200 runs. A job may run for at most one
hour, so we ran the items as two jobs of 50 that write into the same experiment:
```bash
head -50 splits/facts_test100.txt > splits/half_a.txt
tail -50 splits/facts_test100.txt > splits/half_b.txt
JOB_NAME=tacc-facts100-a bash tacc/make_job.sh tacc-facts100 splits/half_a.txt A0,A10 4
JOB_NAME=tacc-facts100-b bash tacc/make_job.sh tacc-facts100 splits/half_b.txt A0,A10 4
(cd build/tacc-facts100-a && tcloud submit); (cd build/tacc-facts100-b && tcloud submit)
# when both jobs have finished:
tcloud download scholar-agent/results/tacc-facts100.tar.gz ./tacc-facts100.tar.gz
tar -xzf tacc-facts100.tar.gz -C runs                      # in the repository root
python3 scripts/run_stats.py runs/tacc-facts100            # judge-free numbers, table below
```
Our jobs took 31 and 59 minutes (model start-up 10 and 26 minutes, the agent runs 21 and 32 minutes).
Each job packs the whole experiment folder when it ends, so the archive of the job that ends last holds
all runs. Runs are stored in your TACC user directory as they finish, so a job that hits the time limit
can simply be submitted again and continues where it stopped. Scoring works as in Option A, on your own
machine. We scored the TACC runs with `claude-haiku-5-5` and stored the scores under the judge name
`haiku`:
```bash
export JUDGE_API_KEY=<key> JUDGE_BASE_URL=https://api.anthropic.com/v1/ JUDGE_MODEL=claude-haiku-5-5
export JUDGE_TEMPERATURE= JUDGE_MAX_TOKENS=32000   # this judge rejects `temperature` and thinks first
docker compose run --rm -e LLM_TIMEOUT_S=600 --entrypoint python agent \
  -m agent.bench score --exp tacc-facts100 --variant official --judge haiku --workers 8
docker compose run --rm --entrypoint python agent -m agent.bench compare --exp tacc-facts100 \
  --variant official --judge haiku --a A0 --b A10 --metrics correct,unsup_rate,unsup_sents,answer_chars
```

Settings on TACC (`tacc/make_job.sh`): the model thinks by default, as in our OpenRouter runs;
`LLM_MAX_TOKENS=8192` leaves room for the prompt in the 32K context; the retry of an empty reply switches
thinking off (`LLM_EMPTY_RETRY_BODY`), because the reasoning cap used on OpenRouter does not exist in vLLM.

Numbers that need no judge (`scripts/run_stats.py`), next to the OpenRouter runs of the same 100 items:

| where the model ran | arm | runs that ended with an answer | model calls / run | answers revised | answers whose quotes all exist | output tokens / run | seconds / run |
|---|---|---|---|---|---|---|---|
| OpenRouter (`runs/facts-test100`) | A0 | 100 / 100 | 3.0 | - | - | 1491 | 10.5 |
| | A10 | 100 / 100 | 3.9 | 30% | 100% | 2591 | 17.8 |
| TACC (`runs/tacc-facts100`) | A0 | 99 / 100 (1 context error) | 3.0 | - | - | 1301 | 34.1 |
| | A10 | 98 / 100 (1 context error, 1 unresolved) | 4.3 | 31% | 99% (98 of 99) | 2845 | 69.1 |

The system behaves on TACC as it does on OpenRouter: the verifier sends back the same share of answers
(31% and 30%), and after revision every quote exists in the document in 98 of 99 answers. The remaining
answer is marked `unresolved`, so it is not presented as verified. Two items show limits: one document
does not fit into the 32K context of the course service (an `error` run in both arms), and one document
contains a character the model cannot type, so its quote never matched. Both are described in
RESULTS_FACTS.md, Section 7. TACC serves about 40 output tokens per second per request (4 requests in
parallel), OpenRouter about 145.

Judge scores, 100 items, paired bootstrap CI. The TACC answers and the OpenRouter answers were scored by
the same judge, `claude-haiku-5-5`; the first row repeats the main result, which uses another judge:

| answers from | judge | correct, A0 | correct, A10 | A10 - A0 [95% CI] |
|---|---|---|---|---|
| OpenRouter | `gpt-6.2-sol` (main result) | 0.27 | 0.57 | +0.30 [+0.19, +0.41] |
| OpenRouter | `claude-haiku-5-5` | 0.60 | 0.80 | +0.20 [+0.09, +0.30] |
| TACC | `claude-haiku-5-5` | 0.64 | 0.80 | +0.16 [+0.06, +0.26] |

The gain of the full system over the plain agent is reproduced on TACC: A10 is better on 22 items and
worse on 6, and the interval excludes zero. A second judge gives higher levels than the main judge but
the same direction on the OpenRouter answers, so compare arms under one judge, not levels across judges.
Details and three failure cases are in RESULTS_FACTS.md, Section 7.

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
| runs on TACC: status, revisions, quote validity, tokens, time | `python3 scripts/run_stats.py runs/tacc-facts100` | Section 7 |
| second judge (`claude-haiku-5-5`): TACC answers and the A0 and A10 answers of the main result | `summary_official_haiku.csv`, `compare_A0_vs_A10_official_haiku.csv` and `score_official_haiku.json` per answer, in `runs/tacc-facts100` and `runs/facts-test100` | Section 7 |

### Dev split
Every method choice was made on `splits/facts_dev30.txt` (30 items x 2 runs) before the test split
was run once. To rerun it: `--exp my-dev --ids splits/facts_dev30.txt --reps 2`.

### Expected variation and known limitations
- Neither the agent nor the judge is deterministic. Expect about ±0.05 on `correct` per arm. The
  ordering A0 < A9 < A8, A10 and the gains of the rules and of the whole system should reproduce; the
  size of the two smaller steps (+0.08 quotes, +0.06 verifier) can change between reruns.
- With a different judge model the absolute numbers move; compare arms, not levels.
- 100 public items and one judge for the four-arm table; a second judge scored the A0 and A10 answers
  only. This is not the official multi-judge FACTS score.
- The verifier proves that quotes are real; it cannot prove that a quote supports the sentence around
  it. That remaining gap is the main source of errors (RESULTS_FACTS.md, Section 5).
- FaithEval loaders exist in `agent/bench.py` but FaithEval is not part of the reported evaluation.
- TACC: two arms only (A0, A10), scored by the second judge. The model there has 4-bit weights and a
  32K context. A request whose prompt plus `LLM_MAX_TOKENS` exceeds 32K is rejected by the service and
  recorded as an `error` run; this happened for one of the 100 documents, in both arms
  (RESULTS_FACTS.md, Section 7).
