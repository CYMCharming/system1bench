# Human review of SciFact cited-pair NOINFO references — **not yet performed**

This protocol prepares a blinded review of **all 130** cited SciFact dev
claim–abstract pairs whose `NOINFO` reference was derived from an explicit
`cited_doc_ids` entry with no annotated abstract evidence. It also mixes in
**15 official SUPPORT and 15 official CONTRADICT** pairs as concealed
calibration items. The 30 calibration items are not a substitute for human
adjudication of the 130 derived references. No generated packet or template
contains model predictions, code logits, original reference labels or a
`NOINFO`/calibration stratum flag.

## Build and provenance

Run from the repository root:

```sh
python research/scifact3_census_v1/human_noinfo_audit/build_packet.py --seed 20260930
```

The builder verifies the official SciFact dev and corpus SHA-256 values,
the immutable 339-pair freeze, and the case-level `reference_provenance.json`.
For each candidate it checks citation membership, evidence-entry status,
reference label, complete title/abstract equality to the frozen case and
unique claim–document IDs. It selects calibration pairs by a seeded,
model-blind shuffle **before annotation**. The seed, selected source IDs,
strata, file hashes and `audit_id` mapping are retained only in
`local_packets/restricted_manifest.json`. Annotators receive `packet_A.csv`
or `packet_B.csv` respectively, with the same pseudonymous cases in
independently randomized orders. `answers_A.csv` and `answers_B.csv` have
blank label fields. The builder refuses to overwrite any packet directory.

`local_packets/` is precisely ignored by the adjacent `.gitignore` because
it contains complete third-party claim, title and abstract text. Do not
publish, commit, email or otherwise redistribute it without a separate
license/rights review. The packet's `NOTICE.txt` identifies the sources:
[SciFact schema](https://github.com/allenai/scifact/blob/master/doc/data.md),
[SciFact license](https://github.com/allenai/scifact/blob/master/LICENSE.md)
(claims/evidence CC BY 4.0; S2ORC abstract corpus ODC-By 1.0), and the
[SciFact paper](https://arxiv.org/abs/2004.14974). Database licensing does
not necessarily resolve rights in every underlying abstract.

## Independent annotation instructions

Two annotators independently read **only** the supplied claim, title and
numbered abstract sentences. The title identifies the cited paper; it is
not sufficient evidence by itself. Do not consult model outputs, original
SciFact annotations, outside knowledge, paper full text or each other's
answers before both forms are locked. For each `audit_id`, choose:

- `SUPPORT`: the abstract itself provides sufficient evidence for the claim;
- `CONTRADICT`: the abstract itself provides sufficient evidence against it;
- `NOINFO`: the abstract provides neither sufficiently supporting nor
  contradicting evidence;
- `UNCERTAIN`: text quality, mixed evidence or genuine ambiguity prevents
  a defensible choice among the first three. Do **not** silently force this
  class into `NOINFO`.

Record confidence (`high`, `medium`, `low`), zero-based abstract sentence
indices supporting the judgment (or blank for no evidence), one reason code
(`none`, `mixed_evidence`, `insufficient_detail`, `text_quality`,
`full_text_needed`, `other`), a short rationale, and an annotator ID.
`NOINFO` may have an empty evidence index but must explain what is missing.
Use the CSV schema in `ANNOTATION_TEMPLATE.csv`; never edit source columns
in the packet. Time spent, annotator background, training examples (if any),
and any protocol deviations should be logged separately without model output.

## Lock, adjudication and reporting

After both independent forms are complete, preserve their SHA-256 hashes and
run:

```sh
python research/scifact3_census_v1/human_noinfo_audit/analyze_annotations.py prepare-adjudication
```

This validates IDs and labels, computes exact agreement and four-category
Cohen's kappa for all items and separately for the 130 derived-reference
items and 30 calibration items, then creates `adjudication_queue.csv` only
for disagreements or `UNCERTAIN` answers. A third reviewer uses the same
abstract-only definitions, sees the two independent labels/rationales but
not source/reference stratum or model outputs, and fills
`adjudication_answers.csv` using `ADJUDICATION_TEMPLATE.csv`. Unresolved
items remain `UNCERTAIN`; no automatic majority rule or post-hoc exclusion.
Then run `analyze_annotations.py report` for final stratum-separated counts,
disagreement and unresolved rates, calibration-vs-official convention
agreement, and an audit manifest of input hashes. The report is written
under ignored `local_packets/` until collaborators approve what can be
released. This procedure can establish how the reviewed annotators judge
these abstracts; it does not prove global scientific truth or that the
models reasoned from the abstracts.
