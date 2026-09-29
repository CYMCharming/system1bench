"""Paired, seed-and-truth-cell stratified analysis of frozen wording records."""
import gzip
import json
from pathlib import Path
import sys

import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from system1bench.common import read,sha,write  # noqa: E402

MODELS=['english','multilingual','llama31_8b_instruct','qwen3_8b','jev-1.13.0']
NAMES={'english':'Laya EN','multilingual':'Laya Multi','llama31_8b_instruct':'Llama 3.1 8B',
       'qwen3_8b':'Qwen3 8B','jev-1.13.0':'Jev 1.13'}
CONDITIONS=('en_compact','en_explicit','zh_compact','zh_explicit')


def record_path(root,model):
    if model=='jev-1.13.0':return root/'api'/model/'routing_wording.json.gz'
    return root/'results'/model/'routing_wording.json.gz'


def load_rows(root,model,frozen):
    path=record_path(root,model)
    meta=read(path.parent/'metadata.json')
    assert meta['status']=='DONE' and meta['suites']['routing_wording']['sha256']==sha(path)
    payload=json.loads(gzip.decompress(path.read_bytes()))
    assert payload['signature']['frozen_sha256']==sha(root/'frozen.json')
    expected={c['id']:c for c in frozen['suites'][0]['cases']}
    rows=payload['rows']
    assert len(rows)==384 and len({r['id'] for r in rows})==384
    assert {r['id'] for r in rows}==set(expected)
    output={}
    for row in rows:
        case=expected[row['id']]
        assert row['request_sha256']==case['request_sha256']
        assert row['gold']==case['gold']['action']['label']
        assert row['qid']=='action'
        output.setdefault(case['group'],{})[case['condition']]={
            'correct':int(row['prediction']==row['gold'] and row.get('error') is None),
            'prediction':row['prediction'],'failed':int(row.get('error') is not None),
            'seed':case['generator_seed'],'cell':case['boolean_cell']}
    assert len(output)==96 and all(set(v)==set(CONDITIONS) for v in output.values())
    return output


def effects(groups):
    keys=sorted(groups)
    def selected(cell=None):return [key for key in keys if cell is None or groups[key]['en_compact']['cell'] in cell]
    def vector(ids,left,right):
        return np.asarray([groups[key][right]['correct']-groups[key][left]['correct'] for key in ids],dtype=float)
    specs={
        'en_xor':(selected({'01','10'}),'en_compact','en_explicit'),
        'en_all':(selected(),'en_compact','en_explicit'),
        'zh_xor':(selected({'01','10'}),'zh_compact','zh_explicit'),
    }
    specs['interaction_xor']=(selected({'01','10'}),None,None)
    out={}
    rng=np.random.default_rng(20260929)
    for name,(ids,left,right) in specs.items():
        values=(vector(ids,left,right) if left else
                vector(ids,'en_compact','en_explicit')-vector(ids,'zh_compact','zh_explicit'))
        strata={}
        for j,key in enumerate(ids):
            case=groups[key]['en_compact']
            strata.setdefault((case['seed'],case['cell']),[]).append(j)
        draws=[]
        for _ in range(10000):
            idx=np.concatenate([rng.choice(members,size=len(members),replace=True)
                                for members in strata.values()])
            draws.append(float(values[idx].mean()))
        out[name]={'n':len(ids),'estimate':float(values.mean()),
                   'ci95':[float(x) for x in np.quantile(draws,[.025,.975])],
                   'improved':int((values>0).sum()),'worsened':int((values<0).sum()),
                   'unchanged':int((values==0).sum())}
    return out


def main():
    root=ROOT/'research/wording_v1'
    frozen=read(root/'frozen.json');manifest=read(root/'manifest.json')
    assert sha(root/'frozen.json')==manifest['frozen_sha256']
    result={'protocol':frozen['protocol'],'frozen_sha256':manifest['frozen_sha256'],
            'unit':'96 base-state clusters; 24 per boolean truth-table cell',
            'bootstrap':manifest['uncertainty'],'models':{}}
    for model in MODELS:
        groups=load_rows(root,model,frozen)
        scores={}
        for cell in ['00','01','10','11']:
            ids=[key for key in groups if groups[key]['en_compact']['cell']==cell]
            assert len(ids)==24
            scores[cell]={condition:{'correct':sum(groups[key][condition]['correct'] for key in ids),
                                     'failed':sum(groups[key][condition]['failed'] for key in ids),
                                     'n':24} for condition in CONDITIONS}
        result['models'][model]={'name':NAMES[model],'truth_cells':scores,'effects':effects(groups)}
    write(root/'summary.json',result)
    lines=['# Held-out routing conjunction wording','',
           'Ninety-six unseen base states are balanced across the four `(outage, paying)` truth-table cells; 24 per cell. Each model answers four matched renderings of one action question per state. A service/response failure counts as incorrect. This is a targeted follow-up motivated by an observed error pattern, not a pre-registered test of the original broad language effect.','',
           '| Model | English compact XOR | English explicit XOR | Explicit − compact (pp), paired 95% CI | Improved / worsened |',
           '|---|---:|---:|---:|---:|']
    for model in MODELS:
        d=result['models'][model];cells=d['truth_cells'];e=d['effects']['en_xor']
        a=sum(cells[c]['en_compact']['correct'] for c in ['01','10']);b=sum(cells[c]['en_explicit']['correct'] for c in ['01','10'])
        lines.append(f"| {d['name']} | {a}/48 | {b}/48 | {e['estimate']*100:+.1f} [{e['ci95'][0]*100:+.1f}, {e['ci95'][1]*100:+.1f}] | {e['improved']} / {e['worsened']} |")
    lines += ['','## Complete truth table','',
              'Each cell has 24 base states. Entries are correct counts in compact → explicit conditions; no state is dropped.','',
              '| Model | Cell 00 EN | Cell 01 EN | Cell 10 EN | Cell 11 EN | Cell 00 ZH | Cell 01 ZH | Cell 10 ZH | Cell 11 ZH |',
              '|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    for model in MODELS:
        cells=result['models'][model]['truth_cells'];parts=[]
        for lang in ['en','zh']:
            for cell in ['00','01','10','11']:
                a=cells[cell][lang+'_compact']['correct'];b=cells[cell][lang+'_explicit']['correct']
                parts.append(f'{a} → {b}')
        lines.append('| '+result['models'][model]['name']+' | '+' | '.join(parts)+' |')
    lines += ['','All secondary paired effects, failure counts and per-cell denominators are in [summary.json](summary.json). The frozen protocol is [PROTOCOL.md](PROTOCOL.md). Within-language wording differs only in the first policy clause; Chinese text still needs independent bilingual adjudication.']
    (root/'RESULTS.en.md').write_text('\n'.join(lines)+'\n')
    print('Verified and analyzed',len(MODELS),'systems × 384 decisions')


if __name__=='__main__':main()
