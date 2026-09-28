# System1Bench v0.2 comparison integrity audit

Date: 2026-09-28. Reviewer: GPT-5.6-Sol ultra, fresh read-only reviewer with focused repair and final-artifact follow-ups. **Same-family / provisional**, not external certification.

**Final A–F Integrity Audit**

`overall_verdict: WARN`

`blocking_experimental_defects: none`

**A. Ground-truth provenance: PASS**

Source bytes are verified before preparation, and reference types remain explicit: dataset labels, authored/AI-reviewed fixtures, synthetic teachers, programmatic references, and human prompt annotations are assigned separately in [prepare.py](../system1bench/prepare.py#L49), [prepare.py](../system1bench/prepare.py#L65), [prepare.py](../system1bench/prepare.py#L83), [prepare.py](../system1bench/prepare.py#L99), and [prepare.py](../system1bench/prepare.py#L117). Gold fields are excluded through the request whitelist at [common.py](../system1bench/common.py#L70) and [run.py](../system1bench/run.py#L100).

**B. Score normalization: PASS**

The LLM adapter uses stable float64 candidate-logit softmax and bounds only floating-point roundoff in expected ordinal scores at [llm_adapter.py](../system1bench/llm_adapter.py#L42). Decoding validates probability domains and mass at [common.py](../system1bench/common.py#L46); published accuracy is direct correctness, while normalization is confined to probability metrics at [metrics.py](../system1bench/metrics.py#L43). The conditional candidate-code semantics and lack of calibration equivalence are disclosed at [LLM_BASELINES.md](../docs/LLM_BASELINES.md#L58). No output-dependent max/mean accuracy rescaling exists.

**C. Raw results and claims: PASS**

Independent reconciliation covered all 144 gzip files and 105,800 rows. Each model has 36 suites, 26,450 decisions, 3,041 batches, zero errors, and 26,450 complete inputs. Correct counts are English 15,093; multilingual 14,756; Llama 15,280; Qwen 18,047.

All IDs, question IDs, request/question hashes, gold labels, types, labels, metadata, batch counts, probabilities, predictions, expected scores, file hashes, and embedded signatures matched frozen inputs and metadata. Cross-model identity passed for all 26,450 decision keys. The validation path is enforced at [run.py](../system1bench/run.py#L24), [metrics.py](../system1bench/metrics.py#L104), and [metrics.py](../system1bench/metrics.py#L173).

CPU replay independently reproduced all 52,900 LLM prompt-token hashes, prompt lengths, and state-token counts. All 151 codes were distinct single tokens. Maximum prompts were 4,005 Llama and 4,045 Qwen tokens against a 32,768 limit. Both published metadata files identify `coded-choice-v2` at [Llama metadata](../results/llama31_8b_instruct/metadata.json#L41) and [Qwen metadata](../results/qwen3_8b/metadata.json#L41).

Independent recomputation exactly matched `summary.json`, all 144 CSV rows, all README tables, and the Chinese report. Current hashes are:

```text
summary.json          9ab27a1b6ec4f81f2b81e7af775d626c0498c727e18ebc55f224c14e91aafbc4
metrics.csv           61a1da071989e82e8f696dbf700801c4f23826f742f073210fdff273443a1c87
README.md             9eddfe5e97477bad553e259fdeed72d55e72876cd70ea2c402ad6a2f28213364
RESULTS.zh-CN.md       25c0fccc4174285415f64641717631e1a5611a14301bf9476eb0e0e579488348
```

**D. Metric reachability: PASS**

Published metrics, OOS, robustness, bilingual, shared-input, ordinal, and reporting paths are executed from [metrics.py](../system1bench/metrics.py#L99) and [report.py](../system1bench/report.py#L65). CI reruns tests, metrics, reports, and a clean generated-artifact diff at [verify.yml](../.github/workflows/verify.yml#L13). All 18 tests and Ruff passed.

**E. Scope and external validity: WARN**

The evidence covers four checkpoints with one seed and one fixed configuration each. It remains sensitive to prompt wording, answer-code priors, candidate ordering, unknown training contamination, synthetic/authored reference quality, and mostly English instructions. Candidate-softmax probabilities are not directly comparable to Laya decision-head confidence. Timing is synchronized batch inference, not controlled serving latency. These limits are disclosed at [PROTOCOL.md](../PROTOCOL.md#L116), [LLM_BASELINES.md](../docs/LLM_BASELINES.md#L64), and [RESULTS.zh-CN.md](../docs/RESULTS.zh-CN.md#L169).

Llama’s extra `configuration.json` has no remote blob metadata at [LOCAL_CHECKPOINT_VERIFICATION.json](../docs/LOCAL_CHECKPOINT_VERIFICATION.json#L95). Its local bytes match the hash-bound run metadata and Transformers does not load it, so this is a provenance limitation rather than a result-integrity defect.

**F. Evaluation types: PASS**

Real dataset/human labels, synthetic proxies, authored fixtures, and programmatic references are visibly classified in the result table at [README.md](../README.md#L41). Synthetic/authored results are explicitly described as reference agreement at [README.md](../README.md#L35). No new human evaluation or Jev run is claimed; [README.md](../README.md#L9) states that Jev was not evaluated.

The earlier v1 LLM runs were correctly rejected after discovering omitted custom boolean criteria and an out-of-range FP32 expected score. The published candidates are v2: supplied boolean meanings are preserved at [llm_adapter.py](../system1bench/llm_adapter.py#L16), and the stable bounded score path is at [llm_adapter.py](../system1bench/llm_adapter.py#L42). Rejected logs remain outside publication under the ignored `local_logs/` tree at [.gitignore](../.gitignore#L9). Original Laya artifacts remain byte-identical to the original v0.1 commit `19646b896d4120c4de1f41ae065019085a29e0f7`.

The final audit artifact is recorded in this file. Correct-count totals above are integrity checks, not a blended performance leaderboard.

`review_independence: same-family`

`acceptance_status: provisional`
