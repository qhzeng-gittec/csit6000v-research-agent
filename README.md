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
tests/            98 unit tests (no API key needed)
scripts/          fetch_benchmarks.py (downloads FACTS + FaithEval)
splits/           facts_dev30.txt, facts_test100.txt: the exact item ids used; demo1.txt: one item for the demo
runs/             our runs: answers, traces, scores (facts-test100 = main results, facts-files30 = dev)
RESULTS_FACTS.md  all results, method, failure case, limitations
```

# Getting Started Instructions

### Prerequisites
- Linux or macOS with Docker and Docker Compose v2 (tested with Docker 27).
- Python 3.9+ on the host, only for downloading the data (standard library only).
- An OpenAI-compatible API key for the agent model. We used `qwen/qwen3.8-27b` on OpenRouter.
- For scoring: an OpenAI-compatible key for the judge model (we used `gpt-6.2-sol`).

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
Expected: `98 passed`. The tests cover the loop (including the empty-reply guard), tools, verifier,
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
