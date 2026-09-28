# Local LLM comparison protocol

These are **System1Bench's own runs**, not scores imported from model cards or
third-party leaderboards. Local Qwen3-8B and Llama-3.1-8B-Instruct checkpoints
are identified by pre-inference SHA256 for every weight shard and the recorded JSON/Jinja
configuration and tokenizer files. A separate post-launch [upstream file verification](LOCAL_CHECKPOINT_VERIFICATION.json)
compares those hashes to Hugging Face LFS SHA256 and small-file Git blob hashes:

| Local model | Matching upstream revision | Coverage |
|---|---|---|
| Qwen3-8B | `b968826d9c46dd6066d109eabc6255188de91218` | All pre-inference recorded files match; `merges.txt` also matched in a separate post-launch check |
| Llama-3.1-8B-Instruct | `0e9e39f249a16976918f6564b8830bc894c89659` | All weights, HF configs and tokenizer files match; extra local `configuration.json` has no upstream counterpart |

The extra 48-byte Llama `configuration.json` only declares framework/task and
is not loaded by Transformers. Qwen also has a `merges.txt` file omitted from the pre-run hash selection. It is
verified separately after launch and explicitly marked as such. The native fast
tokenizer loads the hashed `tokenizer.json`; per-request token hashes additionally
bind the actual encoded prompts. This inventory distinction is preserved.

Original pre-run metadata retains its
`local_snapshot_identified_by_file_hashes` provenance; it was not rewritten to
pretend this later upstream verification preceded inference. Model weights
are not redistributed. Earlier Laya outputs and their historical code hashes
are preserved unchanged.

## Frozen before the measured runs

- Same `data/frozen.json` as Laya (SHA256
  `5baf87ce9010d8229ea1a39722b865fb5ecc20db3c981e97f51a4baae3653be4`).
- All 36 suites, 22,934 logical state requests / 26,450 decisions per model.
- Zero-shot, no demonstrations, no test-label prompt selection or fine-tuning.
- BF16, PyTorch SDPA, seed 0, evaluation mode, batch size 8 on one A100 80GB per
  model; the model metadata records exact library versions.
- Mechanics pilots checked loading, single-token codes, finite distributions
  and choice/score decoding. They were not used to select a prompt by accuracy.

## Conversion to a direct decision

Each question is evaluated separately. The chat prompt contains a fixed system
instruction and a JSON user message with the unchanged state, original question
instructions, primitive type and all candidate labels/descriptions. Source
reference labels, rationales and metadata never enter the prompt. Boolean
questions retain their supplied false/true criteria (generic meanings are used
only when criteria are absent); ordinal questions keep their zero-based
scale and descriptions. Language content is preserved; the wrapper is English.

Candidates receive a fixed ordered sequence of codes (`A`, `B`, ..., `FD`, with
unsupported codes omitted) that are each one token in **both** tokenizers.
The full 151-code list and token IDs are in metadata and the adapter. The native
chat template opens the assistant turn. Qwen uses `enable_thinking=False`;
Llama uses its native instruct template. Qwen's nonthinking chat template inserts
a fixed empty `<think>\n\n</think>\n\n` block at the start of the assistant turn;
this is template text, not generated reasoning. The adapter adds no further
assistant answer prefill. There is no free text generation, generated chain of
thought or sampling. One forward pass gives the
next-token logits. Argmax over the valid codes selects the answer.

Probabilities use stable float64 `softmax(candidate_logits)`. The expected
ordinal index uses a normalized weighted sum with only floating-point boundary
roundoff clamped to its valid range. This is a **conditional distribution over allowed answer
codes**, not full-vocabulary output probability and not calibrated confidence.
Raw candidate logits are retained. Boolean output is P(true); score output also
records the expected index, but classification accuracy uses the modal index.
This conversion enables Brier/ECE/OOS diagnostics but does not make confidence
semantics identical to Laya's trained decision heads. Code priors and prompt
choice can influence results, especially for 151-way classification. The order
controls reassign codes with the reversed candidates; they therefore probe
combined candidate-position/code sensitivity.

## Full inputs and timing

No input is truncated. The LLM context ceiling is 32,768 tokens (bounded by the
checkpoint's native context); Laya uses its existing 8,192 / 4,096 input/head
limits. Token counts differ across tokenizers, so fairness here means the same
full semantic request, not an identical token count. Each actual prompt token
sequence is hashed and counted. Requests beyond the ceiling fail rather than
silently shorten inputs, and errors remain in the denominator. The runner catches
prediction exceptions at batch granularity: one invalid/over-limit request can
fail the entire batch. Complete-input counts do not alone imply successful
inference; failure counts are reported separately. The report shows
shared complete-input coverage across every model.

Batch timing includes the adapter's predict call and GPU synchronization, but
excludes model loading and the separately executed input audit. LLM prompts
are tokenized during that audit and cached for predict. A multi-question state
requires multiple LLM forwards. These timings describe this implementation on
a shared machine, not controlled serving latency or equal-compute comparisons.

## Reproduce with locally available, licensed checkpoints

```bash
pip install -e '.[llm]'
CUDA_VISIBLE_DEVICES=0 python -m system1bench.run \
  --adapter system1bench.llm_adapter:LLMAdapter --model qwen3_8b \
  --checkpoint /path/to/Qwen3-8B --batch-size 8 --output my-results
CUDA_VISIBLE_DEVICES=1 python -m system1bench.run \
  --adapter system1bench.llm_adapter:LLMAdapter --model llama31_8b_instruct \
  --checkpoint /path/to/Llama-3.1-8B-Instruct --batch-size 8 --output my-results
python -m system1bench.metrics --results my-results
python -m system1bench.report --results my-results
```

This evaluates a fixed direct-decision baseline. It does not establish either
LLM's best achievable performance with deliberation, demonstrations, alternate
prompts or task-specific tuning. Jev has not been run.
