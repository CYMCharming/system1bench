# Held-out routing conjunction wording

Ninety-six unseen base states are balanced across the four `(outage, paying)` truth-table cells; 24 per cell. Each model answers four matched renderings of one action question per state. A service/response failure counts as incorrect. This is a targeted follow-up motivated by an observed error pattern, not a pre-registered test of the original broad language effect.

| Model | English compact XOR | English explicit XOR | Explicit − compact (pp), paired 95% CI | Improved / worsened |
|---|---:|---:|---:|---:|
| Laya EN | 35/48 | 20/48 | -31.2 [-45.8, -16.7] | 2 / 17 |
| Laya Multi | 12/48 | 25/48 | +27.1 [+14.6, +39.6] | 13 / 0 |
| Llama 3.1 8B | 12/48 | 11/48 | -2.1 [-16.7, +12.5] | 7 / 8 |
| Qwen3 8B | 0/48 | 14/48 | +29.2 [+20.8, +37.5] | 14 / 0 |
| Jev 1.13 | 7/48 | 13/48 | +12.5 [+2.1, +25.0] | 8 / 2 |

## Complete truth table

Each cell has 24 base states. Entries are correct counts in compact → explicit conditions; no state is dropped.

| Model | Cell 00 EN | Cell 01 EN | Cell 10 EN | Cell 11 EN | Cell 00 ZH | Cell 01 ZH | Cell 10 ZH | Cell 11 ZH |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Laya EN | 20 → 17 | 17 → 8 | 18 → 12 | 4 → 15 | 12 → 12 | 9 → 7 | 9 → 5 | 0 → 15 |
| Laya Multi | 13 → 18 | 7 → 10 | 5 → 15 | 0 → 2 | 15 → 14 | 7 → 7 | 9 → 7 | 0 → 0 |
| Llama 3.1 8B | 10 → 13 | 12 → 7 | 0 → 4 | 17 → 24 | 0 → 12 | 0 → 10 | 0 → 4 | 24 → 24 |
| Qwen3 8B | 13 → 18 | 0 → 14 | 0 → 0 | 24 → 24 | 18 → 18 | 3 → 15 | 1 → 14 | 24 → 21 |
| Jev 1.13 | 24 → 18 | 3 → 7 | 4 → 6 | 24 → 24 | 24 → 17 | 24 → 7 | 22 → 6 | 24 → 24 |

All secondary paired effects, failure counts and per-cell denominators are in [summary.json](summary.json). The frozen protocol is [PROTOCOL.md](PROTOCOL.md). Within-language wording differs only in the first policy clause; Chinese text still needs independent bilingual adjudication.
