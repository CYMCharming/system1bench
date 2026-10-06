# System1Bench leaderboard website

Independent, source-backed static website: overall, domain/task, robustness,
cross-domain, known-probability and same-device latency rankings; dataset taxonomy;
search, family filters, metric selection, model detail and downloadable exact data.
No Elo, missing-score imputation, API credentials or private question corpus.

The default view is a linked visual leaderboard: zero-based horizontal ranking
bars with available 95% intervals, a fixed-scale domain/task heatmap, and a
quality–latency scatter for the fourteen models with both measurements. Forest,
indigo and amber distinguish decision, general and representation models. Show
the first six or expand the complete filtered cohort; switch to **精确数据** for
the original score table. Keyboard and pointer interactions reveal exact values
and open model details. Responsive charts retain readable model names and units.

Chart geometry and table rows use the same frozen `catalog.json`; no scores were
changed for visualization. Missing latency is omitted, not set to zero. Scatter
coordinates join historical main-panel quality with separately measured latency,
not the same run, and are not evidence of architectural causality. Heatmap legal
cells flag StartLux's declared ContractNLI training exposure. Speed intervals are
round-mean intervals, not confidence intervals for P95.

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

The DOM unit checks validate each ranking's coverage, direction, filter logic,
zero-origin mark geometry, exact source coordinates and responsive SVG output.
They do not replace screenshot inspection or browser interaction tests.
