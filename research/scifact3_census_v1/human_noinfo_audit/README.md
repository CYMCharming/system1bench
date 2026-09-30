# Blinded review workspace

Prepared, not annotated. The protocol and builder are hash-bound to the local
packets. Keep them unchanged after preparation. Do not publish source text.

Give each independent reviewer only PROTOCOL.md, their packet and blank answer
form; do not share restricted_manifest.json or model results. Multiple evidence
sentence indices in a form are separated by semicolons, for example `1;3`.
The validator rejects missing IDs, duplicate IDs, invalid/blank labels, absent
rationales, invalid confidence, missing evidence for positive judgments and
out-of-range indices. Reviewer identities must be distinct. A third reviewer
adjudicates disagreements and UNCERTAIN items after independent hashes lock.

`validate_packet.py` is a preparation check requiring blank forms, not a way to
validate completed annotation. `analyze_annotations.py` handles completed forms.
Never regenerate packets over human work. Store completed human reports locally
until rights and collaborator approval are resolved.
