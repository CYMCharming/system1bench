"""Source-separated, paired-cluster metrics, with exact-fraction pilot scoring."""
import argparse
from collections import Counter,defaultdict
import json
import math
from pathlib import Path
import sys
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from system1bench.common import digest,labels,request,sha
from system1bench.decision_models import validate_distribution
from research.startlux_transfer_v1.run import read,save
from research.model_expansion_v1.analyze import analyze as main_metrics

HERE=Path(__file__).resolve().parent
LABELS={'startlux_4b':'StartLux-Decision-4B','startlux_9b':'StartLux-Decision-9B',
 'startlux_27b':'StartLux-Decision-27B','intern_4b':'Intern-Decision-4B','kev_08b':'Kev-0.8B',
 'kev_4b':'Kev-4B','kev_9b':'Kev-9B (earlier release)','kev_27b':'Kev-27B v2',
 'qwen35_08b':'Qwen3.5-0.8B','qwen35_4b':'Qwen3.5-4B','qwen35_9b':'Qwen3.5-9B',
 'qwen38_27b':'Qwen3.8-27B','jev':'Jev 1.13.0 API'}
TASKS=('cladder','cruxeval','finentity','when2call')
PAIRS=(('startlux_4b','qwen35_4b'),('intern_4b','qwen35_4b'),('kev_4b','qwen35_4b'),
       ('startlux_9b','qwen35_9b'),('kev_9b','qwen35_9b'),('startlux_27b','qwen38_27b'),
       ('kev_27b','qwen38_27b'),('kev_08b','qwen35_08b'))

def correct(r): return r['error'] is None and r['prediction']==r['gold']

def interval(values,groups):
    if not values: return None
    buckets=defaultdict(list)
    for v,g in zip(values,groups): buckets[g].append(v)
    stats=np.array([(sum(v),len(v)) for v in buckets.values()],dtype=float)
    sample=np.random.default_rng(20261004).integers(0,len(stats),(2000,len(stats)))
    totals=stats[sample].sum(axis=1)
    return np.quantile(totals[:,0]/totals[:,1],[.025,.975]).tolist()

def rate(rows):
    vals=[int(correct(r)) for r in rows]
    return dict(n=len(rows),correct=sum(vals),score=sum(vals)/len(vals),
                ci95=interval(vals,[r['group'] for r in rows]),errors=sum(r['error'] is not None for r in rows))

def pilot_values(r):
    p,q=r['probabilities'],r['gold_distribution']
    return dict(excess_brier=sum((p[k]-q[k])**2 for k in q),
                expected_brier=1+sum(p[k]**2-2*p[k]*q[k] for k in q),
                total_variation=sum(abs(p[k]-q[k]) for k in q)/2,
                impossible_mass=sum(p[k] for k in q if q[k]==0))

def pilot(rows):
    valid=[r for r in rows if r['error'] is None]
    cells=[pilot_values(r) for r in valid]
    result=dict(n=len(rows),valid=len(valid),errors=len(rows)-len(valid),paired_settings=len({r['group'] for r in rows}))
    for name in ('excess_brier','expected_brier','total_variation','impossible_mass'):
        values=[c[name] for c in cells]
        result[name]=dict(score=float(np.mean(values)) if values else None,
                         ci95=interval(values,[r['group'] for r in valid]))
    return result

def verify(model,panel,manifest,frozen):
    folder=HERE/'results'/panel/model
    meta=read(folder/'metadata.json'); raw=folder/'raw.jsonl'
    assert meta['status']=='DONE' and sha(raw)==meta['raw_sha256']
    accepted={sha(p):read(p) for p in HERE.glob('manifest*.json')}
    assert meta['signature']['manifest_sha256'] in accepted
    run_manifest=accepted[meta['signature']['manifest_sha256']]
    if panel=='transfer':
        assert run_manifest['frozen_sha256']==manifest['frozen_sha256']
        protocols={sha(p) for p in HERE.glob('PROTOCOL*.md')}
        assert run_manifest['protocol_sha256'] in protocols
        if model=='jev': assert run_manifest['protocol_sha256']==manifest['protocol_sha256']
        assert meta['signature']['frozen_sha256']==manifest['frozen_sha256']
    else:
        assert meta['signature']['frozen_sha256']==sha(ROOT/'research/model_expansion_v1/frozen.json')
    adapter_versions=[HERE/'adapter.py',HERE/'adapter.v1.py']
    assert run_manifest['code_sha256']['adapter.py']==meta['signature']['adapter_sha256']
    assert any(sha(p)==meta['signature']['adapter_sha256'] for p in adapter_versions if p.exists())
    runners=[HERE/'run.py',HERE/'run.v1.py',HERE/'run.v2.py',HERE/'run.v3.py',HERE/'run.v4.py']
    assert run_manifest['code_sha256']['run.py']==meta['signature']['runner_sha256']
    assert any(sha(p)==meta['signature']['runner_sha256'] for p in runners if p.exists())
    expected={(s['name'],c['id'],qid):(s,c) for s in frozen['suites'] for c in s['cases'] for qid in c['questions']}
    records=[json.loads(line) for line in raw.read_text(encoding='utf-8').splitlines()]
    seen=set()
    for r in records:
        key=r['suite'],r['id'],r['qid']; assert key in expected and key not in seen
        seen.add(key);s,c=expected[key];q=c['questions'][r['qid']]
        assert digest(request(c))==c['request_sha256']==r['request_sha256']
        assert r['model']==model and r['gold']==str(c['gold'][r['qid']]['label'])
        assert r['labels']==labels(q) and r['group']==c['group']
        assert r['condition']==c['expansion_condition']
        assert r['source_metadata']==c.get('metadata') and r['gold_distribution']==c['gold'][r['qid']].get('distribution')
        if r['error'] is None:
            pred,dist=validate_distribution(q,r['probabilities'])
            assert max(abs(dist[k]-r['probabilities'][k]) for k in dist)<1e-12
            if model=='jev':
                assert r['hosted_evidence']['payload_sha256']==digest(dict(model='jev-1.13.0',**request(c)))
                assert r['prediction']==r['hosted_evidence']['reported_choice']
                assert r['distribution_argmax_prediction']==pred
                assert abs(dist[r['prediction']]-max(dist.values()))<1e-12
                reported=r['hosted_evidence']['reported_probabilities']
                assert abs(sum(reported.values())-1)<=.02
                assert max(abs(dist[k]-reported[k]/sum(reported.values())) for k in dist)<1e-12
            else:
                assert pred==r['prediction']
                assert r['audit']['complete'] and r['audit']['prompt_tokens']<=32768
    assert seen==set(expected) and len(records)==meta['count']==meta['expected']
    assert sum(r['error'] is not None for r in records)==meta['errors']
    return records,dict(raw_sha256=sha(raw),metadata_sha256=sha(folder/'metadata.json'),
                        count=len(records),errors=meta['errors'])

def metrics(rows):
    result={}
    for task in TASKS:
        use=[r for r in rows if r['suite']==task]; bases=[r for r in use if r['condition']=='original']
        pairs=defaultdict(dict)
        for r in use: pairs[r['base_id']][r['condition']]=r
        assert len(pairs)==len(bases) and all(set(p)=={'original','reversed'} for p in pairs.values())
        joint=[int(correct(p['original']) and correct(p['reversed'])) for p in pairs.values()]
        groups=[p['original']['group'] for p in pairs.values()]
        cell=dict(original=rate(bases),reversed=rate([p['reversed'] for p in pairs.values()]),
                  paired_both_correct=dict(n=len(joint),correct=sum(joint),score=sum(joint)/len(joint),ci95=interval(joint,groups)),
                  prediction_flips=sum(p['original']['prediction']!=p['reversed']['prediction'] for p in pairs.values()))
        strata=defaultdict(list)
        for r in bases:
            key=str(r['source_metadata'].get('rung',r['source_metadata'].get('gold_class','all')))
            strata[key].append(r)
        cell['strata']={k:rate(v) for k,v in sorted(strata.items())}
        if task=='cruxeval':
            cell['uniform_choice_chance']=sum(1/len(r['labels']) for r in bases)/len(bases)
            cell['candidate_counts']=dict(Counter(str(len(r['labels'])) for r in bases))
        if task=='when2call':
            direct=sum(r['source_metadata']['option_classes'].get(r['prediction'])=='direct' for r in bases)
            cell['direct_false_selections']=dict(n=len(bases),count=direct,rate=direct/len(bases),gold_positives=0)
        result[task]=cell
    prows=[r for r in rows if r['suite']=='known_distribution']
    result['known_distribution']=pilot(prows)
    uniform=[dict(r,error=None,probabilities={k:1/len(r['labels']) for k in r['labels']}) for r in prows]
    result['known_distribution']['uniform_all_candidates']=pilot(uniform)
    valid=[r for r in prows if r['error'] is None]
    deltas=[pilot_values(r)['excess_brier']-pilot_values(dict(r,probabilities={k:1/len(r['labels']) for k in r['labels']}))['excess_brier'] for r in valid]
    result['known_distribution']['minus_uniform_excess_brier']=dict(n=len(deltas),
        delta=float(np.mean(deltas)),ci95=interval(deltas,[r['group'] for r in valid]))
    result['known_distribution']['categories']={c:pilot([r for r in prows if r['source_metadata']['category']==c])
        for c in sorted({r['source_metadata']['category'] for r in prows})}
    return result

def temperature_sensitivity(rows,model_metadata):
    if 'temperature_by_type' in model_metadata:
        temperature=float(model_metadata['temperature_by_type']['choice'])
    elif 'temperature' in model_metadata:
        temperature=float(model_metadata['temperature'])
    else: return None
    transformed=[]
    for r in rows:
        if r['suite']!='known_distribution':continue
        if r['error'] is not None: transformed.append(r);continue
        logs={k:(temperature*math.log(v) if v>0 else -math.inf) for k,v in r['probabilities'].items()}
        maxlog=max(logs.values());weights={k:math.exp(v-maxlog) for k,v in logs.items()};total=sum(weights.values())
        transformed.append(dict(r,probabilities={k:v/total for k,v in weights.items()}))
    return dict(temperature=temperature,method='recover softmax(logits) from released softmax(logits/T); no fitting; argmax invariant',
                temperature_one=pilot(transformed))

def comparisons(all_rows):
    result={}
    for left,right in PAIRS:
        if left not in all_rows or right not in all_rows: continue
        a={(r['suite'],r['id'],r['qid']):r for r in all_rows[left]}
        b={(r['suite'],r['id'],r['qid']):r for r in all_rows[right]}
        assert set(a)==set(b); cells={}
        for task in TASKS:
            pairs=[(a[k],b[k]) for k in a if k[0]==task and a[k]['condition']=='original']
            vals=[int(correct(x))-int(correct(y)) for x,y in pairs]
            cells[task]=dict(n=len(vals),left_correct=sum(correct(x) for x,y in pairs),
                right_correct=sum(correct(y) for x,y in pairs),delta=sum(vals)/len(vals),
                ci95=interval(vals,[x['group'] for x,y in pairs]))
        pairs=[(a[k],b[k]) for k in a if k[0]=='known_distribution' and a[k]['error'] is None and b[k]['error'] is None]
        for name in ('excess_brier','total_variation','impossible_mass'):
            vals=[pilot_values(x)[name]-pilot_values(y)[name] for x,y in pairs]
            cells['pilot_'+name]=dict(n=len(vals),delta=float(np.mean(vals)),ci95=interval(vals,[x['group'] for x,y in pairs]))
        result[left+'-minus-'+right]=cells
    return result

def report(data):
    rows=['# 新领域迁移与概率表达：固定协议实测','','这是来源分开的诊断面板，不是 Decision Index 官方复现；新任务不会偷偷加入旧综合分。',
          'CLadder 是生成器参考标签；CRUXEval 是历史错误候选构成的选择题；FinEntity 是给定实体情绪分类；When2Call 是工具调用时机的测试选择题。',
          '区间见 JSON：按因果模型、函数、文档、上游工具问题或概率配对设置聚类抽样 2,000 次。小样本、训练史和来源标签质量不由这些区间解决。','',
          '| 模型 | 因果判断 n=144 | 代码输出 n=128 | 金融实体 n=128 | 工具时机 n=128 |',
          '|---|---:|---:|---:|---:|']
    for model in data['cohort']:
        if model not in data['transfer']: continue
        cells=data['transfer'][model]['metrics']
        rows.append('| '+LABELS[model]+' | '+' | '.join(f"{cells[t]['original']['score']:.1%} ({cells[t]['original']['correct']}/{cells[t]['original']['n']})" for t in TASKS)+' |')
    rows+=['','## 换序前后都答对','','| 模型 | 因果判断 | 代码输出 | 金融实体 | 工具时机 |','|---|---:|---:|---:|---:|']
    for m in data['transfer']:
        cells=data['transfer'][m]['metrics']
        rows.append('| '+LABELS[m]+' | '+' | '.join(f"{cells[t]['paired_both_correct']['score']:.1%} ({cells[t]['paired_both_correct']['correct']}/{cells[t]['paired_both_correct']['n']})" for t in TASKS)+' |')
    rows+=['','## 答案是一个概率分布，而不是单个正确选项','','下面越低越好；精确概率题不是采一次随机结果来判对错。96 例只有48个配对设置，且是 Intern 仓库提供的小型诊断集。',
           '| 模型 | 超额 Brier | 总变差 | 不可能结果的概率质量 | 有效/总数 |','|---|---:|---:|---:|---:|']
    for m in sorted(data['transfer'],key=lambda m:data['transfer'][m]['metrics']['known_distribution']['excess_brier']['score'] or 0):
        c=data['transfer'][m]['metrics']['known_distribution']
        rows.append('| '+LABELS[m]+f" | {c['excess_brier']['score']:.4f} | {c['total_variation']['score']:.4f} | {c['impossible_mass']['score']:.2%} | {c['valid']}/{c['n']} |")
    if data['transfer']:
        ref=next(iter(data['transfer'].values()))['metrics']['known_distribution']['uniform_all_candidates']
        rows+=['',f"一个完全不读题、只对所有列出选项均分概率的基线：超额 Brier {ref['excess_brier']['score']:.4f}、总变差 {ref['total_variation']['score']:.4f}。它用于解释额外信息增益，不作为参赛模型。与基线的逐题配对差及无拟合温度1敏感性见 JSON。",'']
    rows+=['','## 解释边界','','这些概率指标检验默认候选分布能否直接用作随机事件的概率，不等于证明某模型不会做概率推理。各原生接口的概率含义、发布温度与训练目标不同；显式概率输出和语义对齐控制仍需另做。',
           'StartLux 官方声明训练过包括 ContractNLI 在内的14个 Decision Index 训练子集。旧法律成绩必须带这个标记；新来源没在声明列表中，并不等于已证明无污染。',
           'Intern 使用官方 HF 后端和在 XTuner 上拟合的发布温度，未在本测试拟合。LLM 是直接候选接口、不开思考；不同训练史不能当成干净的架构对照。',
           'When2Call 没有直接回答的正例；代码输出选择的随机猜测率随候选数变化。逐类别、因果层级、错误率、配对差值和完整来源哈希均见 [summary.json](summary.json)、[source_quality.json](source_quality.json) 与 [PROTOCOL.md](PROTOCOL.md)。','']
    return '\n'.join(rows)

def main():
    p=argparse.ArgumentParser();p.add_argument('--partial',action='store_true');a=p.parse_args()
    manifest=read(HERE/'manifest.json'); frozen=read(ROOT/'data/startlux_transfer_v1/frozen.json')
    assert sha(ROOT/'data/startlux_transfer_v1/frozen.json')==manifest['frozen_sha256']
    data=dict(protocol='startlux-transfer-v1',manifest_sha256=sha(HERE/'manifest.json'),analyzer_sha256=sha(__file__),
              cohort=manifest['cohort'],transfer={},main={},paired_comparisons={},complete=False)
    all_rows={}
    for model in manifest['cohort']:
        path=HERE/'results/transfer'/model/'metadata.json'
        if not path.exists() or read(path)['status']!='DONE':
            if a.partial: continue
            raise ValueError('Incomplete: '+model)
        rows,receipt=verify(model,'transfer',manifest,frozen)
        all_rows[model]=rows
        data['transfer'][model]=dict(receipt=receipt,metrics=metrics(rows))
        metadata=read(HERE/'results/transfer'/model/'metadata.json')
        sensitivity=temperature_sensitivity(rows,metadata['signature']['model'])
        if sensitivity is not None: data['transfer'][model]['temperature_sensitivity']=sensitivity
    old=ROOT/'research/model_expansion_v1/frozen.json'
    for model in manifest['model_pins']:
        path=HERE/'results/main'/model/'metadata.json'
        if not path.exists() or read(path)['status']!='DONE':
            if a.partial: continue
            raise ValueError('Incomplete main: '+model)
        rows,receipt=verify(model,'main',manifest,read(old))
        data['main'][model]=dict(receipt=receipt,panels=main_metrics(rows))
    data['paired_comparisons']=comparisons(all_rows)
    data['complete']=len(data['transfer'])==13 and len(data['main'])==4
    save(HERE/('preview.json' if a.partial else 'summary.json'),data)
    if not a.partial: (HERE/'RESULTS.zh-CN.md').write_text(report(data),encoding='utf-8')
    print('ANALYZED',len(data['transfer']),len(data['main']),'complete',data['complete'])

if __name__=='__main__': main()
