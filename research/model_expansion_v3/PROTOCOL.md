# Original-weight family expansion v3

This is an additive, frozen-input comparison, not an update to earlier model
scores. Each admitted model receives the same 4,905 main-panel decisions and
1,152 transfer-panel decisions as the published v3/transfer-v1 panels. Labels,
candidate meanings, option-order interventions, task groups and scoring are
unchanged. No prompts, temperature or model selection are tuned on test results.

## Models and provenance

- Intern-Decision 0.8B and 2B: official checkpoint and native HF inference,
  upstream published temperatures with checkpoint-hash verification. Those
  temperatures were fitted upstream with XTuner, not fitted here with HF.
- Llama 3.2 1B/3B Instruct: public `unsloth` community distributions, NOT
  Unsloth quantized variants and NOT claimed byte-identical to Meta's gated
  releases without independent verification. Full floating-point weights are
  verified against the pinned distributing repository. Redistribution provenance
  and the Llama license are disclosed, not hidden behind an official-source label.
- Qwen3 1.7B/8B: prefer existing local original weights. A directory name,
  BF16 storage or absence of a quantization config alone does not prove an
  untouched model. Verify every weight shard against the pinned official HF LFS
  SHA-256 before admission. Reject altered, pruned or fake-quantized weights.

General LLMs use the existing zero-shot constrained-candidate next-token prompt
and complete native instruct chat template, with no chain-of-thought generation.
All 151 candidate codes must be distinct single tokens. These probabilities are
conditional candidate-code likelihoods, not calibrated probabilities of being
correct. Models without an instruct chat template are not silently treated as
instruct models. No quantization, pruning or fine-tuning is performed.

Each run is bound to the checkpoint files, tokenizer, protocol, adapter,
unchanged evaluator code and frozen input hash. All failures remain in the
denominator. Incomplete runs do not enter a ranking. Shared-server quality-run
timings are NOT speed-ranking results. Speed requires its own predeclared
workload, cold input preparation, synchronization and hardware conditions.

Existing historical scores remain immutable. New domains and the exact-probability
diagnostic stay separate from the main composite; no invented overall metric
combines quality, speed and probability loss.
