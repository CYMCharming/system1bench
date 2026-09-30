# Natural-domain strict direct-generation control v1

This is a pre-inference, model-blind control for the **fixed Llama 3.1 8B
Instruct and Qwen3 8B model-plus-adapter systems**. It compares historical
one-forward-pass candidate-code logits with greedy direct code generation
using exactly the historical adapter messages. It does not search prompts,
sample multiple completions, evaluate deliberation, or claim to measure each
model's best prompted performance.

## Frozen input and output rules

Use every base case in the two independently frozen natural-domain suites:
144 ContractNLI document--hypothesis pairs from
`research/domain_expansion_v1/contractnli_base`, and 180 SciFact three-class
claim--cited-abstract pairs from `research/scifact3_v1/scifact3_base`.
The source files and old base outputs are SHA-256-pinned. Their source texts
are *not* copied into this companion freeze: it records IDs, domain/source
cluster, reference label, request/question/message hashes and candidate
code/label order only. No result-dependent filtering occurs.

For both models, use the existing pinned checkpoint, tokenizer/chat template
and `llm_adapter.messages` system/user prompt, with `enable_thinking=False`.
Audit every actual tokenizer prompt against the historical code-logit
result's saved prompt-token hash and length before inference. Generate
greedily (`do_sample=False`) at BF16/SDPA, batch size 4,
`max_new_tokens=16`, with the tokenizer's EOS and pad IDs. The only accepted
response is the entire decoded completion matching whitespace + one
historical candidate code + whitespace. The strict parser is exactly the
`direct` parser frozen in `benchmarks/strong_baseline.py`; any commentary,
multiple codes, out-of-set code, empty response, incomplete output or runtime
error is invalid and counts incorrect. No rescue parser or prompt adjustment
is allowed. Preserve the raw decoded text, generated token IDs, parse status,
prompt/code hashes, prompt/completion token counts, per-batch time/errors.
Do not reinterpret generated strings as calibrated probabilities.

## Estimands and uncertainty

On the same IDs, report each adapter's correct/total, invalid count, native
code-logit versus strict direct prediction flips, wrong→right corrections,
right→wrong regressions and accuracy delta. Keep legal and science separate;
the classes and selection schemes differ. For legal, resample the 91 source
contracts as paired clusters; for science, resample the 180 claim groups
(one selected cited abstract per claim) as paired clusters. Use 10,000
percentile bootstrap draws with seed 20260930. A two-domain macro effect is
the unweighted mean of the domain effects, with independent within-domain
cluster resampling per draw. These intervals describe the selected,
class-balanced source pairs, not domain prevalence or legal/scientific
deployment. Invalid direct generations are counted as wrong and not dropped.

No long inference begins if any historical source/model/hash/prompt token
audit fails. GPU2 must be idle before each model. The expected 648 direct
generations should take minutes, not more than approximately 15 minutes;
unexpected cost or input mismatch requires a stop and report. Existing source
freezes and code-logit files are never modified. Source-data redistribution
is governed by the upstream notices, not this ID/hash-only companion.
