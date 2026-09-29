# Post-hoc policy error localization

post-hoc descriptive localization after observing primary results; no new inference or confirmatory inference.

All five models and eight variants are retained in [the machine-readable diagnostic](confirmation_v1/posthoc_diagnostics.json). Below is the Jev routing slice that motivated this inspection. Counts are descriptive and are not independent confirmation of a causal explanation.

| Rendering | outage | paying | N | Correct | Predicted urgent support |
|---|---|---|---:|---:|---:|
| original | False | False | 28 | 28 | 0 |
| original | False | True | 26 | 0 | 26 |
| original | True | False | 18 | 0 | 18 |
| original | True | True | 24 | 24 | 24 |
| chinese | False | False | 28 | 28 | 0 |
| chinese | False | True | 26 | 26 | 0 |
| chinese | True | False | 18 | 18 | 0 |
| chinese | True | True | 24 | 24 | 24 |

The policy requires the conjunction of outage and paying for urgent support. This error concentration motivates testing explicit boolean wording against compact English conjunctions on newly held-out states. The current Chinese condition also changes question and criterion descriptions, so it does not isolate policy wording or language as the cause. No prompt has been revised or rerun on the reported confirmation cases.
