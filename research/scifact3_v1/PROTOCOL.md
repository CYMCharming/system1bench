# SciFact three-class cited-abstract diagnostic v1

This is a **pre-inference, model-blind freeze** for a paired three-class diagnostic, not an end-to-end scientific fact-checking or retrieval benchmark. It is independent of the earlier two-class SciFact freeze in `research/domain_expansion_v1/`; neither that file nor its outcomes are modified here. The frozen 180 source pairs and their 720 requests are in `frozen.json` (SHA-256 in `manifest.json`). The reconstruction script refuses to overwrite an existing freeze. The frozen file contains upstream claim/abstract text and is intentionally Git-ignored; see [attribution and redistribution boundaries](DATA_LICENSES.md).

## Reference construction and source audit

Source: [official SciFact repository](https://github.com/allenai/scifact), its [data schema and `cited_doc_ids` explanation](https://github.com/allenai/scifact/blob/master/doc/data.md), labeled `claims_dev.jsonl`, and `corpus.jsonl`. The official documentation defines `cited_doc_ids` as the documents mentioned in the original citation sentence; cited documents in whose **abstracts** annotators found evidence are listed in `evidence`. Its worked example explicitly has a third cited document for which annotators found no abstract evidence. Therefore an eligible claim--document pair must be present in `cited_doc_ids` and in the abstract corpus. It receives `SUPPORT` or `CONTRADICT` if its `evidence` entry has that internally consistent label; it receives our derived `NOINFO` label only if this **cited** document has no evidence entry. We do not turn arbitrary corpus documents without annotations into negatives, nor infer that a NOINFO claim is false or true in the full paper or wider literature.

The official dev split has 300 claims and the corpus has 5,183 abstracts. There are 340 citation-list occurrences but one repeated `(claim, document)` citation for claim 1245; after de-duplication there are **339 eligible pairs: 138 SUPPORT, 71 CONTRADICT, 130 NOINFO**. All cited IDs exist in the corpus. All evidence IDs are included in the corresponding citation list. There are no conflicting rationale labels within a claim--document pair, unknown positive labels, empty evidence lists, empty cited claims/titles/abstracts, or out-of-range rationale sentence indices. Thirteen claims have an evidence-bearing and a no-evidence *different cited document*; this is not a pair-level label conflict. The checks and counts are reproducible with `source_profile.py` and `edge_checks.py`, and the main profile is saved in `profile.json`/`manifest.json`.

The `NOINFO` label is a faithful operationalization of the upstream *absence of annotated abstract evidence for an explicitly cited document*, not a separately adjudicated three-way NLI label. Annotation omissions and borderline abstracts remain possible. We retain this as a distinct **reference-provenance track**, and any comparison with the earlier two-class experiment must acknowledge the changed label space and sampled pairs.

## Frozen selection and interventions

Seed: `system1bench-scifact3-v1-20260930`. For each label, candidate pairs are ranked by SHA-256 of seed, label, claim ID and document ID. To preserve feasibility with the scarce class, the fixed selection order is `CONTRADICT` then `SUPPORT` then `NOINFO`. The first 60 eligible pairs per class are taken subject to a **global maximum of one selected pair per claim ID and one per document ID**. The actual selection succeeds: 60 per class, 180 distinct claims and 180 distinct documents. Only 64 different dev claims have a CONTRADICT citation, so the 60 selected examples are near-saturating for that class. The balanced selection is diagnostic and must not be presented as SciFact's natural class prevalence or a random population sample. No model outputs or benchmark errors enter the ranking.

Each case contains the unmodified claim, full paper title and complete abstract sentences joined by newline. The question asks whether the abstract supports, contradicts, or supplies no evidence for the claim. The title identifies/contextualizes the paper but is explicitly not a substitute for abstract evidence. Evidence sentence indices are not passed to the model. Four conditions are frozen before inference, each with the same case IDs and gold labels:

1. `base`: full state and canonical criterion order.
2. `exact_repeat`: byte-identical inference payload to `base`.
3. `reversed_option_order`: same state, question instructions, criterion text and label meanings; only criterion insertion order is reversed. Code-likelihood LLM adapters can also change code--label assignment under this intervention, so effects are **interface-level sensitivity**, not purely semantic order effects.
4. `title_removed`: delete only `state.paper_title`; claim, abstract, their order, question and criteria remain exactly unchanged. The frozen question still mentions that a title identifies the paper even when the field is absent, creating a small instruction/state mismatch. This is a mechanical visible-title stressor under a fixed abstract, not by itself a causal proof of a title shortcut or a changed evidence standard.

Thus the plan is **720 requests per system**. `validate.py` independently reconstructs all source pair labels and request transformations from raw SciFact files, checks all 720 request hashes and the frozen-file hash, and records `validation.json`. `audit_inputs.py` uses each adapter's actual local tokenizer and prompt builder, recording `input_audit.json`.

## Analysis plan and limitations

Report base confusion matrix and class-specific recall, balanced accuracy, invalid/error rates and complete-payload coverage. For paired controls report unconditional prediction flips, reference-correct stability, correction (`wrong→right`), regression (`right→wrong`) and excess reversal flips over exact-repeat, separately by reference class and system. The title-removal comparison should report paired changes and show whether NOINFO decisions specifically move toward support/contradiction; do not assert that every movement is error caused by title lexical overlap. Because every selected claim and document is unique, pair-level resampling is also claim- and document-level resampling for this freeze; use paired, label-stratified bootstrap for descriptive uncertainty and preserve the same sampled IDs across conditions. Small sample and balanced selection mean these intervals do not justify population-prevalence or broad-domain claims.

The local pre-run audit found all **720/720 requests complete** on Laya English, Laya multilingual, Llama 3.1 8B Instruct and Qwen3 8B tokenizers: maximum Laya state lengths 1,420/1,438 versus the 8,192 budget, and maximum LLM rendered prompts 1,597/1,589 versus 32,768 model limits. The hosted Jev service's tokenizer/context handling is not locally observable, so a complete HTTP payload alone is not proof of full server-side context use. All systems evaluate a **model plus typed-choice adapter** on a supplied cited abstract. This protocol does not test retrieving the right paper, finding evidence spans, evaluating full texts, or deployed fact-checking. Source annotations are references, not independent re-adjudicated truth.

Reproduce source checks/freeze from the repository root, after obtaining the official SciFact archive at the hashed path given in `manifest.json`:

```bash
.venv/bin/python research/scifact3_v1/source_profile.py
.venv/bin/python research/scifact3_v1/prepare.py  # only in a fresh output directory
.venv/bin/python research/scifact3_v1/validate.py
PYTHONPATH=.:/mnt/sata2/cym/laya /home/cym/miniconda3/envs/lmeval/bin/python research/scifact3_v1/audit_inputs.py
```

The final command is specific to the checked gpu29-cym installation; adapt the environment path elsewhere without changing the frozen requests.
