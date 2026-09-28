# System1Bench v0.1 Laya experiment integrity audit

Historical scope: this report covers the original two Laya runs and v0.1 code,
not the added LLM baselines. The [v0.2 comparison review](BASELINE_AUDIT.md) is separate.

Date: 2026-09-28. Reviewer: GPT-5.6-Sol ultra, fresh read-only agent with a
focused follow-up after repairs. **Review independence: same-family. Acceptance:
provisional.** This is an automated integrity review, not external certification.

## Overall verdict: WARN

The repaired release passes every deterministic integrity check. The remaining
warning concerns evidence scope and reference quality, not a numerical mismatch.

| Check | Final status | Evidence |
|---|---|---|
| A. Ground-truth provenance | PASS | Pinned source rows map to frozen states/gold; only state/questions enter inference (`system1bench/common.py:70`, `run.py:100`). Synthetic, authored, programmatic and human references are distinguished. No references come from these Laya predictions |
| B. Score normalization | PASS | Fixed accuracy denominator; failures count as incorrect. Direct F1/Brier/ECE/ordinal calculations (`metrics.py:43`). Only validated rounded probability mass is renormalized (`common.py:57`); no model-max/mean scaling |
| C. Results and claims | PASS | All72 compressed result files,52,900 decisions and6,082 batches exist; zero errors. IDs, inputs, labels, timings, signatures, current inference source, pinned model bytes and24 installed Laya source files match. Independent recomputation matches every summary field and all72 CSV rows; clean regeneration is byte-identical |
| D. Metric execution | PASS | Published functions are reached by suite/OOS/robustness/bilingual/shared-input paths (`metrics.py:123`). CI executes tests, recomputes reports and requires a clean generated-file diff (`.github/workflows/verify.yml:13`) |
| E. Scope | WARN | Two checkpoints, one seed/configuration. Bootstrap does not cover prompt choice, annotation error, training randomness or contamination. Known AG News/BoolQ task-family overlap, unknown other overlap, synthetic/authored references and mostly English instructions are disclosed |
| F. Evaluation types | PASS |36 suites:18 dataset-provided,8 authored/AI-reviewed,8 synthetic-teacher,1 programmatic,1 human-prompt-annotation. All predictions are actual Laya inference; no Jev inference or new human evaluation is claimed |

The tokenizer replay in the first review matched all52,900 stored audits, with
zero truncated states/instructions/options, sanitation events or collisions.
The repaired controls reverse the same unmodified candidate texts; final
request/order audits verify all of them. The complete-input claims are supported.

## Defect found and repaired before publication

**Round one was FAIL.** Banking77 and MASSIVE selected cases shared a question
object. Deep-copying the whole selected list preserved that alias; reversing it
once per case meant100 reversals restored the original order. Their original
“reversed” controls were actually unchanged repeats. The ordinary task metrics
and the JevBench/Reflex controls were unaffected, but the corresponding stability
claims were invalid.

The release copies each case separately and asserts exact reversal plus unchanged
state/gold (`system1bench/prepare.py:34`). Metrics independently reject unchanged
reversal inputs (`metrics.py:139`). A regression test uses100 cases sharing one
question (`tests/test_integrity.py:12`). Both models were fully rerun under the
final code/input signatures; all metrics/reports were regenerated and rechecked.

Final recheck confirmed, for both models:

- Unchanged same-order repeats, and exact changed reversals for Banking77 100/100,
  MASSIVE 100/100, JevBench36/36 and Reflex95/95.
- Correct published agreement rates. For example, English Banking77/MASSIVE
  reversal agreement is52%/50%, replacing the invalid100%/100% claim.
- Ten integrity tests pass, including reversal, categorical argmax/ties and
  rejection of missing completed-run files.

Additional hardening enforces categorical choice/probability consistency, rejects
missing/corrupt files for DONE runs before rewriting results, validates raw result
hashes when rendering a report, and checks regenerated files are unchanged in CI.
The original failed artifacts are retained privately for audit history; they are
not the published benchmark results.

## Reference and licensing qualifications

Prompt-injections label polarity is corroborated by the publisher's pinned
classifier config, with immutable links in [the source review](DATASET_REVIEW.md).
Its narrow definition of legitimate requests limits the score to policy agreement.
Its CC BY4.0/Apache2.0 card conflict remains unresolved; source text is not
redistributed. Other original dataset terms also remain separate from this
repository's code license.

Synthetic teacher agreement is not independently verified human task correctness.
Authored/development fixtures are not pristine held-out natural observations.
Reported confidence is not certified calibration. The release supports the
source-specific static-task findings, not a global decision-intelligence ranking,
production safety guarantee or comparison against an unrun Jev model.

## Final artifact hashes

```text
protocol_manifest.json       625cfbda10b414083a2a5fa7353eaa08fec55caf6c2989e8b6be5625d2e5aa6d
data/frozen.json             5baf87ce9010d8229ea1a39722b865fb5ecc20db3c981e97f51a4baae3653be4
english/metadata.json        01f0709beaaefc2835281b2126c2917d51830ca5bc44d2d04abd1272acf904cf
multilingual/metadata.json   afd9ee7ce5957e5021800cd21de632188a4078e763a570fe854f86cfb0d559d9
results/summary.json         8d16e123d95009d21024b849d39673726854185e491a586373a9d04c836e43c8
results/metrics.csv          672cd083c2adcbbef63f8162a6f46f1d619dd166166b8fd5e4e7f8bf02c576bc
docs/RESULTS.zh-CN.md        aae96107b8a30bee1a50c6f9d1efc4572611da72605c6cf02a1a0b3dd1891e91
```

`data/frozen.json` is reconstructed locally, not redistributed. The metadata
paths above are under `results/`. The companion JSON binds analysis/report code
as well as results, so this review is tied to concrete artifact bytes.
