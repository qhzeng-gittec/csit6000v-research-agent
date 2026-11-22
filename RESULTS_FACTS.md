# FACTS Grounding results

Model under test: `qwen/qwen3.8-27b` (OpenRouter, temperature 0). Judge: `gpt-6.2-sol`.
All numbers are on the **test split**: 100 FACTS Grounding public items, 1 run per item and arm.
Every method choice was made on a separate dev split first (see Protocol).

## 1. What is measured

Each FACTS item is a long document plus a user request. The agent does not get the document in its
prompt: the document is saved as `doc.txt` and the agent must read it with its read-only tools.

The judge uses the official FACTS prompts (`data/benchmarks/facts_evaluation_prompts.csv`):

| metric | how it is computed | example |
|---|---|---|
| **accurate** | Sentence-level judge (official JSON template): every sentence of the answer is labelled supported / unsupported / contradictory / no_rad (needs no support). The answer is accurate only if **no** sentence is unsupported or contradictory. | 14 sentences, 13 supported, 1 says "the most significant change" while the document says "perhaps the most significant" → not accurate |
| **eligible** | Official instruction-following rubric: is the answer a real attempt at the request? Ineligible only on "Major Issue(s)" (evasive, off-topic, missing the main ask). | "The document covers several topics." for a 600-word request → ineligible |
| **correct** (main metric) | accurate AND eligible. Empty answers count as incorrect. | |
| unsupported sentences / answer | count of unsupported + contradictory sentences | |
| unsup rate | unsupported sentences / all graded sentences | |
| supported sentences / answer, chars | how much the answer says | |

**Why the score cannot be raised by writing less.** Fewer sentences means fewer chances to be wrong, so
we check three things beside `correct`: (1) eligibility catches evasive answers; (2) answer length;
(3) supported sentences per answer, which only goes up if the answer says more that is grounded.

**Differences from the official FACTS score.** One judge instead of several; 100 sampled public items
instead of the full public + private set. The eligibility rubric compares an answer with a baseline
answer; ours is the plain agent's answer (A0). A0 itself is not compared with itself and counts as
eligible, which can only favour A0, so every "better than A0" result is conservative.
Because the judge sees the document as the file `doc.txt` and the agent's answers mention that file
and line numbers, the judge prompt adds one paragraph saying that file names, citation markers and
line references refer to the context and are not claims by themselves (`agent/bench.py: JUDGE_NOTES`).

The `correct` level is low for every arm because it is all-or-nothing over about 14 sentences:
with 95% of sentences supported, 0.95^14 ≈ 0.49 of answers are fully correct. It is not comparable
with the public leaderboard (different judges, different model).

## 2. Main result: building the system step by step

| step | arm | correct | eligible | unsup sentences / answer | unsup rate | supported sentences / answer | chars |
|---|---|---|---|---|---|---|---|
| plain agent | A0 | 0.27 | 1.00 (reference) | 2.16 | 0.170 | 11.4 | 2452 |
| + 4 writing rules | A9 | 0.43 | 0.98 | 1.04 | 0.098 | 11.4 | 2275 |
| + verbatim quotes | A8 | 0.51 | 0.95 | 0.82 | 0.071 | 13.7 | 2527 |
| + quote verifier (full system) | **A10** | **0.57** | 0.97 | **0.78** | 0.072 | 13.3 | 2431 |

Paired differences over the same 100 items, 95% bootstrap CI (10,000 resamples):

| step | correct | unsup sentences / answer | unsup rate | chars |
|---|---|---|---|---|
| A9 - A0 (rules) | **+0.16 [+0.06, +0.26]** | -1.12 [-1.48, -0.78] | -0.072 [-0.103, -0.040] | -177 [-279, -81] |
| A8 - A9 (quotes) | +0.08 [-0.04, +0.20] | -0.22 [-0.55, +0.09] | **-0.027 [-0.054, -0.001]** | +252 [+152, +361] |
| A10 - A8 (verifier) | +0.06 [-0.04, +0.16] | -0.04 [-0.32, +0.23] | +0.001 [-0.019, +0.021] | -95 [-225, +24] |
| **A10 - A0 (whole system)** | **+0.30 [+0.19, +0.41]** | **-1.38 [-1.76, -1.01]** | **-0.098 [-0.129, -0.068]** | -21 [-122, +80] |

Reading the table:
- **Rules** give the largest jump, but part of it comes from shorter answers (A9 is 7% shorter and does
  not say more grounded things: 11.4 supported sentences, same as A0).
- **Verbatim quotes** make answers longer again and add grounded content (13.7 supported sentences,
  the most of all steps) while the share of unsupported sentences falls further. `correct` rises by
  0.08: A8 is better on 23 items and worse on 15.
- **The verifier** adds 0.06 on `correct`; its main job is different: every quote the user sees is
  real (see Section 3).
- **Whole system**: `correct` doubles (0.27 → 0.57) at the same answer length; eligibility stays at
  0.97 against a reference that is itself counted as 1.00.

## 3. The verifier: what it guarantees and what it does not

The verifier (`agent/verify.py`) checks every quote mechanically: the quoted text must exist in the
cited file, match it word for word (after whitespace/quote normalisation), and appear in a tool result
the agent actually saw. It makes no semantic judgement. In A10 a failed quote is sent back and the
model fixes only that spot with `edit_draft` (at most 2 rounds; a revision that shrinks the answer below
60% of the draft is rejected).

| | A8 (quotes, failures only logged) | A10 (failures sent back) |
|---|---|---|
| answers revised | 0% | 30% |
| quotes that match the document, final answer | 0.68 | **1.00** |
| failed quotes per answer, final answer | 0.75 | 0.00 |
| output tokens per answer | 2327 | 2591 (+11%) |
| correct (judge) | 0.51 | 0.57 |

Without the verifier about one quote in three that the user sees is not in the document, so the user
could not find it there. With the verifier every quote can be located in the source. The judge score
moves less than quote validity because a failed quote is usually a paraphrase of a true statement,
not a false claim: the judge asks "is this supported?", the verifier asks "is this quote real?".

## 4. Side issue fixed in the agent loop: empty answers

Seven test runs first ended with no answer at all. Trace: for a request such as "about 600 words" the
model counted words one by one in its hidden reasoning until it used the full 16k output budget
(`finish_reason=length`, empty content). This happens inside one model call, so step limits and
repeated-call counters cannot see it. The loop now treats an empty reply as a "said but did nothing"
ending: it is sent back with a short nudge (at most 2 times) and the retry
caps reasoning at 4,000 tokens; if it is still empty the run is recorded as `empty`, never as
`answered`. All seven runs answer after the fix; the numbers above include them.

## 5. Failure case: a real quote used wrongly, and why the product design tolerates it

Most remaining unsupported sentences are not invented facts. They wrap a correct quote in words that
claim a little more than the document:
- "For felony DUI, the document explains the circumstances that elevate **the charge**: "The enhanced
  penalties are direct outcomes of ..."" — the quote is about penalties, not about the charge.
- "**The authors note** that "further in vivo, animal and clinical trials would be required ..."" —
  the document does not attribute this to the study's authors.
- "The most significant change was "the institution of the first national income tax"" — the document
  says *perhaps* the most significant.

The verifier passes all three: the quotes are real. Rule-based detection does not help either. On the
dev split, patterns such as superlatives ("most", "only"), two quotes in one sentence, or attribution
to "the authors" flag sentences that are wrong only 9-20% of the time. Recap sentences ("So, ...",
"Overall, ...") are wrong 54% of the time, but the writing rules already removed most of them. Catching
the rest needs a per-sentence semantic check, which is what the judge does, so we do not put one in
the loop.

**Why this is acceptable for the product.** The goal is not an answer the user must trust blindly, but
an answer the user can check. Every claim carries the exact source text, and the verifier guarantees
that this text is really in the document, so the user can jump to it. In all three cases above the
mistake is visible right next to the quote: the reader sees "enhanced penalties", "perhaps", or that
no author is named. A small overstatement in the model's own words is then caught by the reader in
seconds, instead of being hidden in an unreferenced summary. The same errors in an answer without
quotes (A0) cannot be checked without rereading the whole document.

## 6. Limitations and expected variation
- One judge model. Judging the same answers twice changes unsupported sentences per answer by
  at most 0.1 and flips `accurate` on 4 of 58 dev answers (A0, A8), about 7%; expect about ±0.05 on
  `correct` per arm.
- Temperature 0, but provider-side sampling is not deterministic; a rerun of the agent gives
  different answers. The ordering A0 < A9 < A8, A10 and the whole-system gain should hold; the size of
  the two smaller steps (+0.08 for quotes, +0.06 for the verifier) can change between reruns.
- 100 items; a larger sample would narrow the intervals of the smaller steps.
- The writing rules were written after reading dev-split judge output; the test split guards against
  fitting those 30 items, not against fitting this judge's general preferences.

## 7. Runs on the course cluster (TACC)

The same agent was run on TACC against the course's model service: Qwen3.8-27B with 4-bit AWQ weights,
served by vLLM 0.26 on two 24 GB GPUs, 32K context, 4 requests in parallel. One job starts the service,
runs the agent and stops the service (`tacc/job.sh`). Items: the first 25 test ids
(`splits/facts_tacc25.txt`); arms A0 and A10; one run per item and arm. The method was not changed for
these runs; the two TACC settings below differ only in whether the model thinks before it answers.

| where the model ran | arm | runs that ended with an answer | model calls / run | answers revised | answers whose quotes all exist | output tokens / run | seconds / run |
|---|---|---|---|---|---|---|---|
| OpenRouter (Section 2, same 25 items) | A0 | 25 / 25 | 3.0 | - | - | 1907 | 11.7 |
| | A10 | 25 / 25 | 3.7 | 24% | 100% | 3162 | 18.6 |
| TACC, thinking on (job 30810) | A0 | 25 / 25 | 3.2 | - | - | 1987 | 48.3 |
| | A10 | 24 / 25 (1 empty) | 4.1 | 24% | 100% | 3093 | 71.4 |
| TACC, thinking off (job 30789) | A0 | 25 / 25 | 3.6 | - | - | 630 | 22.9 |
| | A10 | 21 / 25 (3 out of steps, 1 unresolved) | 7.6 | 24% | 88% | 1029 | 38.3 |

These numbers need no judge (`python3 scripts/run_stats.py runs/tacc-facts25-think`). With thinking on,
the verifier path behaves on TACC as it does on OpenRouter: one answer in four is sent back, and after
revision every quote in every final answer exists in the document.

**Judge scores.** Judge for this section: `claude-haiku-5-5` through Anthropic's OpenAI-compatible
endpoint (`JUDGE_TEMPERATURE` empty, because the model rejects the parameter; `JUDGE_MAX_TOKENS=32000`),
official protocol as in Section 1. Section 2 used another judge, so levels cannot be compared across the
two sections; the OpenRouter answers of the same 25 items were scored again with this judge
(`runs/openrouter-facts25`).

| answers from | correct, A0 | correct, A10 | A10 - A0 [95% CI] | unsupported sentences / answer, A0 and A10 | A10 - A0 [95% CI] |
|---|---|---|---|---|---|
| OpenRouter (25 items of Section 2) | 0.48 | 0.80 | +0.32 [+0.16, +0.52] | 0.84 and 0.40 | -0.44 [-0.76, -0.08] |
| TACC, thinking on | 0.76 | 0.72 | -0.04 [-0.28, +0.20] | 0.52 and 0.60 | +0.08 [-0.48, +0.76] |
| TACC, thinking off | 0.76 | 0.84 | +0.08 [-0.08, +0.24] | 0.64 and 0.36 | -0.28 [-0.68, +0.12] |

Reading the table:
- The second judge confirms Section 2 on the OpenRouter answers: +0.32 with this judge, +0.20 with the
  original judge on the same 25 items (0.32 and 0.52), +0.30 on all 100 items.
- On TACC the gain in `correct` is not reproduced at this sample size. The plain agent already scores 0.76
  there (6 of 25 answers contain an unsupported sentence, against 13 of 25 for the OpenRouter answers), so
  less is left to gain, and with 25 items an interval of about 0.2 either way cannot separate the arms. The
  A10 number with thinking on includes the empty answer of failure case 2, counted as incorrect.
- We do not know why the plain agent makes fewer unsupported statements on TACC than through OpenRouter.
  The weights (4-bit AWQ on TACC), the serving stack and the output limit differ, and 25 items are few; we
  report the difference without attributing it.
- What carries over to TACC is the property the verifier is responsible for: with thinking on, every
  quote in every final A10 answer exists in the document.

**Failure case 1: repeated tool calls when thinking is off.** Three A10 runs used all 30 steps and one
stayed `unresolved`. One run resent the same rejected `edit_draft` call 24 times (its `old` text was
398 characters; the limit is 300, and the error message says so). One issued an `edit_draft` whose `new`
text equalled `old` 23 times. One read the document with 28 `bash` calls and never wrote a draft. The
step limit and the two-round revision limit ended all of them, and their status
(`budget_exhausted`, `unresolved`) shows that they did not pass, so no unverified quote is presented as
verified. What it shows: the loop bounds the number of calls but does not notice that a call is
identical to the previous one. None of this happened with thinking on, on TACC or on OpenRouter, so the
method was left unchanged; a check for identical consecutive calls is the obvious next guard.

**Failure case 2: an empty answer when thinking is on.** For "about 600 words" the model counted words in
its reasoning until the 8,192-token output limit, three times in a row. This is the case of Section 4,
but the retry there limits reasoning with an OpenRouter option that vLLM does not have, so on TACC the
retry changed nothing. The retry can now send provider-specific fields (`LLM_EMPTY_RETRY_BODY`); the TACC
job uses it to switch thinking off for the retry only. Job 30823 reran the item with this setting
(`runs/tacc-check`): the first reply was empty again after 8,192 tokens of reasoning, and the retry
answered in 15 seconds.

**Judge robustness.** Before the judge above we tried `deepseek-flash`, which thinks before it answers.
With the default 16,384-token limit,
6 of 50 judge outputs came back empty because the whole limit went into reasoning, and the scorer
counted an output without any unsupported label as accurate. A cut-off or label-free judge output is now
an error that is retried on the next `score` run, and the limit is configurable (`JUDGE_MAX_TOKENS`). The
400 scores of Section 2 are not affected: none of them has zero labels. In a spot check with thinking
switched off, the same judge labelled all 22 graded sentences of one answer as supported where the
thinking judge found 11 unsupported; a judge of this kind is only usable with thinking on.

## Protocol
- **Dev split** (`splits/facts_dev30.txt`, sampled with seed 1): 30 items x 2 runs. All rules, arms and
  the judge setting were chosen here.
- **Test split** (`splits/facts_test100.txt`, seed 2, disjoint from dev): 100 items x 1 run, run once
  after the method was frozen. A9 and A10 are ablations of the frozen system, not tuning steps.

## Appendix: development log (dev split, legacy single-template scoring)
Arms tried on the dev split before freezing: A4/A5 (evidence block first, then the answer: answers
20% shorter, no gain), A6 (verbatim quotes + "state only what the document says"), A7 (A6 + one nudge
when there is no quote: +70% output tokens, no gain), A8 (A6 + 3 rules written from A6's unsupported
sentences). A semantic grounding check by a second model inside the loop was tried and
dropped, because it is the judge's own task. Raw dev numbers: `runs/facts-files30/summary.csv`.
