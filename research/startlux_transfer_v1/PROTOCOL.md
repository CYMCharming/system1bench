# Decision transfer panel v1 — frozen before inference

This is a focused, text-only transfer study, not a reproduction of Decision Index
or its vendor-reported scores. Historical 4,905-decision results stay immutable.
Four new checkpoints run that same original panel: StartLux-Decision-4B/9B/27B
and Intern-Decision-4B. Official native adapters, BF16, no generation, no thinking,
one request per batch, complete inputs, 32,768-token limit, no truncation.
Shared GPUs and slow-kernel fallbacks prohibit controlled latency claims.

## New sources and task definitions

* CLadder: 144 source questions, 24 per causal rung × yes/no cell. Background,
  given information and question only; never reasoning or latent model parameters.
  Cluster on source causal model. Three rungs are association, intervention and
  counterfactual. Labels use the published generator, not independent rederivation.
* CRUXEval: 128 output-choice cases with at least one distinct, parseable, published
  incorrect CodeLlama generation as distractor. Never execute source code; parse
  Python literals only. Up to 10 candidate outputs; exclude equivalent literals.
  This is NOT free-generation CRUXEval-O/pass@1; distractor availability conditions
  the sample on a historical model's mistakes. Report candidate counts/chance.
* FinEntity: 128 supplied-span entity sentiment cases (43 negative,42 neutral,
  43 positive), at most one selected entity per document. Validate span offsets
  and duplicate/conflicting labels before selection. This is classification,
  not entity extraction. Full published corpus, NOT a claimed held-out test split.
* When2Call: 128 official test MCQs (43 tool_call,43 cannot_answer,42 request_for_info),
  at most one per upstream source problem (strip generated suffix after '-').
  Four response candidates, THREE observed gold classes. Direct has no positives;
  report its false-selection rate, not direct recall. Inputs expose available
  tools and user question, never original tools, target tools or mutation metadata.
* Intern known-distribution pilot: all 96 cases,48 paired source settings. Use exact
  reference fractions checked to sum to one. Proper metrics: excess Brier sum(p-q)^2,
  expected Brier 1+sum(p²)-2sum(pq), total variation, impossible-outcome probability
  mass. No stochastic realization/argmax accuracy; no temperature fit on test data.

All four classification sources have independently seeded opaque option-ID
assignments (no fixed gold ID), a seeded shuffled candidate ordering and a
semantic-key-preserving reversed ordering: 528 originals +528 reversals. Pilot
adds96: 1,152 new decisions/model. Reversal is a robustness perturbation, not an
independent sample. Exclusions and source hashes must be recorded before inference.
Seed20261004. Deterministic hash-priority selection within each quota.

## Fixed representative cohort

The new panel includes StartLux4/9/27,Intern4,Kev0.8/4/9/27,Qwen3.5-0.8/4/9,
Qwen3.8-27 and Jev API (13 models). This cohort is chosen before results, contains
size-matched families and intentionally excludes older historical baselines and
NanoJev's different toy-task training distribution. No result-dependent selection.
Four new checkpoints also receive the unchanged main panel. Main overall index
and new transfer/pilot metrics remain separate; no mixing incomparable coverage.

## Inference and calibration

StartLux uses pinned official native per-type temperature and renderer; graphs,
images and prefix caching off. If fused kernels unavailable, the official
STARTLUX_ALLOW_SLOW=1 fallback is disclosed; accuracy only. Intern uses official
HF backend and the released 4B temperature1.9924182353655278 (fit on a separate
upstream calibration split using XTuner). Verify all preset checkpoint hashes
before rebinding its local path; disclose HF/XTuner backend difference. Native
noul yes/no labels are mapped to our true/false semantics. Other model interfaces
remain identical to the previous benchmark. Gold/metadata are never in requests.
Errors remain in denominators; invalid distributions are not silently dropped.
Hosted probabilities can be rounded to two decimals: use the historical hosted
client's 0.02 unit-mass tolerance, normalize validated probabilities, and retain
both reported and normalized values. Malformed distributions remain errors.
Hosted task accuracy uses the validated official reported choice, including
rounded-probability ties; separately retain our distribution-argmax prediction.
Rounded ties must not manufacture an apparent option-order sensitivity.
This hosted-format amendment does not alter any native model inputs or scores;
all final hosted cases are rerun, never replaced by selected diagnostic retries.
Partial runs cannot enter final ranking. Raw results bind input/code/model hashes.

## Statistics, contamination and claims

Report source/domain/class/rung panels, original and paired-both-correct rates,
cluster bootstrap95% intervals (seed20261004,2,000 draws), and sample denominators.
Pilot uncertainty is clustered by paired setting. No causal claim about architecture
from heterogeneous checkpoints/training. StartLux declares training on14 Decision
Index train splits, including ContractNLI in our old panel; visibly flag this known
overlap. New four sources are not in that declared list, but that is NOT proof of
clean pretraining or held-out evaluation. Intern pilot is vendor-supplied diagnostic
data, not an independent large calibration benchmark. Do not claim saturation,
general domain superiority or native end-to-end agent competence from these samples.
