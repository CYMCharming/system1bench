# Complete-cohort classification ranking, v1

Frozen on 2026-10-09 before supplementary inference. Scope: the 23 models
already listed in the website, the five original classification tasks, four
transfer classification tasks, and the official full CLINC150/BANKING77 tests.
Existing completed runs are reused without changing inputs, scores or adapters.

## Eligibility and weighting

The default comprehensive ranking requires all eleven classification tasks.
Models whose native interface cannot retain all 151 CLINC / 77 BANKING choices
are excluded, not given zero, and remain visible in historical/per-task tables.
Missing runs are not averaged away. Failed predictions count as incorrect in
the full fixed denominator, but incomplete runs are never ranked.

Eight domains are equally weighted: policy (mean refund/access/routing), legal,
science, causal, code, finance, tools, and intent (mean CLINC/BANKING accuracy).
An eleven-task equal-weight score is also reported. Classification accuracies
only are aggregated. Probability errors, robustness and latency stay separate.
Neither weighted score has a single pooled correct/total denominator.

All evaluations retain the frozen full ontology, source order, instructions,
and gold-free payload. CLINC has 5,500 official test rows (including 1,000 OOS)
and BANKING has 3,080. Historical tasks retain their published frozen subsets;
"complete" means the entire predeclared evaluation matrix, not a claim that
every historical dataset's original census was evaluated. Binary CLINC and
intent pilots are not counted as independent datasets.

Original floating-point weights only; no quantization or test fitting. The
historical Laya 8192/4096 input budgets and Llama candidate-code adapter are
retained. Native decision adapters and pinned calibrations are reused. Single
request inference, no free generation or chain of thought. GPU co-tenancy is
permitted for accuracy runs only; these times do not enter the speed ranking.
Hosted Jev is pinned to jev-1.13.0, with the existing validated reported-choice
semantics and rounded-distribution normalization. Server tokenization cannot
be verified. Bounded retries and a USD 10 accounted-cost limit are retained.

All raw journals are append-only and resumable only under unchanged bindings.
Bindings include source, frozen-input, checkpoint and adapter hashes. Complete
option/input audits precede inference. Independent replay checks unique IDs,
request digests, probability mass, full option sets, and completion hashes.
Public projections omit input text and secrets. Source licenses, training
exposure and exact-overlap caveats from the published audit remain applicable;
test accuracy is not proof of uncontaminated pretraining or architecture causality.
