# System1Bench leaderboard website

Independent, source-backed static website: overall, domain/task, robustness,
cross-domain, known-probability and same-device latency rankings; dataset taxonomy;
search, family filters, metric selection, model detail and downloadable exact data.
No Elo, missing-score imputation, API credentials or private question corpus.

From this directory:

```
node prepare.mjs
node check.mjs
npm run build
npm run dev
```

`prepare.mjs` exports verified public research artifacts from the repository and
rejects modifications to the previous eighteen-model scores or latency hash/
hardware mismatches. Commit the resulting `data/catalog.json`. Production builds
are self-contained: Vercel only needs this directory, `node build.mjs`, output
`dist`. The preview serves at http://127.0.0.1:4173/.

Quality: 23 distinct models, 4,905 decisions each in the main panel. Transfer:
19 models, 1,152 decisions each. The quality composite uses three domain means,
not 4,905 as an accuracy denominator. Latency coverage is explicitly displayed;
only completed, uncontaminated measurements enter that ranking. Qwen3.5 latency
uses reference kernels in this environment; it does not measure optimized-kernel
limits. Hosted Jev and external hardware figures never enter the A100 ranking.

The DOM unit checks validate each ranking's coverage, direction and filter logic.
They do not replace screenshot inspection or browser interaction tests.
