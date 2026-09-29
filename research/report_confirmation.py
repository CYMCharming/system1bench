"""Render all fresh cells without selecting favorable models or interventions."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NAMES = {'english':'Laya EN', 'multilingual':'Laya Multi', 'llama31_8b_instruct':'Llama 8B',
         'qwen3_8b':'Qwen 8B', 'jev-1.13.0':'Jev 1.13'}


def main():
    d = json.loads((ROOT/'research/confirmation_v1/summary.json').read_text())
    rows = sorted(d['families'], key=lambda r:(r['family'], list(NAMES).index(r['model'])))
    lines = ['# Fresh executable-policy diagnostic', '',
             'These are actual evaluations on a diagnostic frozen before inference. Each of the three policy families contains 96 unique base states, with three generator seeds and eight matched variants. Every model answers 6,912 decisions; each LLM also answers 1,440 codebook-control decisions. The curated policies test explicit rule composition, not real business outcome utility.', '',
             '## Original states and one-field counterfactuals', '',
             'Percent reference accuracy; joint means both the original and counterfactual action are correct. Each row uses 96 paired base-state clusters. Majority is the observed original action-label majority baseline.', '',
             '| Policy | Model | Action | Review | Severity | Majority | Joint action |',
             '|---|---|---:|---:|---:|---:|---:|']
    tex = [r'\subsection{Fresh policy interventions and codebook controls}',
           r'Table~\ref{tab:fresh} reports the original-state accuracies and joint original/counterfactual action success. The fresh diagnostic covers 96 base states per family, with eight matched variants. Figure~\ref{fig:confirmation} retains all six predeclared effects per model and policy, with simultaneous intervals within each six-effect family. The codebook experiment separates display order from answer-code identity for the two LLM adapters.',
           r'\begin{table}[t]', r'\centering\small', r'\begin{tabular}{llrrrrr}', r'\toprule',
           r'Policy & Model & Action & Review & Severity & Majority & Joint \\', r'\midrule']
    for r in rows:
        vals = [r['base'][q]['estimate']*100 for q in ['action','review','severity']]
        vals += [r['base']['action']['majority_reference_baseline']*100, r['counterfactual_joint']['estimate']*100]
        family = r['family'].removeprefix('policy_').title()
        lines.append('| '+family+' | '+NAMES[r['model']]+' | '+' | '.join(f'{v:.1f}' for v in vals)+' |')
        tex.append(family+' & '+NAMES[r['model']]+' & '+' & '.join(f'{v:.1f}' for v in vals)+r' \\')
    tex += [r'\bottomrule', r'\end{tabular}',
            r'\caption{Fresh policy reference accuracy (percent). Joint requires both original and one-field-counterfactual actions to be correct. Majority is the original action-label baseline. All rows have 96 paired base clusters; the complete machine-readable analysis includes pointwise cluster intervals and all reference-label distributions.}', r'\label{tab:fresh}', r'\end{table}']
    lines += ['', '## All predeclared paired effects', '',
              'Units are percentage points. Intervals are simultaneous 95% max-standardized-deviation bootstrap intervals across six effects within each model/policy family, stratified by the three generator seeds, with 10,000 resamples. They do not cover all models/families jointly. A zero-variance flag means the empirical bootstrap is degenerate, not that population invariance is established.', '',
              '| Policy | Model | Effect | Estimate | Simultaneous 95% CI | Zero variance |', '|---|---|---|---:|---|---|']
    for r in rows:
        for e in r['primary_effects']:
            lo,hi = e['simultaneous_ci95']
            lines.append(f'| {r["family"]} | {NAMES[r["model"]]} | {e["name"]} | {100*e["estimate"]:+.1f} | [{100*lo:+.1f}, {100*hi:+.1f}] | {e["zero_empirical_variance"]} |')
    lines += ['', '## Orthogonal LLM codebook controls', '',
              'The baseline prompt matches the ordinary adapter. Display changes preserve semantic code mapping; code changes preserve semantic display order; both reproduces ordinary reversal. These comparisons use a separate inference block. Intervals below are pointwise paired cluster intervals, not the primary simultaneous family.', '',
              '| Policy | Model | Intervention | Prediction flips | 95% CI | Accuracy change (pp) |', '|---|---|---|---:|---|---:|']
    for r in d['codebook']:
        for e in r['contrasts']:
            lo,hi = e['discordance']['ci95']
            lines.append(f'| {r["family"]} | {NAMES[r["model"]]} | {e["mode"]} | {100*e["discordance"]["estimate"]:.1f} | [{100*lo:.1f}, {100*hi:.1f}] | {100*e["paired_accuracy"]["estimate"]:+.1f} |')
    lines += ['', 'The original, repeat, reversal, Chinese, distractor, paraphrase, choice-encoded and counterfactual results for every output primitive, including failure counts, per-seed effects and paired vectors, are retained in [summary.json](confirmation_v1/summary.json).', '',
              'Execution deviation: one Jev refund Chinese request returned HTTP 520. The frozen runner retries selected 5xx codes, whereas the protocol stated 5xx generally; this status received one attempt. Its three decisions remain incorrect in primary results. Refund Chinese-minus-original action correctness is -1/96 (-1.04 pp); the valid-pair sensitivity is 0/95 (0 pp), conditional on a successful response. This is not evidence of a language regression. See [the execution log](JEV_RUN_LOG.md).', '',
              'Protocol and scope: [PROTOCOL.md](confirmation_v1/PROTOCOL.md). Chinese text was authored and has not received independent bilingual human adjudication. Performance is specific to the evaluated adapter; these experiments do not isolate neural architecture.']
    (ROOT/'research/CONFIRMATION_RESULTS.en.md').write_text('\n'.join(lines)+'\n')
    (ROOT/'paper/tables/confirmation_results.tex').write_text('\n'.join(tex)+'\n')
    print('Rendered',len(rows),'fresh model/policy cells')


if __name__ == '__main__':
    main()
