# Eighteen-model descriptive leaderboard v3

Keep v1/v2 unchanged. Add StartLux-Decision4B/9B/27B and Intern-Decision4B only
after all4,905 main decisions are complete and individually verified. Reuse
the same historical14 runs, domain weights, condition definitions and 5,000
paired-cluster bootstrap draws (seed20261002). No new tasks enter this index.
Require identical semantic keys, gold labels, request hashes and source clusters
across all18 models. Training overlap and heterogeneous reference validity
are visible caveats, not corrected by confidence intervals.

Overall descriptive index = [policy action mean + legal agreement + science
agreement]/3. Policy action mean pools288 equally weighted originals across
refund/access/routing; legal144; science339. Five-task weight sensitivity also
reported. All-three-head, head-specific, policy counterfactual and natural
reversal rankings retain their established denominators. Rank exact ties equally.
StartLux declares ContractNLI train-split use; add a visible flag to its rows.
Qwen is constrained direct inference, no thinking. Intern is native HF with
published XTuner-fit temperature, no fit on our test. Latency never enters ranking.

Publish source/task/head/count tables and separate transfer/pilot figures.
Those extra samples do not establish native Decision Index scores, broad agent
competence, clean architecture/scale effects or uncontaminated test performance.
