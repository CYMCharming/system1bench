# Transparent corrective amendment before matched-batch rerun

Recorded 2026-09-29 16:57 UTC, after the initial batch-eight pilot and its
first summary, but **before** the matched-batch inference below. This is not
retrospectively described as part of the original preregistration.

Independent QA found that `research/domain_expansion_v1` ran ContractNLI at
batch size **four**, while `PROTOCOL.md` and `run.py` erroneously specified
eight. Although base/both prompt token hashes, model files, chat template and
adapter code matched, padding/batch shape did not. The original batch-eight
new-mode results and first `summary_batch8.json` are retained, unmodified, as
a pilot sensitivity. The corrected runner uses four, retains the identical
144 cases, four frozen prompts/code assignments, model settings and reference
outputs, and writes to the separate `results_batch4/` directory. No GPU
output is overwritten. The corrected two-mode inference is run once for each
model. Any subsequent deviations must be separately documented.

QA also found that the historical `both` run's reversed `question.criteria`
order changes the native decoder's first-maximum tie-break. This matters
for exact BF16 top-logit ties. The **native recorded predictions** remain
the primary record for continuity with the original domain expansion;
they must not be silently rewritten. A clearly labeled, post-hoc
**canonical semantic tie-break sensitivity** recomputes all four predictions
from their stored full-precision semantic probabilities using fixed class
order Entailment, Contradiction, NotMentioned. It does not require extra
inference and can be independently verified from stored logits where
available. The 2×2 factor contrast is interpretable as an adapter-prompt
diagnostic only with the common tie convention; raw historical flips mix
prompt/code effects with the decoder convention. Report top-tie counts,
native-vs-canonical changed predictions, four-cell accuracy, paired flips,
and document-cluster bootstrap intervals for both views. Report batch-eight
vs batch-four differences as a sensitivity, not as replicated trials.

The source text is never copied into this directory; the existing frozen
source is referenced by IDs and SHA-256. All raw outputs and errors are
retained. This remains a diagnostic of two pinned model-plus-adapter systems,
not a general claim about LLM reasoning or ContractNLI in the wild.
