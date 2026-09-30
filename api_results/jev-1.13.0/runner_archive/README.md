# Exact historical API client

`jev_api.py` preserves the source bytes used for the original Jev 1.13.0 matrix.
SHA-256: `e915d685d4780f9409b8a72474ae8a55ee0d3241aa1b64a29ae42fa1a96dc555`.
Recovered from Git commit `50546e5` without changing the measurement contract,
request journal, response files, timing or probabilities. It is an archival
source artifact, not a new inference run or a standalone entry point at this
nested directory. The current client adds capabilities for later frozen studies;
it must not be retroactively described as the source of earlier measurements.

The public verifier accepts a source only if its hash matches the original
contract. It does not accept arbitrary code drift or recompute contract hashes.
