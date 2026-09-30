# Independent natural-domain paired diagnostic

This is a separately frozen extension to the 15-source historical atlas, not a new pooled leaderboard. Five fixed model–adapter systems were evaluated on the same **144 ContractNLI document–hypothesis pairs** and **120 SciFact claim–cited-abstract pairs**. Each pair received a base request, a byte-identical repeat and a criteria-order reversal: 792 requests/system, 3,960 total. The four local adapters' inputs were token-audited as complete; the hosted provider's server-side tokenization is not observable. Full [selection/protocol](PROTOCOL.md), [source attribution](DATA_LICENSES.md), [model-blind shortcut audit](SHORTCUT_AUDIT.en.md), [machine-readable outcomes](summary.json) and [vector figure](../../paper/figures/fig_domain_expansion.svg) are available alongside the code.

Reference agreement is conditional on the deliberately balanced sample, not an estimate of naturally prevalent legal or scientific task accuracy. The two source annotations have different construct scope and are **never pooled**.

| Source | System | Base reference-correct | Correct both base/reversal | Reversal reference-correct | Correction / regression | Valid-label reversal flips | Literal-repeat flips |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| ContractNLI, 144 | Laya English | 56 | 53 | 58 | 5 / 3 | 13 | 0 |
|  | Laya Multilingual | 49 | 42 | 49 | 7 / 7 | 18 | 0 |
|  | Llama 3.1 8B | 44 | 33 | 59 | 26 / 11 | 66 | 0 |
|  | Qwen3 8B | 65 | 51 | 83 | 32 / 14 | 64 | 0 |
|  | Jev 1.13 | 111 | 107 | 109 | 2 / 4 | 6 | 2 |
| SciFact, 120 | Laya English | 65 | 62 | 63 | 1 / 3 | 4 | 0 |
|  | Laya Multilingual | 70 | 68 | 71 | 3 / 2 | 5 | 0 |
|  | Llama 3.1 8B | 60 | 57 | 59 | 2 / 3 | 5 | 0 |
|  | Qwen3 8B | 92 | 81 | 84 | 3 / 11 | 14 | 0 |
|  | Jev 1.13 | 112 | 112 | 112 | 0 / 0 | 0 | 0 |

The legal LLM result illustrates why a single net score is insufficient. Llama and Qwen gain 15 and 18 correct answers under ordinary reversal, but respectively turn over 66 and 64 of 144 predictions; their jointly correct counts are only 33 and 51. Clustered paired accuracy changes are +10.4 percentage points for Llama (95% interval [+2.8,+18.3]) and +12.5 for Qwen ([+4.2,+20.7]). These are changes in the **combined display-order and answer-code mapping** of a constrained next-token adapter; they do not establish that reversing a list improves contract understanding. A separate 2×2 codebook control is being analyzed. On SciFact's positive-evidence pairs, Qwen instead loses eight net correct answers (−6.7 points, [−12.5,−0.8]); reclustering by the 111 abstracts rather than 120 claims changes that interval only to [−12.7,−0.8]. Jev keeps the same 112 SciFact pairs correct under both renderings. The observed direction of net change thus differs by source and adapter, while the joint-correct count discloses how many particular decisions remain correct.

The literal-repeat control is not a universal noise-floor estimate: the four local adapters use deterministic inference, whereas hosted Jev can vary. In the completed Jev run, two ContractNLI labels changed under literal repeat and six under reversal; no SciFact label changed under either. An initial hosted pass stopped after 216 requests because one HTTP-200 choice disagreed with its own maximum-probability option. That append-only aborted journal is preserved separately and **not** mixed with the fresh 792-request primary pass. The primary pass used a versioned runner that records malformed typed answers as invalid rather than silently repairing them; it encountered none. No API key or authentication header is stored in results. Accounted input-token cost for the complete primary pass was USD 0.05055, not a claim about comparative model cost or server runtime.

## What the source audit changes

- The ContractNLI 16,000-character cap removes 24/123 contracts; 13/23 SEC-HTML documents are excluded, versus 7/76 PDF and 4/24 SEC-text. This is extraction-format selection skew, not a legal-domain taxonomy.
- The selected legal labels are 48/48/48, while the official 2,091 test annotations are 968 entailment, 220 contradiction and 903 not-mentioned. The 17 hypothesis IDs repeat across contracts. A lookup learned solely from official *training* contracts' modal label for each ID reaches **82/144 (56.9%)** on the frozen sample without reading a contract (95% document-cluster interval [49.3%,64.3%]). This is a supervised shortcut diagnostic, not a fair zero-shot comparator or proof that an evaluated system used the shortcut.
- The SciFact task here is **binary relation classification with a positively annotated cited abstract supplied**, not retrieval or full three-way fact-checking. It samples 60/64 eligible contradiction claims and 60/124 support claims and excludes all no-information claims. Claim-writing mechanisms and shared abstracts may enable other shortcuts; a three-way follow-up is separately specified.
- The task prompts include SciFact paper titles and tell models to use supplied evidence rather than outside materials. A future no-title sensitivity is needed before attributing behavior to abstract content alone.

All intervals are pointwise descriptive 10,000-draw percentile bootstraps over source documents or claims, not simultaneous paper-wide tests. Local probability heads, LLM candidate-code softmax scores and hosted typed confidence have different semantics; only selected-label outcomes are compared here. This extension informs *typed decision interfaces under matched source inputs*, not whole-system legal advice or scientific truth adjudication.
