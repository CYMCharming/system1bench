# Laya full-option-text transfer supplement

Predeclared before supplementary inference on 2026-10-09. Uses exactly the
same frozen transfer requests, labels, ordering, global input budgets (8192 /
4096), floating-point tensors and native model as completion v1.

The upstream encoder unconditionally limits each individual option description
to 48 tokens, even when the complete request fits its global window. The v1
strict audit rejected 106 English transfer requests; multilingual also failed.
Those inputs were not scored with silently shortened options.

This explicitly named input adaptation removes only that per-description token
cutoff, leaving the rest of the native formatter untouched. Model weights,
ontology, question text, source state, option order, and global budgets are
unchanged. The full token audit must pass on every request before inference.
This is not claimed to be an unchanged native interface or an upstream official
benchmark reproduction. Option-count limitations of StartLux/Intern are not
changed and remain excluded from the comprehensive ranking.

The already completed CLINC/BANKING runs are reused: their complete audits show
all descriptions were preserved even under the 48-token rule. Every recorded
tensor hash must match the historical model. Current upstream temperature
validation and runtime source hashes are recorded, not treated as correctness
confidence calibration. Probability and latency are separate from accuracy.

The parent completion-v1 weighting, failure denominator, complete-case admission,
data-source caveats and source provenance rules apply unchanged. This supplement
has its own code/manifest bindings and output directory; no failed v1 journal or
historical result is overwritten.
