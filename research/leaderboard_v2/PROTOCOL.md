# Fourteen-model descriptive leaderboard, version 2

This extends the immutable ten-model leaderboard with Kev-27B v2 and three
official open-weight Qwen checkpoints. It is a post-result descriptive
presentation, not a pre-registered hypothesis test or the canonical score for
the historical 15-source benchmark. Version 1 remains unchanged.

Population: exactly 4,905 case × question × condition decisions per model,
covering 2,601 requests. The first ten model runs are reused; four new models
use the independently frozen `model_expansion_v2` protocol and weights pinned
to exact Hugging Face revisions. Require the same suite/case/question IDs,
gold labels, and request hashes across all fourteen. An unavailable answer is
not silently dropped. New-seed Kev-4B/9B replication is excluded because the
other models did not run those states.

Primary descriptive index (0–100): policy action = mean of refund, access and
routing original-condition accuracy (96 states each); legal = 144 ContractNLI
source-label agreements; science = 339 cited SciFact agreements. Overall =
the mean of these three domain values, one third each. Science NOINFO is
derived from absence of annotated evidence, not independently adjudicated.
The two natural-reference tracks are not as strong a correctness standard as
the executable policies. The index is a transparent navigation device, not
a scalar of intelligence, safety, or deployment suitability. A five-task
equal-weight index is included as a weight-sensitivity check. These weights
were not preregistered before evaluation.

Publish all models for the domain, task, decision-head, all-three-head, and
metamorphic sub-rankings. Natural reversal robustness is the mean of legal
and science fractions correct on both the original and reversed forms, all
original pairs as denominator. Policy factual response is the fraction of
policy states with both original and decisive one-fact counterfactual actions
correct. Mere answer change is not a correctness measure. Rank exact ties
equally. No leaderboard incorporates latency, confidence, or raw probability.

Pointwise 95% descriptive percentile intervals for the primary index use
5,000 paired cluster-bootstrap draws, seed 20261002. Resampling units are
policy state, legal document, and scientific claim. Each draw keeps all models
together. Intervals do not capture reference validity, training histories,
multiple searches, or unobserved deployment domains.

Same-size contrasts report percentage-point differences, Kev minus Qwen, on
the exact same requests. Kev-0.8/4/9B are compared with Qwen3.5 counterparts;
Kev-27B v2 is compared with Qwen3.8-27B. The 9B Kev is an earlier pinned
release; Kev-27B v2 starts from an already post-trained Qwen3.8 base, whereas
the smaller Kev bases are Qwen3.5-Base. None is a controlled causal estimate
of scale or architecture. Qwen uses a direct next-token candidate-code
interface with thinking off; generative reasoning ceilings are unmeasured.
Native Jev, Kev, Laya and NanoJev interfaces receive equivalent supplied
information but not identical token strings. Hosted Jev tokenization is not
independently verified. NanoJev is game-specialized.

Published SHA-256 receipts for text use UTF-8 bytes with CRLF normalized to
LF. Binary inputs and figures use raw bytes. This permits verification from
Windows checkouts with automatic line-ending conversion.
