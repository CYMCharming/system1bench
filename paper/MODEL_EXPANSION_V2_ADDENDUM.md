# Kev-27B and Qwen checkpoint expansion: manuscript addendum

This is a measured-results addendum for a *future* manuscript revision. The
existing `main.tex` and `submission.tex` PDFs predate this experiment and have
not been updated, submitted, or represented as containing these results. The
four new models and the fourteen-model leaderboard are fully documented in
[`model_expansion_v2`](../research/model_expansion_v2/PROTOCOL.md) and
[`leaderboard_v2`](../research/leaderboard_v2/PROTOCOL.md).

## What was actually run

Four pinned open-weight checkpoints were evaluated on the identical frozen
panel: [Kev-27B v2](https://huggingface.co/jaredpalmer/kev-27b),
[Qwen3.8-27B](https://huggingface.co/Qwen/Qwen3.8-27B),
[Qwen3.5-4B](https://huggingface.co/Qwen/Qwen3.5-4B), and
[Qwen3.5-0.8B](https://huggingface.co/Qwen/Qwen3.5-0.8B). Each made 4,905
decisions across 2,601 requests; 19,620 new decisions were parsed and
independently replay-verified. The previous ten model outputs were reused,
not rerun. Exact repository revisions, model files, protocol hashes, and
per-request receipts are in the [manifest](../research/model_expansion_v2/manifest.json)
and [verification report](../research/model_expansion_v2/verification.json).
Neither the licensed natural-source text nor the weights are published here.

## Main findings, in manuscript-ready language

The fourteen-model, three-domain equal-weight *descriptive* index ranks
Kev-27B v2 first at 88.2%, Jev 1.13.0 API second at 82.5%, and Qwen3.8-27B
third at 82.3%. The domain scores explain more than this scalar: Kev-27B v2
gets all 288 original executable-policy actions correct, while Qwen3.8-27B
gets 245/288; their ContractNLI source-label agreements are 116/144 and
112/144; both get 285/339 SciFact cited-pair labels. On the same 288 decisive
one-fact policy transformations, both original and changed actions are correct
for 288/288 Kev-27B v2 and 241/288 Qwen3.8-27B pairs. Policy is a small,
synthetic, rule-grammar-matched panel; the observed 100% is a ceiling on this
panel, not evidence of general policy mastery or deployment readiness.

The **equal-science-score, different-errors** result is a useful design
insight. Of the 339 original scientific evidence pairs, both 27B systems are
correct on 264, only Kev is correct on 21, only Qwen is correct on 21, and
both are wrong on 33. Retrospectively selecting the correct answer whenever
either system has it would reach 306/339 (90.3%), versus 285/339 (84.1%) for
either alone. This is an *oracle upper bound*, not a trained router or measured
ensemble. A real claim would require a selector trained without answer leakage
and evaluated prospectively on independent claims and sources. The same
complementarity is weaker in legal inference (105 both right, 11 Kev-only,
7 Qwen-only, 21 both wrong; 85.4% oracle ceiling).

Keeping a correct answer when the form is benignly changed and revising it
when a decisive fact changes remain distinct reliability tests. Kev-27B v2
has 114/144 legal and 282/339 science original-plus-reordered pairs both
correct; Qwen3.8-27B has 103/144 and 276/339. The two tests have different
populations and references, so they are displayed as separate rankings, not
summed into a new score. Stability of a wrong answer is never counted as
success.

The four same-parameter-count contrasts do **not** support a clean size law.
Kev-0.8B and Kev-4B exceed their Qwen3.5 comparators on each of the three
domain scores, whereas the earlier pinned Kev-9B gains on policy but trails
Qwen3.5-9B on legal and science. Kev-27B v2 starts from an *already
post-trained* Qwen3.8-27B checkpoint, unlike the smaller Kev releases based
on Qwen3.5-Base. Model history and tuning differ; the observed differences
cannot isolate a decision architecture, scaling, or post-training treatment.
For the 27B pair, paired clustered 95% intervals for Kev-minus-Qwen are
+14.6 to +31.2 percentage points on refund action, +0.0 to +7.3 on access,
+11.5 to +27.1 on routing, -2.8 to +8.6 on legal, and -3.6 to +3.7 on science.
These are per-task descriptive intervals without multiple-comparison correction.

## Figures and scoring

The reproducible [overall scorecard](figures/fig_leaderboard_v2_overview.pdf),
[domain rankings](figures/fig_leaderboard_v2_domains.pdf),
[typed-output rankings](figures/fig_leaderboard_v2_heads.pdf),
[robustness rankings](figures/fig_leaderboard_v2_robustness.pdf),
[matched-size contrasts](figures/fig_leaderboard_v2_paired.pdf), and
[error-overlap decomposition](figures/fig_leaderboard_v2_overlap.pdf) are
available as PDF, SVG, and PNG. Exact numerators, denominators, all fourteen
model rankings, and cluster intervals are in the
[score JSON](../research/leaderboard_v2/scores.json) and
[editable CSV](../research/leaderboard_v2/rankings.csv). The primary index
equally weights executable-policy action, ContractNLI source-label agreement,
and SciFact cited-label agreement. The policy component itself equally weights
refund, access, and routing; a five-task equal-weight sensitivity index is
also published. Neither index was preregistered or is a universal notion of
model quality.

The scientific NOINFO reference is derived from absence of source annotation,
not independent human adjudication. Legal and scientific source agreement is
not the same reference strength as programmatically executable policy. Qwen
used a direct candidate-code likelihood interface with thinking disabled;
the results do not establish its generative reasoning ceiling. Hosted Jev's
tokenization cannot be independently inspected. No latency, cost, or
probability calibration is included in the leaderboard. Intervals account for
observed clustering, not these reference, interface, training-history, or
domain-shift uncertainties.
