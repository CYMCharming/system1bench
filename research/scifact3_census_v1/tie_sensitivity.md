# SciFact3 full-census decoder-tie sensitivity

This is a **post-hoc offline re-decoding** of the two fixed LLM code-logit
adapters on all 339 fresh cited claim--abstract pairs. It neither modifies
the recorded native outputs nor performs additional inference. The script
`tie_sensitivity.py` independently verifies the four raw gzip SHA-256 hashes
per model against `summary.json`, checks every semantic probability/top-logit
tie, and recovers the published native counts and full base-to-reversal
transition matrix before applying one fixed semantic tie priority:
`SUPPORT`, `CONTRADICT`, `NOINFO`. The raw records and JSON report do not
contain claim or abstract text.

| Model | Top ties, base / reversal | Reversal labels changed by fixed tie | Native base → reversal correct /339 | Common-tie base → reversal correct /339 | Base→reversal flips, native → common |
|---|---:|---:|---:|---:|---:|
| Llama 3.1 8B Instruct | 11 / 7 | 7 | 182 → 158 | 182 → 159 | 73 → 77 |
| Qwen3 8B | 3 / 1 | 1 | 231 → 220 | 231 → 219 | 97 → 98 |

The base, exact-repeat, and title-removal conditions already use the common
semantic first-maximum priority, so no decisions in those three conditions
change. In reversed criterion order, the native decoder instead prioritizes
`NOINFO`, then `CONTRADICT`, then `SUPPORT`; all 7 Llama and 1 Qwen top-tie
cases change under the fixed rule. Qwen's NOINFO-reference correct count
under reversal changes only 68 → 67/130; Llama's changes 25 → 23/130.
The direction of the aggregate and NOINFO findings therefore remains, but
the precise turnover count has a decoder component. These values are a
fixed-sample sensitivity, not new confidence intervals or a factorial
decomposition on the 339 pairs. The earlier four-cell factorial control
covers only the selected 180 old-run cases; it cannot assign the full-census
joint reversal effect to display versus code identity.

Machine-readable evidence, including safe pair IDs, raw hashes, class-wise
counts and both transition matrices, is in `tie_sensitivity.json`. The
original native census `summary.json` remains the primary record.
