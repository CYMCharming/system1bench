# Strong prompted LLM baseline v1 (pre-inference protocol)

## Question and boundary

The historical 8B LLM baselines select the highest single next-token candidate-code
logit. This experiment asks whether a **fixed prompted generation adapter** changes
their decisions on the *same* held-out System1Bench requests. The evaluated object
is a model plus its prompt, parser and generation settings, not a whole downstream
system, and this is not an optimization search for either model's best performance.

All inputs, references and original-baseline rows come from the immutable
`data/frozen.json` and `results/{model}` outputs. We use one predeclared question
per sampled state and retain its original state, instructions, criteria, candidate
order and gold label. Source data or model errors are never used to choose cases.
For the mixed Typed Decisions suite the prespecified question is `urgency`,
the only ordinal decision shared by all four scenario generators.

## Sampling

`freeze.py` deterministically selects the 18 predeclared suites in its `SPECS`:
12 states per suite except 8 long-policy JevBench states (212 states in all).
Sorting is by SHA-256 of `strong-baseline-v1\0<suite>\0<case-id>` followed by
case ID. CLINC150/OOS is selected as six `oos` and six named intents to ensure
the rejection transition is tested; its balanced subset is *not* prevalence
representative. The other suites use simple hash sampling and therefore can
also differ from their source prevalence. No cross-domain pooled accuracy is
interpreted as a natural population estimate. The source-balanced sample spans
all 15 source collections in the current atlas; it does not add new domains.

The exact case IDs, input/reference hashes, selected question, source, domain,
and reference label are frozen in `frozen.json`; `manifest.json` binds the input
file, code and protocol. The scripts refuse changed hashes.

## Predeclared model conditions

Models: the original local Llama-3.1-8B-Instruct and Qwen3-8B snapshots, one
resident A100 per process, BF16/SDPA, seed 0, native chat template, Qwen
`enable_thinking=False`, zero demonstrations, greedy decoding, no truncation.
Use the same candidate-code assignment and JSON payload as the historical
`llm_adapter.messages` conversion. The state is delimited as data, never as
instructions. Neither labels nor rationales enter the prompt.

* `direct`: the historical prompt, now greedily generated up to 16 new tokens.
  Valid only if the entire stripped response is one allowed code.
* `deliberate`: the same JSON payload with a fixed instruction to explain in at
  most two short sentences and end with a standalone `FINAL: <CODE>` line;
  greedily generate up to 128 new tokens. Valid only if the last non-empty line
  has that exact form and the code is allowed.

The prompted adapters emit a discrete selected label only. They do **not**
produce calibrated confidence, native `noul` probability or ordinal expected
score; comparisons are restricted to exact-label accuracy and decision turnover.
All malformed, unparsed, out-of-set and unfinished outputs are retained as
invalid and count as incorrect. No retry, self-consistency, prompt-tuning or
post-hoc rescue is permitted. A runtime exception ends the run with the prior
raw rows intact, rather than imputing an answer.

## Analysis and limits

Compare each condition against the historical candidate-logit decision on the
*identical requests* via paired accuracy difference, correction and regression
counts, prediction disagreement and invalid output rate. Report suite-level
and 15-source summaries. A 10,000-draw stratified paired bootstrap resamples
cases within each suite; its interval describes finite sample sensitivity,
not dataset curation or model-training uncertainty. For the source-balanced
macro effect, first average suites within source and then sources equally.
Report exact numerator/denominator and no significance claim for small domains.

Record raw decoded text, token counts, hashes, parser result, invalid reason,
per-batch inference time, model file hashes and environment. GPU wall time and
token budgets describe compute under this implementation; they are not
equal-cost matched and are not directly comparable to hosted API latency.
