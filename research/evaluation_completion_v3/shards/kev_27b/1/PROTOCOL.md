# Single-request execution sharding, v3

Declared before shard inference on 2026-10-09. This is an execution-only
supplement to evaluation_completion_v1, not a new task or scoring protocol.
The two unfinished 27B intent runs are partitioned across four A100 80GB GPUs.
No other user's process is stopped. Completed, flushed original rows are
retained unchanged; the unfinished request, if any, is repeated after migration.

The full 8,580 frozen requests, 151/77 choices, checkpoint tensor bytes,
native adapters, probability semantics, single-request batch size, and scoring
rules remain unchanged. No tuning, generation, quantization or timing ranking
is introduced. Remaining cases are assigned alternately by source index to two
workers; assignment never uses predictions, correctness or gold labels.

Each shard has its own immutable input file, manifest, source binding, full
input audit, and append-only journal. The original completed prefix also has
an immutable file-hash receipt. The union is accepted only when the fragments
are disjoint, cover every original case exactly once, preserve every original
request digest and full ontology, retain identical checkpoint tensor hashes,
and reproduce the original preflight token audits. No placeholder predictions
or synthetic completion receipts are inserted into unfinished original runs.

An explicit verified-shard-union output preserves all fragment receipts and
their original journal bytes. It is independently replayed before publication.
The public manifest records source indices and fragment input hashes; the
text-free prediction projection allows complete-case classification replay.
GPU co-tenancy is allowed for accuracy, never for the separate latency board.
