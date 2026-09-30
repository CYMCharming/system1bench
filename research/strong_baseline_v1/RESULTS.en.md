# Frozen cross-domain prompted-baseline stress test

This is a paired challenge on a **selected subset**, not an estimate of
population-wide mean accuracy or either model's best prompted performance.
The input file was frozen before inference: 212 states, one prespecified
question each, 18 suites and 15 source collections. Each model generated 424
responses (212 direct and 212 deliberative). The historical code-logit output
was matched by request hash and reference label on every case. Original
checkpoint file and chat-template hashes matched before inference. All 848
new generations completed without runtime failure or context truncation.

| Model | Condition | Correct / 212 | Difference vs. code-logit | Fix / break | Invalid | 95% paired CI for difference |
|---|---|---:|---:|---:|---:|---:|
| Llama-3.1-8B-Instruct | historical code-logit | 133 | reference | — | original run | — |
| Llama-3.1-8B-Instruct | direct generation | 134 | +0.5 pp | 2 / 1 | 0 | [−0.9, +1.9] pp |
| Llama-3.1-8B-Instruct | brief deliberation | 145 | +5.7 pp | 25 / 13 | 3 | [+0.5, +10.8] pp |
| Qwen3-8B | historical code-logit | 158 | reference | — | original run | — |
| Qwen3-8B | direct generation | 158 | 0.0 pp | 0 / 0 | 0 | [0.0, 0.0] pp |
| Qwen3-8B | brief deliberation | 153 | −2.4 pp | 12 / 17 | 10 | [−7.1, +2.4] pp |

Intervals use 10,000 suite-stratified paired case resamples. The overall
Llama gain under brief deliberation is fragile to how sources are weighted:
the equal-source macro difference is +4.7 pp, with interval [−1.4, +10.6].
The analogous Qwen macro difference is −1.1 pp [−6.1, +3.9]. An additional
post-hoc dependence sensitivity that block-resamples
within source-group IDs gives [−1.1, +10.6] and [−6.3, +4.0] respectively.
These intervals exclude between-dataset curation, reference noise and model
training variability. Source cells have only 8–24 sampled states and are
descriptive, not separate hypothesis tests.

Source heterogeneity is substantial. Llama gains 4/12 on English XNLI but
loses 1/12 on Chinese XNLI, yielding +3/24 over XNLI. Qwen gains 4/12 on
Banking77 yet loses 4/12 on BoolQ under strict output parsing; all four
BoolQ losses are parser failures. Qwen also loses 4/24 across XNLI. These
patterns rule out a single "reasoning helps" or "reasoning hurts" summary.

## Invalids and explicitly post-hoc parser sensitivity

The prespecified grammar requires direct outputs to consist solely of one
candidate code; deliberative outputs must end with a *standalone* `FINAL:
<CODE>` line. All invalids count incorrect. Llama's three invalids reached
the 128-token cap without a final code (two long JevBench policy cases and one
MASSIVE Chinese case). Qwen's ten invalids were unparseable under the standalone
line rule. Eight of them end instead with a code in an inline `FINAL: <CODE>`;
two have `FINAL: None`. A **post-hoc** permissive end-of-response parser recovers
eight Qwen answers, six of which are correct, giving 159/212 correct. This
would be +0.5 pp against Qwen's original 158/212, but is *not* the primary
registered result and must never overwrite the raw rows. The divergence
shows that output-format reliability and answer quality are separate axes.

## Compute and interpretation

With batch size four on a single A100 80GB (physical GPU 2), direct generation
used 15.7 s for Llama and 16.9 s for Qwen, versus 87.6 s and 90.1 s for brief
deliberation. These are synchronized model-generate times, excluding checkpoint
loading and prompt tokenization. Completion tokens were 424/424 for direct and
9,246/8,912 for deliberation (Llama/Qwen). The deliberate condition therefore
used about 5.6×/5.3× the measured generation time of the corresponding direct
condition in this run. These local timings are not comparable to the separate
historical performance contract or a hosted API's end-to-end latency.

The deliberate condition is one frozen zero-shot prompt, greedy decoding and
128 output tokens. It is a stronger challenge to the one-token logit baseline,
not a search over exemplars, self-consistency, long chain of thought or
task-specific prompts. The generated adapter does not output typed confidence
or ordinal expectation; this experiment supports accuracy/turnover claims only.
Reference types remain mixed as documented in the cross-domain atlas.

## Reproduce

Inputs and fingerprints: `frozen.json`, `manifest.json`, `PROTOCOL.md`.
Raw text/failures: `results/{model}/raw.jsonl` and `metadata.json`.
Analyses: `summary.json`, `posthoc_parse_sensitivity.json`.
Code: `freeze.py`, `analyze.py`, `verify_raw.py`, `posthoc_parse_sensitivity.py`,
`../../benchmarks/strong_baseline.py`,
`../../paper/figures/gen_strong_baseline.py`.
