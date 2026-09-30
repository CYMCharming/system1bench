# Five-model release validation

Executed on the research host after all measured outputs were complete:

- Ruff across `system1bench`, `benchmarks`, `research`, `tests`: pass.
- Unittest discovery: **48 tests**, pass. Native bridge primitive conversion,
  independent request overflow and cache invalidation are covered without GPUs;
  formal model measurements use the separately frozen native research runner.
- Historical metrics/report regeneration, hosted-output archive verification,
  confirmation analysis, policy diagnostics and controlled performance report:
  pass. Historical generated result files remain unchanged.
- Expansion raw replay: five × 4,905 unique decisions, 2,601 requests/model,
  zero invalid outputs; exact prepared input / gold / complete token audit,
  source/model/runner/adapter identity and integer metrics: pass.
- Replication raw replay: two × 3,456 unique decisions, 1,152 requests/model,
  zero invalid outputs; two executable oracles, one decisive fact change,
  576 unique original/CF states excluding all discovery states, every head and
  six primary paired differences: pass.
- `--check-only --public-only` replay of both studies: pass. This checks
  publishable outputs without pretending to re-read private source text and
  does not replace the complete host input-validation receipts.
- Historical context: five × 4,905 exact request/gold matches checked against
  individually hash-bound original source files. These are reuse, not new runs.
- Four PDF/SVG/PNG figures generated from verified summaries. Rendered PNGs
  inspected: point positions, units, intervals, correct/wrong stability stacks,
  model/source labels, legends and text layout. Figure counts and source hashes
  remain inspectable in `figure_data.json`.

The verification receipts bind the verifier, summary and manifest hashes.
These checks establish output integrity and arithmetic, not human construct
validity, model mechanism, novelty, exact bootstrap coverage or deployment safety.
Scientific derived NOINFO, specialized NanoJev training, checkpoint training
confounds, direct Qwen inference and the unmeasured full historical new-model
matrix are disclosed in the result and reproduction documents.

Credentials, private environment/model caches and licensed natural-data freezes
are excluded from Git. The old PDF drafts are preserved; new results are recorded
in the manuscript addendum for explicit future integration.
