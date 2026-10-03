# Pinned Kev-27B and Qwen comparison extension

This is a new measured extension, not a rewrite of the immutable
`model_expansion_v1` runs. All four models receive precisely the same 2,601
requests and 4,905 typed decisions per model as the earlier five models:
three executable-policy families (refund, access, routing), source-labelled
ContractNLI, and cited SciFact with the same derived NOINFO label. Every
request identity, gold answer and SHA-256 is matched before ranking. Repeated
or reversed cases are diagnostic controls, not fresh independent questions.

Model identities are pinned to official Hugging Face repository commits:

| ID | Official checkpoint | Revision | Interface |
|---|---|---|---|
| `kev_27b` | `jaredpalmer/kev-27b` | `af0e6d551bdc2cc724f3e9d7a8bee1cd4fb8f7bf` (Kev 1.0 / v2) | Official Kev pointer head and calibrated temperature |
| `qwen35_08b` | `Qwen/Qwen3.5-0.8B` | `2fc06364715b967f1860aea9cf38778875588b17` | Direct candidate-code likelihood; thinking off |
| `qwen35_4b` | `Qwen/Qwen3.5-4B` | `851bf6e806efd8d0a36b00ddf55e13ccb7b8cd0a` | Same direct interface |
| `qwen38_27b` | `Qwen/Qwen3.8-27B` | `1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0` | Same direct interface |

The 27B Qwen checkpoint is Kev-27B's **post-trained base**, unlike the
Qwen3.5-Base backbones of older Kev-0.8B/4B/9B. This makes the 27B pair an
especially informative, but not causal, comparison of decision fine-tuning
against direct constrained output. The older Kev-9B result is an earlier
immutable checkpoint, not Kev 1.0's newer v2 revision. Do not infer a
within-family size law from these four releases. Training sets, post-training
and inference objectives differ.

The Qwen adapter uses the *same* supplied-information prompt, candidate codes,
single-next-token likelihood and `enable_thinking=False` as the existing
Qwen3.5-9B baseline. No generative reasoning ceiling is claimed. All text is
run without vision inputs, and the largest 32k-token context cap of the
earlier extension is retained. Kev probabilities are checkpoint-calibrated;
Qwen likelihoods are normalized across supplied code tokens and are not
calibrated correctness probabilities. Accuracy and exact paired correctness
are comparable; probability-dependent calibration/risk curves require separate
interpretation.

The downloadable original source text and model weights are excluded from
Git. Public raw outputs record the canonical request SHA-256, label,
prediction, probability vector, input-length audit and model-code hashes.
Official model files are verified byte-for-byte against Hugging Face LFS
SHA-256 or Git blob IDs during transfer. No TLS verification is disabled.

Data quality gates: exactly 4,905 non-duplicated decisions per model; no
invalid outputs; every `(suite, case, question)` equals the frozen source;
request hashes and gold answers agree across all models; no partial request;
all reference-type and source-validity distinctions remain visible. Policy
action gold is executable. Legal labels reflect source annotations. SciFact
NOINFO is derived absence of annotation, not a separate adjudicated truth.
The descriptive three-domain equal-weight score and five-task sensitivity
score are the same post-hoc navigation devices as in `leaderboard_v1`; neither
is a universal model-quality claim. Uncertainty uses paired cluster resampling
at policy state, legal document and scientific-claim grain.
