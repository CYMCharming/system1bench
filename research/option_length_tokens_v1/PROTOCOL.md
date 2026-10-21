# Absolute and relative option-token length diagnostics v1

This is a post-hoc observational extension of `option_length_v1`, not a new
model run, an accuracy leaderboard, or a causal verbosity-preference test.
It reuses the same 23 models' frozen selections. No prompts, model outputs,
weights, accuracy scores or composite rankings are changed.

## Length definition and public receipts

Primary unit: the official `Qwen/Qwen3-8B` reference tokenizer, pinned to the
exact repository revision and tokenizer file SHA-256 recorded in
`token_lengths.json.gz` and `bindings.json`. A separately pinned Llama 3.2
tokenizer distributed by Unsloth is a sensitivity reference, not an assertion
of a directly downloaded Meta artifact. Runtime versions are recorded too.

Each exact candidate description is encoded standalone, with
`add_special_tokens=False`, no truncation, and no candidate ID, question,
state, chat template, or padding. Boundary-dependent tokenization in an actual
concatenated model prompt can differ. These are **reference-token counts**,
not Jev's undisclosed native tokens and not each evaluated model's native
input lengths. Shared reference units make cross-model comparison consistent;
they are not a claim that all models internally see the same segmentation.

The collector verifies the private frozen source manifests, exact description
SHA, and earlier character/word counts before publishing a text-free lookup.
Only 893 candidate hashes and their token counts are exposed. No candidate
body, source question, API credential, or tokenizer authentication is public.
Collection uses existing tokenizer files only; it does not load model weights
or invoke inference. Public replay uses Python and the parent's NumPy-based
bootstrap; no Transformers package, model weights, source text, or API is needed.

## Population and paired comparison

The parent audit has 1,299 original questions across nine classification tasks
and 1,011 order reversals. This extension analyzes originals only; reversals
do not double the sample size. The parent selection/accuracy replay and source
bindings remain authoritative and unchanged.

The default `variable` scope uses CRUXEval and When2Call: these have varying
candidate descriptions, unlike the other seven tasks' fixed semantic labels.
For each reference tokenizer separately, every model is restricted to the
same questions with valid outputs from all 23 models and non-equal candidate
lengths under **both** character and token definitions. Counts and exclusions
are recorded. Token/character scores and absolute/relative primary plots
therefore compare the same questions. Task and all-nine-task views use the
same intersection rule within their scopes. Fixed-label views are exploratory:
semantic category and length are structurally entangled.

An additional `absolute_all_valid` table restores equal-length questions but
still requires every model's output to be valid. It is a distinct descriptive
population and is never silently substituted for the primary plots. The
errors-only filter selects each model's own mistakes; those subsets differ
between models and are not a shared measure of task difficulty.

## Absolute length: magnitude, not just order

Report the mean token length of the selected candidate, correct candidate,
and per-question chance baseline. In all-answer mode, chance samples each
candidate uniformly. In errors-only mode, it samples uniformly among wrong
candidates, because the selected candidate is known to be wrong.

    d_i = tokens(selected_i) - mean(tokens(eligible candidates_i))
    absolute excess = mean_i(d_i)

The difference is paired within question. Positive values mean choices are
longer than this chance baseline; negative values mean shorter. A raw chosen
mean alone is not a preference estimate: some questions have only long answers.
Also report the correct-answer mean, since accurate selection can legitimately
be longer or shorter than chance. Zero excess is not evidence of no bias.
With only one wrong candidate, or equal-length wrong candidates, an errors-only
zero is mechanical, not evidence against preference. Publish the count of
length-identifiable comparisons separately.

Absolute bins (1–8, 9–16, 17–32, 33–64, 65+ reference tokens) report selected
counts, rates, per-question opportunity mass, expected counts and
`selection rate / chance mass`. Each question contributes equal weight;
do not pool candidate counts as if all questions had the same number of
choices. Bins with zero opportunity have a null ratio, not zero. These are
descriptive bins, not a causal test that a model prefers a fixed token threshold.

Absolute means are sensitive to large gaps. An audited CRUXEval wrong candidate
is a 702-digit number (description SHA-256
`7e8893ff47dfed3e51f9d3c89a4d56de12d4e19635ea636efa4ce9743baa7391`).
It has 702 Qwen-reference tokens but 234 Llama-reference tokens: these tokenizers
segment digits differently. Exact decoding confirms no truncation or counting
error. This item remains in the frozen analysis, never silently clipped.
Report the median paired excess and the range of mean excess after removing
each source group in turn. A direction crossing zero under that diagnostic is
not robust to removing one group. It is not a replacement confidence interval,
nor does a stable sign establish a causal preference.

## Relative length: order within the same question

For K candidates, ties receive their midrank:

    r(j) = (# strictly shorter + .5 * # equally long other candidates)/(K-1)
    relative score = 200 * mean(r(selected)) - 100

The range is [-100,+100]; all-candidate uniform chance has expectation zero.
The score is not a percentage or model ability score. It ignores how large
the token gaps are. The errors-only score still uses ranks among all candidates;
its separately reported baseline averages those ranks over wrong candidates.
Compare errors-only choices with that baseline, not automatically with zero.
`relative_excess` subtracts each question's baseline before bootstrap, giving
a paired difference interval rather than a raw-score-versus-fixed-tick test.
Token-versus-character rank differences are paired on exactly the same cohort,
with their own interval; overlapping independent intervals are not a paired test.

## Uncertainty and limits

Use 2,000 source-group bootstrap resamples, stratified by task, with seed
20261021. Questions sharing a recorded source group remain together. Compute
the absolute interval by resampling the paired within-question differences,
not by subtracting two independent confidence intervals. A single source
cluster gets no interval. Means are question-weighted, not task/domain-equal.

Intervals describe question sampling only, not model-population, training,
prompt, or tokenizer uncertainty. They are exploratory and not corrected for
multiple comparisons. Do not infer a family-level architecture effect from
these selected checkpoints. Do not compare interval widths in token and rank
units as a test of which metric is stronger.

Different meanings naturally have different lengths. Neither metric proves
that length itself causes the choices. Establishing that requires a separately
validated, meaning-preserving length intervention with unchanged gold,
controlled order, independent semantic checks, and paired model evaluation.
The constrained-code LLM inference used here has no chain-of-thought and does
not multiply likelihood across the full candidate answer; these findings
cannot be attributed to that particular long-answer likelihood penalty.

## Reproduce

```text
python research/option_length_tokens_v1/collect_tokens.py --help
python research/option_length_tokens_v1/analyze.py
python research/option_length_tokens_v1/analyze.py --check
python -m unittest discover -s tests -p test_option_length_tokens.py
```

Collection requires the private frozen descriptions and pinned cached
tokenizers; public statistical replay does not. Source receipts, deterministic
gzip metadata, script/protocol hashes, JSON and CSV allow independent replay.
