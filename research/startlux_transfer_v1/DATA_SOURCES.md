# Source attribution, identity and limits

Model/source versions were pinned and the sample frozen before the new inference
runs. `source_quality.json` contains exact download URLs, sizes and SHA-256;
`manifest*.json` bind the evaluation interface versions. Large weights, raw text
corpora, credentials and vendor source checkouts are excluded from Git.

## Model selection

* [StartLux-Decision](https://github.com/StartLuxLabs/StartLux-Decision), commit
  `0e7a2e81b9c92756e26d8edd843a44d50e362669`: official4B/9B/27B models;
  native inference source Apache2.0, weights CC-BY-NC4.0. This research use does
  not imply unrestricted commercial permission. Checkpoints from the official
  [startlux-models collection](https://huggingface.co/startlux-models); full fixed
  model revisions in `manifest.json`. Text track only, not multimodal claims.
* [Intern-Decision](https://github.com/InternLM/Intern-Decision), commit
  `3572c8a68b5df5dafe02d0e093989ba8ec0183bc`, and official
  [Intern-Decision-4B](https://huggingface.co/internlm/Intern-Decision-4B), fixed
  revision `0e5e6aa7d6d750e2b1504ba11a8136cb58aeb3cd`: Apache2.0 source/checkpoint.
  Trained decision marker and native HF scoring retained. Released temperature
 1.9924182353655278 is checkpoint-hash-verified; its fit backend was XTuner.
* Existing Kev/Qwen/Jev controls retain their original fixed versions and
  interfaces. Kev-9B is the earlier release; Qwen3.8-27B is not Qwen3.5-27B.

StartLux's declared training comprises14 Decision Index train sources; our
historical ContractNLI panel therefore has known source-level training exposure.
This is NOT proof of test-split leakage. Conversely, a source absent from that
list is not proven pretraining-clean. No cross-vendor score was copied into ours.

## Dataset adaptation

| Source | Exact public version | License / reference | Included task and caveat |
|---|---|---|---|
| [CLadder](https://github.com/causalNLP/cladder) | `3d2d1169b4b939a09048a6a75956c8972a93cc38` | MIT; generator-derived causal answers |144 questions balanced by3 rungs×2 labels. No source reasoning or latent parameters in prompts. Rounded prose inputs are retained as published. |
| [CRUXEval](https://github.com/facebookresearch/cruxeval) | `190faf16d175b5847b0af05d937872b1fb395942` | MIT; published execution-verified references |128 output-choice cases from570 eligible functions. Distractors are published incorrect CodeLlama7B outputs.230 have no distinct parseable wrong literal. Not native free generation. |
| [FinEntity](https://github.com/yixuantt/FinEntity) | `3b6cedc5485b669c2ed168f1d949f517636eb7b8` | Dataset ODC-BY per its README; source annotations |128 supplied-span classification cases from128 distinct documents.70 invalid spans/labels,2 duplicate and2 conflicting span annotations excluded. No claim of held-out test split or extraction performance. |
| [When2Call](https://huggingface.co/datasets/nvidia/When2Call) | `0582f7749df63a96fdc3070932e83e72396ace53` | CC-BY4.0; synthetic automated labels |128 official test MCQs, one per upstream problem. Three gold classes; direct reply is only a distractor. No end-to-end tool execution. |
| [Intern known-distribution pilot](https://github.com/InternLM/Intern-Decision/tree/3572c8a68b5df5dafe02d0e093989ba8ec0183bc/benchmarks) | Intern source commit above | Apache2.0; exact rational references |All96 cases/48 settings. Small vendor-authored diagnostic, not an independent large calibration corpus. No fit on these cases. |

All transformations, exclusions and original/reversed request fingerprints are
reproducible in `freeze.py`. Only state/questions are forwarded. Gold labels,
strata, original/target tools, references and probability derivations remain
outside inference payloads. The run uses byte-preserved receipts; request hashes
also bind ordered semantic JSON independently of platform line-ending conventions.

## Evaluating the evaluation

The original Boolean adapter expected a full distribution from StartLux while
its official `noul` API returns P(true). Failed main runs are quarantined and
excluded, with their signatures/counts recorded in `harness_correction.json`.
The corrected adapter maps that scalar to false/true. Unaffected complete main
runs retain their measured code/manifests; archives are independently accepted
by the verifier, not relabeled as the corrected code.
The subsequent option-identity amendment blinds candidate IDs independently of
display order: the preliminary CRUX adaptation always named its gold option_0.
All13 transfer models are rerun, not retroactively relabeled. Exact selected
cases, display meanings/order, reference meanings and the probability pilot
are proved unchanged in `identity_audit.json`; preliminary runs remain privately
archived and excluded, with counts/hashes in `option_identity_amendment.json`.
The hosted-format amendment corrects an assumed four-decimal precision: observed
Jev probabilities can be rounded to two decimals. Final hosted cases use the
historical client's0.02 mass tolerance and unit-mass normalization; raw reported
probabilities are retained. A separate diagnostic query is never substituted for
a benchmark answer. The entire hosted panel is rerun after this correction;
`api_format_amendment.json` records the excluded run and diagnostic evidence.
Accuracy uses the official validated reported choice, not an arbitrary new
tie-break on rounded probabilities. The latter is retained as a sensitivity
field; a tied fake response is covered by the end-to-end test. This prevents
output rounding from fabricating apparent option-order sensitivity.
Native inference/inputs/scoring are unchanged. The end-to-end hosted append test
also covers rounded probabilities and preserves their original values.

Intern yes/no is explicitly mapped to our true/false semantics. Six semantic and
integration checks cover these mappings, probability scoring, identity blinding,
payload whitelisting and hosted persistence.

Our source-replay checks validate provenance and calculations, not a new human
adjudication of every label. A good result on these focused samples is not proof
of deployment safety or an architecture's causal advantage.
