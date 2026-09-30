# Measured model-expansion addendum

This file records new results for integration into a subsequent manuscript
revision. It does not silently replace or relabel the previously published PDF
drafts, which predate this five-model expansion.

We added official pinned Kev-0.8B/4B/9B, the unified-games NanoJev checkpoint,
and post-trained Qwen3.5-9B. Each produced 4,905 complete-input decisions across
three separately interpreted reference tracks: executable policy, ContractNLI
source annotations, and cited SciFact evidence pairs (including derived NOINFO).
All 24,525 outputs were valid. We further measured 6,912 new decisions from
Kev-4B/9B on state-disjoint policy replication pairs. Neither count represents
independent questions, and the new systems have not yet completed the historical
15-source matrix. Qwen uses constrained next-token code likelihood, thinking off;
these are direct-decision comparisons, not an LLM reasoning ceiling.

The primary methodological story is that reliability has two requirements:
preserve a correct decision under meaning-preserving changes, and correctly
update it under a decisive factual change. Stability alone can reward rigidity:
NanoJev had no scientific reversal flips, yet 213/339 pairs were wrong in both
conditions. Its game-specialized training bounds this transfer finding.
The sample scientific ranking also changes: Qwen3.5/ Kev-4B have 283/339 versus
274/339 base agreements but 250/339 versus 265/339 correct-and-stable pairs.
The paired pointwise intervals do not establish secure general superiority
(base difference +2.65 pp, CI [−0.92, +6.43]; joint difference −4.42 pp,
CI [−8.93, 0.00], Qwen minus Kev).

Release upgrades can differ across workflows. In the prospective, post-discovery
new-seed study, refund counterfactual joint success increases 82/96 → 96/96
from Kev-4B to Kev-9B, whereas routing decreases 68/96 → 56/96. Routing's
pointwise interval is [−21.88, −3.13] pp, but the six-effect nominal 99.1667%
guard reaches zero: [−26.04, 0.00]. We retain all six primary effects, including
null/contrary results. These approximate bootstrap intervals and release-specific
shifts are not an architectural size law: training histories differ and rule
grammar remains familiar. A supplementary, exploratory head-correctness audit
finds 25/96 (discovery) and 30/96 (replication) Kev-9B routing states whose
severity label is correct but action is wrong; this cannot identify internal
knowledge or intention.

Use the four new reproducible PDF/SVG figures under `paper/figures/`:
`fig_model_expansion_accuracy`, `fig_model_expansion_stability`,
`fig_model_expansion_scale`, and `fig_model_expansion_replication`.
Every plotted value comes from hash-bound raw outputs and independent integer
replay; complete source-input reconstruction was verified on the research host.
Public CI replays publishable artifacts only. Full methods, limitations,
probability semantics, class-level metrics and historical-source receipts are
in the expansion and replication study directories.

The proposed manuscript framing is **"Reliable decisions must know when to
stay and when to switch"**. Novelty, natural-data validity, strong reasoning
baselines and prospective constrained-routing benefit remain open empirical
requirements, not achievements implied by these measurements.
