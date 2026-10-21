# Option-description length diagnostics v1

This is a **post-hoc observational audit**, not a new model evaluation or a
causal test of verbosity preference. It does not change published accuracy,
composite scores, model weights, prompts, or inference settings.

## Population and source reconstruction

23 models, the same nine original classification tasks as the seven-domain
common suite: 1,299 original requests/model. Excludes full intent recognition,
counterfactual policy facts, repeated executions and auxiliary policy heads.
Another 1,011 same-content order reversals provide a separate paired check;
they never double the main sample size. Frozen inputs are SHA-bound to the
published main and transfer manifests. Each prediction is joined by suite,
case ID, head, full request SHA-256, gold and ordered candidate IDs. Original
correct/n cells for all 23 x 9 tasks must exactly match common-suite scores.

`collect.py` retains only candidate lengths, exact-description hashes, choices,
source clusters, IDs and request hashes in `observations.json.gz`. No source
questions, states or candidate text are published. `bindings.json` records all
source receipts. Existing textual journals are hashed after CRLF -> LF, as in
the Linux producer; compressed files use exact bytes. Collector output gzip
has mtime=0 and an empty filename for cross-platform determinism.

Jev has three failed original transfer requests. A failed selection is missing,
not a neutral score or an incorrect candidate. The default `variable` plots
restrict every model to the same successful requests: 221 informative questions
(256 original code/tool questions minus 34 all-equal lengths and one remaining
failed request). `variable_available` retains model-specific successful coverage;
`shared_variable` is an explicit alias of the default cohort. Individual task
and all-nine-task views disclose their own valid n. Ranking
accuracy retains its original treatment and is not redefined here.

## Main view and interpretation

Only CRUXEval and When2Call have candidate contents varying across questions.
The other seven tasks use fixed candidate labels: length is tied to semantic
class (e.g. science's evidence label). Default plots therefore use the two
variable-description tasks and exclude all-equal lengths. Even in these tasks,
different semantic answers differ in length: **the displayed correlation does
not establish that making the same meaning longer would cause its selection**.

Primary length = count of Unicode characters excluding whitespace, candidate
description only, without candidate IDs or question/state text. Length ranks
handle different K and ties:

    r(j) = (# strictly shorter + .5 * # equally long other candidates)/(K-1)
    length position score = 200 * mean(r(chosen)) - 100

Uniformly choosing from all candidates gives expectation zero. This is an
ordinal score on [-100,+100], **not a percentage, accuracy, fairness score or
ability ranking**. Correct answers' scores and longest/shortest rates are
shown alongside model choices. A perfect model need not score zero. Aggregate
views pool eligible questions (micro averages), not task/domain-equal averages.

Longest/shortest rates include ties. Their chance baselines are calculated
per question as number of extreme candidates / K, never assumed to be 25%.
The four-option/unique-shortest slice does not require the other three options
to be equal. It is not an exact test of the proverb 'three equally long and
one short'. Zero eligible cases produce null, not 0% preference.

## Errors and uncertainty

The errors-only filter is descriptive. Different models fail on different
questions; mistakes do not identify a common independently defined difficulty
stratum or a model's internal uncertainty. The plotted score still uses all
candidate length ranks. Its reference tick and extreme-rate baselines instead
sample uniformly among WRONG candidates in that question. Also publish a
wrong-option-only length-rank score, only where at least two wrong candidates
have different lengths. Binary choices and all-equal wrong candidates have no
identification power and are excluded from this additional score (null if none).

95% percentile intervals use 2,000 source-group bootstrap resamples stratified
by task (seed 20261021). Cases from the same source `group` stay together.
Intervals reflect question sampling only, not training history, prompt choice,
the model population or architecture. A single source cluster gets no interval.
Do not use overlapping per-model intervals as a significance test of a paired
model difference. No model-family significance claim or causal comparison is
made. Source-group dependence beyond recorded groups remains a limitation.

The same-content reversal diagnostic matches exact candidate hashes and gold
meaning; it measures semantic-choice retention and length-score change. It can
reveal position sensitivity but **does not remove semantic confounding**.
Whitespace-word sensitivity uses only the common character-and-word-informative
cohort. These are word counts, not tokens; no common tokenizer analysis is
claimed. Short fixed labels especially depend on the length definition.

General LLM baselines choose a constrained single-token candidate code without
CoT, not the summed probability of the candidate description. Therefore a
short-choice skew cannot be attributed directly to a long-answer likelihood
product penalty in this implementation. Laya is a representation baseline,
shown separately from S1 and general LLMs; its full-option text adaptation and
StartLux's declared ContractNLI training exposure remain relevant.

## Reproduction and further experiment

    python research/option_length_v1/collect.py  # needs private frozen source text
    python research/option_length_v1/analyze.py # public text-free replay only
    python research/option_length_v1/analyze.py --check

The next causal-adjacent test should hold the question, facts, gold and candidate
meanings fixed, counterbalance position and which candidate gets expanded, and
compare redundant expansion of correct vs wrong choices. Freeze an independent
semantic-equivalence review before inference. Repeating content also changes
emphasis; call it redundant-expansion sensitivity rather than isolated pure
length causality. No such intervention is reported as completed in v1.

Related primary research (precedents, **not evidence about these 23 models**):
[Stress Testing Generalization (2025 preprint)](https://arxiv.org/html/2502.12459v1)
manipulates correct/wrong option lengths;
[Verbosity Bias in Preference Labeling (2023)](https://arxiv.org/html/2310.10076v1)
separates observed longer-choice rates from quality-confounded preference
(preference judging is not objective multiple-choice answering).
