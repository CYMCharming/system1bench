# SciFact3 reference provenance

The frozen suites use the legacy suite-level field `reference: "source_annotation"`.
It does **not** mean that every three-way case has a directly annotated label.
Do not edit the frozen requests to repair this metadata field.

`reference_provenance.json` is a text-free, case-level sidecar keyed by
`case_id` and `base_request_sha256`. It is derived after checking the frozen
file and official dev-source hashes against `manifest.json`:

- `SUPPORT` (60) and `CONTRADICT` (60) have an explicit, nonempty official
  `evidence` entry for that cited document, with a consistent rationale label.
- `NOINFO` (60) is **derived** only where the document is in that claim's
  `cited_doc_ids` but has no `evidence` entry. It has not been independently
  adjudicated as a neutral relation and does not assert absence of evidence
  from full text or the wider literature.

The sidecar contains IDs, labels, types and hashes, but no claim or abstract
text. Regenerate or check it with
`python research/scifact3_census_v1/build_reference_provenance.py scifact3_v1 [--check]`.
Upstream schema and licenses are linked within the JSON sidecar and
`DATA_LICENSES.md`.
