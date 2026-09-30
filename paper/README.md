# System1Bench paper drafts

`main.tex` is the extended research preprint, with detailed experiments and appendices; it is not trimmed to a conference main-text limit. `submission.tex` is a separate, compact, anonymous *prospective* E&D-style draft whose main text is checked against a nine-page limit. It uses the NeurIPS 2026 `[eandd]` style only as an internal layout rehearsal. The 2026 deadline has passed: neither PDF is a submitted or accepted paper, and a future venue's instructions must be rechecked.

The evidence has distinct sampling and reference scopes: 15 historical source collections (28 main suites and eight case-reusing controls), 288 fresh executable-policy states, 144 selected ContractNLI document–hypothesis pairs, 120 positive-evidence SciFact claim–cited-abstract pairs, and a separately frozen *follow-up* of 180 three-class SciFact cited pairs. The follow-up was designed after the two-class scope gap was observed but before its own inference. A subsequent post-hoc same-source census reran all five systems on all 339 eligible three-class cited pairs; its 159-pair complement to the balanced selection is not an independent holdout. The NoInfo source convention means a cited abstract lacks annotated evidence; it is not an independently adjudicated negative. Percentages from unlike references and samples are not pooled into a leaderboard. Protocols, analyses and source notes reside in `../research/domain_expansion_v1/`, `../research/scifact3_v1/`, `../research/scifact3_census_v1/`, `../research/scifact3_codebook_v1/`, `../research/natural_direct_v1/` and the other named study directories.

Build either document from this directory with `latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex` or the same command using `submission.tex`. Regenerate numerical tables with `python paper/build_assets.py` from the repository root. Figure generators under `figures/gen_*.py` require Matplotlib and their frozen analysis summaries; `references.bib` is shared by both documents. The compact figures have dedicated `*_main` or `*_compact` files so the extended preprint's graphics are preserved. `fig_scifact3_census_main.pdf` was laid out at native single-column width, with verified source counts and print-size lettering.

Source-containing legal and scientific freezes are local-only. Review `../research/domain_expansion_v1/DATA_LICENSES.md`, `../research/scifact3_v1/DATA_LICENSES.md` and `../research/scifact3_census_v1/DATA_LICENSES.md` before any redistribution. Case-level reference-provenance sidecars explicitly separate annotated SUPPORT/CONTRADICT from derived cited-absence NOINFO. No public artifact release, official venue checklist completion, or source-license clearance is asserted. Independent construct/bilingual validation, artifact packaging and venue-specific anonymity/checklist review remain open; do not publish or push the drafts or restricted freezes without separate authorization.

The 2026-09-30 execution-context follow-up adds 6,780 local LLM decisions on
the same 339 census pairs, two interface conditions and five execution plans.
`../research/batch_context_v1/` retains its prospectively frozen follow-up
protocol/schedule, raw logits, independent verifier and summary. The native-width
`fig_batch_context.pdf` shows execution drift and class-specific interface effects
with paired claim-cluster intervals. This is a same-source robustness diagnostic,
not a new independent benchmark sample.

The blinded review package in
`../research/scifact3_census_v1/human_noinfo_audit/` is prepared but not annotated:
130 derived NOINFO pairs plus 30 concealed calibration items, independently
randomized orders, blank forms, validation and adjudication tooling.
Its source-containing `local_packets/` is precisely ignored. No human-validity
result exists; generated labels cannot replace independent human review.
