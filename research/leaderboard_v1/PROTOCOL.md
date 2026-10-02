# Ten-model descriptive leaderboard, version 1

This leaderboard was requested after all ten model outputs were available. It
is a descriptive presentation, not a pre-registered hypothesis test, a new
inference run, or the canonical score for the historical 15-source benchmark.

Population: the identical 4,905 case × question × condition decisions per
model in `model_expansion_v1` and `historical_context.json`. The older five
models are reused from their original, individually hash-bound run files;
the five new models use their published raw files. Require the same set of
suite/case/question IDs, gold labels and request hashes for all ten. No model
may gain a rank by silently omitting an unavailable case. The extra 3,456
new-seed policy decisions per Kev-4B/9B are separate, since other models have
not seen those states.

Primary descriptive index (0–100): policy action = mean of refund/access/routing
base correctness (96 cases each). Legal = 144 base ContractNLI source-label
agreements. Science = 339 base cited SciFact agreements. Overall = the simple
mean of these three domain values. This is **equal-domain weighting**, one
third each. The scientific NOINFO class is derived from absence of annotated
evidence, not independently human-adjudicated. The two natural reference
tracks do not have the same validity as executable policy correctness. Thus
the overall index is a transparent navigation device, not a scalar measure of
model intelligence, safety or deployment suitability. Equal weighting of the
five task columns is reported as a sensitivity check for every model. The
weights were chosen for this post-result presentation and were not preregistered
before model evaluation.

Publish ALL models in every relevant specialized leaderboard: three domains,
three individual policies, three output primitives averaged equally over the
three policies, two metamorphic endpoints, and all-three-head policy success.
Natural reversal robustness is the mean of legal and science fractions correct
on BOTH base and reversed forms, using all original pairs as denominator.
Policy factual response is the mean across three policy families of pairs with
both original and decisive one-fact counterfactual actions correct, again all
original pairs as denominator. Pairwise answer-change percentages are NOT
substitutes for either correctness metric. Primitive-head scores use all 288
base states (96/family). Policy all-head success requires action, review and
severity all correct on a base state. Rank equal scores equally: rank = 1 +
number of strictly better models. No leaderboard uses latency, confidence or
raw probability, because execution and probability semantics differ.

Pointwise 95% descriptive percentile intervals for the primary index use
5,000 paired bootstrap draws, seed 20261002. Resample each policy family by
base state; legal by document; science by claim. A cluster draw keeps all its
cases and every model together, so differences remain paired. Recompute the
equal-domain index in each draw. These intervals do not account for reference
validity, selection, model training histories, multiple leaderboard searches or
unseen deployment domains. Do not call overlapping intervals ties or separated
intervals a familywise significance proof.

The native Jev, Kev, Laya and NanoJev and direct next-token LLM interfaces
receive equivalent supplied information, not identical token strings. Qwen
thinking is off; no generative reasoning ceiling is established. NanoJev is a
game-specialized release, making these out-of-domain results especially
limited. Hosted Jev tokenization is not independently verified. There is no
controlled cross-model speed claim.

Published SHA-256 receipts for text inputs and outputs use UTF-8 bytes with
CRLF line endings normalized to LF. Binary inputs and figures use raw bytes.
This permits a Windows checkout with Git automatic line-ending conversion to
verify the same published content as the Linux research host.
