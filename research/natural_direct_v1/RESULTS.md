# Strict direct-generation control on natural-domain cases

The pre-inference freeze includes exactly 144 selected ContractNLI legal
document--hypothesis cases and 180 selected three-class SciFact
claim--cited-abstract cases. Each Llama-3.1-8B-Instruct and Qwen3-8B
prompt's rendered token IDs were checked against the saved historical
code-logit prompt token SHA-256 and length **before** generation. The same
checkpoints, chat templates, adapter system/user messages, batch size four,
BF16/SDPA and greedy decoding were used. The response grammar accepts only
one candidate code as the entire decoded completion; the fixed 16-token
limit and parser were not tuned on outcomes.

| Model | Domain | Code-logit correct | Strict direct correct | Invalid / paired flips | Paired accuracy effect, 95% source-cluster interval |
|---|---|---:|---:|---:|---:|
| Llama 3.1 8B | ContractNLI | 44/144 | 44/144 | 0 / 0 | 0.0 pp [0.0, 0.0] |
| Llama 3.1 8B | SciFact3 | 78/180 | 78/180 | 0 / 0 | 0.0 pp [0.0, 0.0] |
| Qwen3 8B | ContractNLI | 65/144 | 65/144 | 0 / 0 | 0.0 pp [0.0, 0.0] |
| Qwen3 8B | SciFact3 | 104/180 | 104/180 | 0 / 0 | 0.0 pp [0.0, 0.0] |

All 648 generations are valid under the strict parser, and each produces
the **same discrete semantic label** as its historical constrained
next-token output. Thus corrections and regressions are also zero. The
legal intervals resample 91 source contracts, and the science intervals
resample 180 unique source claims, with 10,000 paired percentile draws
and seed 20260930. The equal-domain macro effect is likewise 0.0 pp
[0.0, 0.0] for both models. These degenerate intervals are the exact
consequence of zero observed paired differences, not evidence of
equivalence under other prompts, domains or inference settings.

This is a useful interface control but **not** a best-prompted-performance
claim: a single zero-shot candidate-code prompt and 16-token greedy
completion may constrain model behavior. Direct generations do not yield
the typed conditional option probabilities of the code-logit adapter and
are not treated as probabilistically equivalent. Neither domain sample
represents natural prevalence; SciFact3 NOINFO is operationally derived
from lack of annotated abstract evidence for a cited document.

`frozen.json` contains only IDs, groups, reference labels, candidate codes
and hashes; it does not duplicate upstream contracts/abstracts. `manifest.json`
pins the two source freezes, historical output and metadata files, parser,
adapter and protocol. `results/{llama31_8b_instruct,qwen3_8b}/metadata.json`
contains the model/inference signature, output SHA-256, validity, token and
synchronized batch-time totals. The corresponding `raw.jsonl` preserves
decoded text, generated token IDs, prompts hashes, errors and batch data;
it is exactly Git-ignored because an invalid generated response could echo
upstream text. `analyze.py` independently reparses the raw text and
SHA-verifies every paired comparator; `summary.json` contains the audited
per-source and macro estimates. Synchronized generation alone took 49.5 s
for Llama and 54.1 s for Qwen, excluding load and prompt
tokenization; it is not mixed with the paper's separate performance assay.
