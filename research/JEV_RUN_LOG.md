# Jev execution interventions

## Completion and retry-policy deviation

2026-09-29: The historical matrix completed 22,934 requests / 26,450 decisions, with four choice/probability-validation failures affecting eight decisions. The fresh policy matrix then completed 2,304 requests / 6,912 decisions, with one HTTP 520 response affecting three decisions (`refund:101:023:chinese`). All failures remain in primary denominators; none was repaired or replayed.

The frozen protocol's phrase “5xx” was broader than the frozen implementation: the runner retries only HTTP 429, 500, 502, 503, 504 and 529, plus transport exceptions. HTTP 520 received one attempt, not five. This is a documented protocol/implementation deviation, not a fully conformant retry execution. The runner and recorded outputs remain unchanged. The corresponding primary refund Chinese-minus-original action effect is -1/96 (-1.0417 percentage points); the valid-pair sensitivity excludes that entire matched base pair and is 0/95 (0 percentage points). That sensitivity is conditional on a successful response and does not replace the primary system-level result. No claim of a linguistic regression follows from this service failure.

Accounted input-token charges were USD 1.001358666 for the historical matrix and USD 0.064318674 for confirmation; unreported failed-call usage and excluded toy pilots are not invoice reconciled.

An independent record-order audit found one historical resume-boundary inversion: journal line 11,184 is `typed_decisions:68` (manifest index 11,184), followed by line 11,185 `massive_zh:1346` (manifest index 10,467). Thus the complete journal is append-only but not globally manifest-ordered, contrary to the protocol's ordering phrase. Request identities, payload hashes, decoded outputs and the complete matrix are checked by key; the inversion changes neither selection nor scoring. Original journal bytes are retained.

2026-09-29: Started the frozen full matrix with the pinned runner and Jev 1.13.0. After 6,684 journaled requests, one response failed the predeclared choice/probability consistency check (SST5 choice case `sst5:1519`). The returned choice was `neutral`, while the exposed distribution's argmax was `positive` (0.47 versus 0.46). The runner halted further calls and retained the complete returned model/answer/usage and failure. No answer was replaced or repaired.

After inspecting the stored response, resume the SAME contract/runner from unexecuted requests. All 6,684 journaled requests, including the failed one, remain immutable and are not replayed. This is recovery after an inspected interface fault, not fastest-run or score-based selection. Public scores must count the invalid answer as a failure; a valid-only sensitivity may be separately labeled but is not the primary score. Accounted usage so far is approximately USD 0.13421, excluding unknown unreported failed-call billing.

2026-09-29T07:46:23.513424+00:00: inspected recovery 2, 8818 journaled requests. Additional known choice/probability-argmax inconsistencies: xnli_zh/xnli_zh:3966. Same pinned version and unchanged runner; failed records retained without repair/replay. Continue only unexecuted requests.

2026-09-29T07:47:18.465416+00:00: inspected recovery 3, 9408 journaled requests. Additional known choice/probability-argmax inconsistencies: massive_en/massive_en:1167. Same pinned version and unchanged runner; failed records retained without repair/replay. Continue only unexecuted requests.

2026-09-29T07:50:15.053437+00:00: inspected recovery 4, 11184 journaled requests. Additional known choice/probability-argmax inconsistencies: typed_decisions/typed_decisions:42. Same pinned version and unchanged runner; failed records retained without repair/replay. Continue only unexecuted requests.
