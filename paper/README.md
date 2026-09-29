# System1Bench working paper

Title: System1Bench: Typed Decisions Across Domains and Matched Interventions.

This is a research draft, not a submitted or accepted paper. The current NeurIPS-style preprint has 11 main-text pages and 19 pages including references/appendices. Authors remain anonymous placeholders until author metadata is provided. The draft exceeds a nine-page main-text limit and needs a venue-specific trim before submission.

Build: run `python paper/build_assets.py` at repository root, run the `paper/figures/gen_*.py` scripts with Matplotlib available, then `latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex` in this directory. The tracked `references.bib` supports offline compilation. Generated numerical tables and figures consume saved measured analyses and never depend on ignored local caches.

The domain/function atlas is generated from `source_atlas.json`; it maps 15 source collections and 28 suites without pooling unlike reference standards. The separately frozen wording follow-up is documented in `../research/wording_v1/PROTOCOL.md`, with verified outputs in `summary.json` and `RESULTS.en.md`. It tests a post-hoc conjunction hypothesis on 96 new states and yields mixed English/Chinese effects, so no universal wording benefit is claimed.

Review status and limitations are recorded in `../research/RESEARCH_PROGRESS.zh-CN.md` and the paper. Independent human construct and bilingual wording validation, stronger baseline settings, and a venue-specific length edit remain open. The manuscript and generated figures are kept local on gpu29 pending review; do not push them to a public remote without separate authorization.
