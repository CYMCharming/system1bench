# Controlled local decision performance (v1)

All timings below are new local measurements using the [predeclared protocol](PERFORMANCE_PROTOCOL.md). They compare the stated adapters, not optimized serving engines or architecture-only speed. Jev is excluded from this resident-GPU track; hosted results are reported separately.

The completed matrix contains 67,584 measured logical requests and 98,304 decisions, excluding warm-up. All inputs are complete; failures: 0. There are 11 workloads, four checkpoints, three batch sizes, and eight rounds on the same physical A100 80GB PCIe.

Timing includes uncached prompt encoding and native structured-answer construction, with GPU synchronization. It excludes model loading, the input audit, file I/O, external network/queue time, and post-call validation. Each model used fresh worker processes, fixed CPU affinity/threads and disjoint warm-up inputs. GPU occupancy was monitored; the wider host remained shared.

Cells show the median of eight round statistics and a 95% bootstrap interval over rounds. Intervals describe this fixed workload on this host; eight rounds are too few to certify rare-tail behavior. Reference-agreement intervals measure repeat variation on the same 64 states, not uncertainty over new dataset samples; a zero-width interval does not imply known population accuracy. p95 is descriptive, not a service-level guarantee. All round values, ranges, memory and token counts are in [summary.json](../performance/v1/summary.json).

## Sequential request latency (batch size 1)

A request includes every question in its state. Latency is never divided by the question count.

| Workload | Model | Request p50 ms [95% CI] | Request p95 ms [95% CI] | Reference agreement % [95% CI] |
|---|---|---:|---:|---:|
| ag_news | Laya English | 10.38 [10.29, 18.35] | 14.47 [10.44, 18.86] | 98.44 [98.44, 98.44] |
| boolq | Laya English | 10.30 [10.23, 10.32] | 10.83 [10.82, 10.85] | 87.50 [87.50, 87.50] |
| sst5 | Laya English | 10.27 [10.21, 10.41] | 10.39 [10.34, 10.62] | 25.00 [25.00, 25.00] |
| banking77 | Laya English | 12.66 [12.55, 12.74] | 13.09 [12.98, 13.20] | 51.56 [51.56, 51.56] |
| massive_en | Laya English | 11.44 [11.35, 20.04] | 11.53 [11.39, 20.21] | 54.69 [54.69, 54.69] |
| massive_zh | Laya English | 11.38 [11.34, 11.48] | 11.51 [11.46, 11.58] | 32.81 [32.81, 32.81] |
| clinc150_oos | Laya English | 21.37 [21.29, 21.68] | 21.44 [21.37, 21.76] | 59.38 [59.38, 59.38] |
| jev_laya_triage | Laya English | 13.89 [13.83, 19.89] | 15.72 [15.65, 20.22] | 64.58 [64.58, 64.58] |
| needle_100 | Laya English | 11.96 [11.95, 12.00] | 12.01 [12.00, 12.03] | 63.28 [63.28, 63.28] |
| needle_1000 | Laya English | 34.79 [34.76, 34.83] | 35.25 [35.17, 35.37] | 49.22 [49.22, 49.22] |
| needle_4000 | Laya English | 171.11 [170.28, 171.40] | 171.95 [171.28, 172.42] | 50.78 [50.78, 50.78] |
| ag_news | Laya Multilingual | 8.51 [8.46, 8.94] | 8.63 [8.56, 9.15] | 96.88 [96.88, 96.88] |
| boolq | Laya Multilingual | 8.55 [8.50, 8.71] | 8.86 [8.77, 9.38] | 84.38 [84.38, 84.38] |
| sst5 | Laya Multilingual | 8.47 [8.38, 8.53] | 8.62 [8.51, 8.76] | 20.31 [20.31, 20.31] |
| banking77 | Laya Multilingual | 9.93 [9.81, 10.09] | 10.08 [9.91, 10.18] | 46.88 [46.88, 46.88] |
| massive_en | Laya Multilingual | 9.50 [9.36, 13.45] | 9.59 [9.49, 13.67] | 35.94 [35.94, 35.94] |
| massive_zh | Laya Multilingual | 9.48 [9.34, 17.08] | 9.60 [9.49, 17.39] | 32.81 [32.81, 32.81] |
| clinc150_oos | Laya Multilingual | 13.60 [13.49, 13.77] | 13.76 [13.56, 20.78] | 68.75 [68.75, 68.75] |
| jev_laya_triage | Laya Multilingual | 9.30 [9.27, 9.43] | 9.82 [9.76, 10.05] | 56.25 [56.25, 56.25] |
| needle_100 | Laya Multilingual | 9.08 [9.00, 12.76] | 9.24 [9.09, 13.00] | 60.94 [60.94, 60.94] |
| needle_1000 | Laya Multilingual | 18.30 [18.26, 18.37] | 18.65 [18.61, 18.75] | 42.97 [42.97, 42.97] |
| needle_4000 | Laya Multilingual | 92.94 [92.84, 93.04] | 94.01 [93.58, 94.15] | 46.88 [46.88, 46.88] |
| ag_news | Llama-3.1-8B-Instruct | 30.69 [30.39, 30.78] | 31.52 [31.26, 31.56] | 87.50 [87.50, 87.50] |
| boolq | Llama-3.1-8B-Instruct | 36.86 [36.53, 37.19] | 48.55 [48.32, 49.22] | 64.06 [64.06, 64.06] |
| sst5 | Llama-3.1-8B-Instruct | 29.20 [29.08, 29.31] | 30.75 [30.59, 30.90] | 28.12 [28.12, 28.12] |
| banking77 | Llama-3.1-8B-Instruct | 112.93 [111.15, 113.03] | 114.14 [111.94, 114.43] | 51.56 [51.56, 51.56] |
| massive_en | Llama-3.1-8B-Instruct | 91.18 [90.88, 91.29] | 91.68 [91.48, 91.95] | 54.69 [54.69, 54.69] |
| massive_zh | Llama-3.1-8B-Instruct | 91.15 [90.66, 91.19] | 91.61 [91.31, 91.67] | 46.88 [46.88, 46.88] |
| clinc150_oos | Llama-3.1-8B-Instruct | 201.76 [201.59, 201.94] | 202.84 [202.52, 204.00] | 56.25 [56.25, 56.25] |
| jev_laya_triage | Llama-3.1-8B-Instruct | 100.02 [99.51, 100.78] | 113.98 [113.47, 114.61] | 73.44 [73.44, 73.44] |
| needle_100 | Llama-3.1-8B-Instruct | 69.02 [68.65, 69.14] | 69.35 [68.98, 69.44] | 89.84 [89.84, 89.84] |
| needle_1000 | Llama-3.1-8B-Instruct | 202.67 [202.39, 202.87] | 211.93 [211.38, 212.16] | 75.78 [75.78, 75.78] |
| needle_4000 | Llama-3.1-8B-Instruct | 705.78 [705.57, 706.11] | 707.37 [707.11, 707.87] | 72.66 [72.66, 72.66] |
| ag_news | Qwen3-8B | 30.96 [30.71, 31.02] | 31.97 [31.75, 32.08] | 87.50 [87.50, 87.50] |
| boolq | Qwen3-8B | 33.51 [33.34, 33.71] | 49.01 [48.75, 49.41] | 81.25 [81.25, 81.25] |
| sst5 | Qwen3-8B | 29.27 [29.12, 29.36] | 30.69 [30.49, 30.86] | 39.06 [39.06, 39.06] |
| banking77 | Qwen3-8B | 119.91 [118.15, 120.11] | 120.89 [119.03, 121.36] | 60.94 [60.94, 60.94] |
| massive_en | Qwen3-8B | 96.01 [95.87, 96.06] | 96.68 [96.54, 96.95] | 62.50 [62.50, 62.50] |
| massive_zh | Qwen3-8B | 95.66 [95.44, 95.81] | 96.54 [96.30, 96.69] | 62.50 [62.50, 62.50] |
| clinc150_oos | Qwen3-8B | 214.74 [214.46, 215.18] | 216.06 [215.72, 216.35] | 68.75 [68.75, 68.75] |
| jev_laya_triage | Qwen3-8B | 102.95 [102.66, 103.92] | 115.94 [115.69, 117.02] | 79.17 [79.17, 79.17] |
| needle_100 | Qwen3-8B | 72.63 [72.45, 73.39] | 72.97 [72.90, 73.77] | 88.28 [88.28, 88.28] |
| needle_1000 | Qwen3-8B | 214.47 [213.60, 214.78] | 216.43 [216.14, 216.82] | 87.50 [87.50, 87.50] |
| needle_4000 | Qwen3-8B | 758.71 [757.50, 759.77] | 763.42 [759.92, 764.47] | 88.28 [88.28, 88.28] |

## Fixed-batch throughput (batch size 8)

Throughput is work divided by cumulative synchronized prediction time, excluding validation/file writes. It is not maximum serving capacity under an arrival-rate or tail-latency constraint.

| Workload | Model | Requests/s [95% CI] | Decisions/s [95% CI] | Peak allocated GiB (median) | Reference agreement % |
|---|---|---:|---:|---:|---:|
| ag_news | Laya English | 441.20 [436.82, 444.37] | 441.20 [436.82, 444.37] | 2.31 | 98.44 |
| boolq | Laya English | 257.19 [256.58, 261.75] | 257.19 [256.58, 261.75] | 2.37 | 84.38 |
| sst5 | Laya English | 516.73 [512.80, 520.98] | 516.73 [512.80, 520.98] | 2.31 | 25.00 |
| banking77 | Laya English | 165.13 [134.06, 168.60] | 165.13 [134.06, 168.60] | 2.37 | 51.56 |
| massive_en | Laya English | 225.14 [221.28, 229.00] | 225.14 [221.28, 229.00] | 2.34 | 56.25 |
| massive_zh | Laya English | 223.72 [218.93, 224.30] | 223.72 [218.93, 224.30] | 2.35 | 32.81 |
| clinc150_oos | Laya English | 58.55 [57.44, 58.76] | 58.55 [57.44, 58.76] | 2.58 | 59.38 |
| jev_laya_triage | Laya English | 121.58 [121.06, 122.84] | 364.73 [363.18, 368.51] | 2.48 | 64.58 |
| needle_100 | Laya English | 234.66 [233.99, 235.23] | 469.33 [467.99, 470.46] | 2.35 | 63.28 |
| needle_1000 | Laya English | 39.37 [38.08, 39.49] | 78.74 [76.16, 78.98] | 2.88 | 49.22 |
| needle_4000 | Laya English | 6.57 [6.55, 6.59] | 13.14 [13.10, 13.18] | 5.06 | 50.78 |
| ag_news | Laya Multilingual | 696.15 [690.33, 703.78] | 696.15 [690.33, 703.78] | 1.50 | 96.88 |
| boolq | Laya Multilingual | 448.91 [372.81, 457.76] | 448.91 [372.81, 457.76] | 1.54 | 82.81 |
| sst5 | Laya Multilingual | 746.61 [715.84, 752.40] | 746.61 [715.84, 752.40] | 1.49 | 20.31 |
| banking77 | Laya Multilingual | 265.39 [257.80, 267.94] | 265.39 [257.80, 267.94] | 1.55 | 48.44 |
| massive_en | Laya Multilingual | 357.15 [292.98, 364.11] | 357.15 [292.98, 364.11] | 1.52 | 35.94 |
| massive_zh | Laya Multilingual | 360.41 [248.90, 366.44] | 360.41 [248.90, 366.44] | 1.52 | 32.81 |
| clinc150_oos | Laya Multilingual | 101.92 [100.23, 102.75] | 101.92 [100.23, 102.75] | 1.68 | 68.75 |
| jev_laya_triage | Laya Multilingual | 225.77 [197.01, 228.87] | 677.32 [591.04, 686.62] | 1.61 | 56.25 |
| needle_100 | Laya Multilingual | 404.35 [336.13, 405.09] | 808.70 [672.25, 810.18] | 1.55 | 60.94 |
| needle_1000 | Laya Multilingual | 75.38 [75.24, 75.66] | 150.76 [150.47, 151.32] | 1.91 | 42.97 |
| needle_4000 | Laya Multilingual | 12.50 [12.46, 12.53] | 25.00 [24.92, 25.06] | 3.76 | 46.88 |
| ag_news | Llama-3.1-8B-Instruct | 47.11 [46.67, 47.61] | 47.11 [46.67, 47.61] | 15.20 | 87.50 |
| boolq | Llama-3.1-8B-Instruct | 29.18 [29.00, 29.47] | 29.18 [29.00, 29.47] | 15.46 | 64.06 |
| sst5 | Llama-3.1-8B-Instruct | 54.06 [53.02, 54.85] | 54.06 [53.02, 54.85] | 15.16 | 29.69 |
| banking77 | Llama-3.1-8B-Instruct | 9.00 [8.99, 9.05] | 9.00 [8.99, 9.05] | 16.10 | 50.00 |
| massive_en | Llama-3.1-8B-Instruct | 12.02 [12.02, 12.06] | 12.02 [12.02, 12.06] | 15.82 | 55.47 |
| massive_zh | Llama-3.1-8B-Instruct | 12.02 [12.00, 12.03] | 12.02 [12.00, 12.03] | 15.81 | 48.44 |
| clinc150_oos | Llama-3.1-8B-Instruct | 4.50 [4.50, 4.51] | 4.50 [4.50, 4.51] | 17.06 | 53.91 |
| jev_laya_triage | Llama-3.1-8B-Instruct | 12.58 [12.46, 12.64] | 37.74 [37.37, 37.93] | 15.32 | 71.88 |
| needle_100 | Llama-3.1-8B-Instruct | 20.89 [20.86, 20.94] | 41.78 [41.73, 41.87] | 15.23 | 89.84 |
| needle_1000 | Llama-3.1-8B-Instruct | 4.96 [4.95, 4.96] | 9.92 [9.90, 9.93] | 16.00 | 75.78 |
| needle_4000 | Llama-3.1-8B-Instruct | 1.15 [1.15, 1.15] | 2.30 [2.30, 2.31] | 18.65 | 72.66 |
| ag_news | Qwen3-8B | 46.46 [45.26, 47.51] | 46.46 [45.26, 47.51] | 15.46 | 87.50 |
| boolq | Qwen3-8B | 27.81 [27.55, 28.07] | 27.81 [27.55, 28.07] | 15.70 | 81.25 |
| sst5 | Qwen3-8B | 55.05 [54.60, 56.62] | 55.05 [54.60, 56.62] | 15.43 | 40.62 |
| banking77 | Qwen3-8B | 8.41 [8.41, 8.47] | 8.41 [8.41, 8.47] | 16.27 | 60.94 |
| massive_en | Qwen3-8B | 11.35 [11.31, 11.44] | 11.35 [11.31, 11.44] | 16.01 | 62.50 |
| massive_zh | Qwen3-8B | 11.37 [11.35, 11.39] | 11.37 [11.35, 11.39] | 16.01 | 64.06 |
| clinc150_oos | Qwen3-8B | 4.17 [4.17, 4.18] | 4.17 [4.17, 4.18] | 17.14 | 67.19 |
| jev_laya_triage | Qwen3-8B | 12.08 [11.99, 12.27] | 36.23 [35.98, 36.82] | 15.57 | 79.17 |
| needle_100 | Qwen3-8B | 20.26 [20.23, 20.33] | 40.51 [40.46, 40.66] | 15.49 | 89.06 |
| needle_1000 | Qwen3-8B | 4.65 [4.64, 4.66] | 9.30 [9.27, 9.31] | 16.19 | 88.67 |
| needle_4000 | Qwen3-8B | 1.06 [1.06, 1.06] | 2.12 [2.12, 2.12] | 18.58 | 87.50 |

## Fixed-batch throughput (batch size 32)

Throughput is work divided by cumulative synchronized prediction time, excluding validation/file writes. It is not maximum serving capacity under an arrival-rate or tail-latency constraint.

| Workload | Model | Requests/s [95% CI] | Decisions/s [95% CI] | Peak allocated GiB (median) | Reference agreement % |
|---|---|---:|---:|---:|---:|
| ag_news | Laya English | 573.63 [570.54, 582.44] | 573.63 [570.54, 582.44] | 2.41 | 98.44 |
| boolq | Laya English | 249.67 [248.99, 255.97] | 249.67 [248.99, 255.97] | 2.74 | 85.94 |
| sst5 | Laya English | 805.83 [765.12, 823.88] | 805.83 [765.12, 823.88] | 2.36 | 25.00 |
| banking77 | Laya English | 180.98 [158.88, 185.87] | 180.98 [158.88, 185.87] | 2.70 | 51.56 |
| massive_en | Laya English | 260.98 [205.78, 264.71] | 260.98 [205.78, 264.71] | 2.55 | 56.25 |
| massive_zh | Laya English | 256.27 [249.63, 258.63] | 256.27 [249.63, 258.63] | 2.57 | 32.81 |
| clinc150_oos | Laya English | 61.65 [50.61, 62.48] | 61.65 [50.61, 62.48] | 3.65 | 59.38 |
| jev_laya_triage | Laya English | 124.05 [113.78, 125.68] | 372.15 [341.34, 377.04] | 3.19 | 64.58 |
| needle_100 | Laya English | 269.75 [267.47, 270.78] | 539.50 [534.93, 541.57] | 2.64 | 63.28 |
| needle_1000 | Laya English | 41.13 [41.00, 41.22] | 82.27 [81.99, 82.44] | 4.85 | 49.22 |
| needle_4000 | Laya English | 6.65 [6.63, 6.66] | 13.29 [13.27, 13.32] | 13.58 | 50.78 |
| ag_news | Laya Multilingual | 1037.98 [910.16, 1048.95] | 1037.98 [910.16, 1048.95] | 1.57 | 96.88 |
| boolq | Laya Multilingual | 456.62 [451.39, 482.04] | 456.62 [451.39, 482.04] | 1.81 | 82.81 |
| sst5 | Laya Multilingual | 1305.71 [1286.94, 1318.23] | 1305.71 [1286.94, 1318.23] | 1.54 | 20.31 |
| banking77 | Laya Multilingual | 295.38 [292.77, 300.42] | 295.38 [292.77, 300.42] | 1.77 | 48.44 |
| massive_en | Laya Multilingual | 420.73 [414.38, 432.53] | 420.73 [414.38, 432.53] | 1.66 | 35.94 |
| massive_zh | Laya Multilingual | 424.18 [417.61, 435.98] | 424.18 [417.61, 435.98] | 1.66 | 32.81 |
| clinc150_oos | Laya Multilingual | 109.08 [106.06, 110.01] | 109.08 [106.06, 110.01] | 2.43 | 68.75 |
| jev_laya_triage | Laya Multilingual | 244.28 [241.82, 246.21] | 732.84 [725.47, 738.62] | 2.11 | 56.25 |
| needle_100 | Laya Multilingual | 488.97 [404.88, 493.09] | 977.94 [809.75, 986.17] | 1.74 | 60.94 |
| needle_1000 | Laya Multilingual | 79.72 [79.02, 80.03] | 159.44 [158.04, 160.06] | 3.29 | 42.97 |
| needle_4000 | Laya Multilingual | 12.56 [12.52, 12.57] | 25.11 [25.04, 25.13] | 10.71 | 46.88 |
| ag_news | Llama-3.1-8B-Instruct | 47.07 [46.89, 48.16] | 47.07 [46.89, 48.16] | 15.91 | 87.50 |
| boolq | Llama-3.1-8B-Instruct | 25.18 [25.15, 25.53] | 25.18 [25.15, 25.53] | 16.94 | 64.06 |
| sst5 | Llama-3.1-8B-Instruct | 57.68 [57.50, 58.33] | 57.68 [57.50, 58.33] | 15.74 | 29.69 |
| banking77 | Llama-3.1-8B-Instruct | 9.02 [9.00, 9.03] | 9.02 [9.00, 9.03] | 19.49 | 50.00 |
| massive_en | Llama-3.1-8B-Instruct | 12.25 [12.23, 12.26] | 12.25 [12.23, 12.26] | 18.36 | 54.69 |
| massive_zh | Llama-3.1-8B-Instruct | 12.31 [12.28, 12.32] | 12.31 [12.28, 12.32] | 18.35 | 46.88 |
| clinc150_oos | Llama-3.1-8B-Instruct | 4.52 [4.50, 4.53] | 4.52 [4.50, 4.53] | 23.32 | 54.69 |
| jev_laya_triage | Llama-3.1-8B-Instruct | 12.61 [12.55, 12.67] | 37.84 [37.65, 38.00] | 16.37 | 72.40 |
| needle_100 | Llama-3.1-8B-Instruct | 22.15 [22.14, 22.17] | 44.29 [44.28, 44.34] | 16.02 | 89.84 |
| needle_1000 | Llama-3.1-8B-Instruct | 5.02 [5.00, 5.05] | 10.03 [10.00, 10.10] | 19.11 | 75.78 |
| needle_4000 | Llama-3.1-8B-Instruct | 1.16 [1.16, 1.16] | 2.32 [2.31, 2.32] | 29.69 | 72.66 |
| ag_news | Qwen3-8B | 47.25 [47.13, 47.79] | 47.25 [47.13, 47.79] | 16.06 | 87.50 |
| boolq | Qwen3-8B | 23.78 [23.69, 23.89] | 23.78 [23.69, 23.89] | 17.00 | 81.25 |
| sst5 | Qwen3-8B | 56.30 [56.12, 57.19] | 56.30 [56.12, 57.19] | 15.91 | 40.62 |
| banking77 | Qwen3-8B | 8.44 [8.43, 8.46] | 8.44 [8.43, 8.46] | 19.27 | 60.94 |
| massive_en | Qwen3-8B | 11.60 [11.58, 11.60] | 11.60 [11.58, 11.60] | 18.25 | 62.50 |
| massive_zh | Qwen3-8B | 11.64 [11.63, 11.67] | 11.64 [11.63, 11.67] | 18.23 | 64.06 |
| clinc150_oos | Qwen3-8B | 4.21 [4.21, 4.23] | 4.21 [4.21, 4.23] | 22.75 | 67.19 |
| jev_laya_triage | Qwen3-8B | 12.39 [12.35, 12.46] | 37.18 [37.06, 37.38] | 16.47 | 78.91 |
| needle_100 | Qwen3-8B | 21.75 [21.72, 21.78] | 43.50 [43.44, 43.56] | 16.17 | 88.28 |
| needle_1000 | Qwen3-8B | 4.69 [4.69, 4.70] | 9.38 [9.38, 9.40] | 18.98 | 89.06 |
| needle_4000 | Qwen3-8B | 1.07 [1.07, 1.07] | 2.14 [2.14, 2.14] | 28.52 | 87.50 |

## Hardware observations

These telemetry ranges span the monitored block, including input audit, warm-up, idle gaps and measurement. They are not active-kernel-only clock or power summaries. Raw phase labels and monotonic call boundaries support finer inspection. The observer ran on CPU 24, separately from worker cores 20–23 and their SMT siblings 84–87; no block may pass with an observed foreign GPU process or a sustained CPU/SMT threshold violation. Brief interference and shared memory-bandwidth effects remain possible.

| Model | GPU telemetry samples | Foreign GPU process observations | SM clock MHz min–max | Temperature C min–max | Host 1-minute load min–max |
|---|---:|---:|---:|---:|---:|
| Laya English | 867 | 0 | 1155–1410 | 29–60 | 4.65–9.47 |
| Laya Multilingual | 617 | 0 | 1200–1410 | 43–58 | 4.71–9.09 |
| Llama-3.1-8B-Instruct | 4434 | 0 | 930–1410 | 37–64 | 4.60–12.14 |
| Qwen3-8B | 4728 | 0 | 930–1410 | 39–64 | 4.76–9.36 |

## Interpretation and limits

- Compare quality and speed within each workload. Reference agreement on a fixed 64-state subset is not a new overall accuracy leaderboard.
- Source annotation caveats remain: synthetic workflow scores are teacher agreement. The original full v0.2 accuracy results are unchanged.
- Shared-host CPU/memory contention, unlocked device clocks and finite telemetry sampling remain limitations despite observed GPU isolation and fixed CPU affinity.
- Prompt lengths differ between tokenizers. All models receive the same semantic request; this is not identical FLOPs or token counts.
- The LLM baseline performs direct next-token candidate scoring without generated reasoning. It is not vLLM, TensorRT-LLM, or a best-possible serving implementation.
- No generated tokens/s, TTFT/TPOT, p99 certification, network latency, concurrency scaling, or MLPerf compliance is claimed.
- No best-run selection or cross-task blended speed winner is reported. Full raw rounds, input IDs, telemetry, code/model hashes and failed-run policy support reproducibility.

Instrumentation is confined to [performance.py](../benchmarks/performance.py), [performance_report.py](../benchmarks/performance_report.py), their tests, and the performance output directory. Existing accuracy adapters and results were not modified.
