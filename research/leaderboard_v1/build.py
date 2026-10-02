"""Build a public, auditable ten-model leaderboard from same-payload runs."""
from collections import defaultdict
import csv
import gzip
import hashlib
import json
from pathlib import Path

import numpy as np

ROOT=Path(__file__).resolve().parents[2]
HERE=ROOT/'research/leaderboard_v1'
EXP=ROOT/'research/model_expansion_v1'
OLD=['english','multilingual','llama31_8b_instruct','qwen3_8b','jev-1.13.0']
NEW=['kev_08b','kev_4b','kev_9b','nanojev','qwen35_9b']
MODELS=OLD+NEW
LABELS={'english':'Laya English','multilingual':'Laya Multilingual',
        'llama31_8b_instruct':'Llama-3.1-8B','qwen3_8b':'Qwen3-8B',
        'jev-1.13.0':'Jev 1.13.0 API','kev_08b':'Kev-0.8B','kev_4b':'Kev-4B',
        'kev_9b':'Kev-9B','nanojev':'NanoJev','qwen35_9b':'Qwen3.5-9B'}
INTERFACES={m:('direct_llm' if m in ('llama31_8b_instruct','qwen3_8b','qwen35_9b') else 'decision_interface') for m in MODELS}
FAMILIES=('refund','access','routing')
TASKS=('refund/action','access/action','routing/action','contractnli/answer','scifact3/answer')
BOOTSTRAPS,SEED=5000,20261002

def read(path):
    return json.loads(path.read_text(encoding='utf-8'))

def sha(path):
    content=path.read_bytes()
    if path.suffix in {'.md','.py','.json','.jsonl','.csv','.svg','.yml','.yaml'}:
        content=content.replace(b'\r\n',b'\n')
    return hashlib.sha256(content).hexdigest()

def write(path,obj):
    path.write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')

def condition(row,suite):
    if suite.startswith('policy_'):
        declared=row.get('condition',row['id'].rsplit(':',1)[-1])
        return {'original':'base','repeat':'repeat','reversed':'reverse','counterfactual':'counterfactual'}[declared]
    if suite.endswith('_base'):
        return 'base'
    if suite.endswith('_exact_repeat'):
        return 'repeat'
    if suite.endswith('_reversed_option_order'):
        return 'reverse'
    raise ValueError(suite)

def key(row,suite):
    family=row['family']
    pair=row['group'] if suite.startswith('policy_') else row['id']
    return family,pair,row['qid'],condition(row,suite)

def load_rows(history,expansion):
    results={}
    historical_receipts={}
    for model in MODELS:
        rows=[]
        if model in OLD:
            info=history['models'][model]
            assert info['decisions']==4905
            for receipt in info['source_receipts']:
                path=ROOT/receipt['path']
                assert sha(path)==receipt['sha256']
                saved=json.loads(gzip.decompress(path.read_bytes()))
                suite=path.name.removesuffix('.json.gz')
                use=[r for r in saved['rows'] if not suite.startswith('policy_') or
                     r.get('condition',r['id'].rsplit(':',1)[-1]) in
                     {'original','repeat','reversed','counterfactual'}]
                assert len(use)==receipt['matched_decisions']
                rows.extend((suite,r) for r in use)
            historical_receipts[model]=[(x['path'],x['sha256']) for x in info['source_receipts']]
        else:
            folder=EXP/'results'/model
            metadata=read(folder/'metadata.json')
            assert metadata['status']=='DONE' and metadata['errors']==0
            assert sha(folder/'raw.jsonl')==metadata['raw_sha256']==expansion['models'][model]['raw_sha256']
            rows=[(r['suite'],r) for r in map(json.loads,(folder/'raw.jsonl').read_text(encoding='utf-8').splitlines())]
        mapping={}
        for suite,row in rows:
            k=key(row,suite)
            assert k not in mapping and row['error'] is None
            mapping[k]=dict(gold=row['gold'],prediction=row['prediction'],
                request_sha256=row['request_sha256'],group=row['group'],
                id=row['id'],correct=int(row['prediction']==row['gold']))
        assert len(rows)==len(mapping)==4905
        results[model]=mapping
    first=results[MODELS[0]]
    for model,mapping in results.items():
        assert set(mapping)==set(first)
        assert all(mapping[k]['request_sha256']==first[k]['request_sha256'] and
                   mapping[k]['gold']==first[k]['gold'] and
                   mapping[k]['group']==first[k]['group'] for k in first),model
    return results,historical_receipts

def cluster_bootstrap(results):
    first=results[MODELS[0]]
    rng=np.random.default_rng(SEED)
    boot={}
    domains={'refund':'refund','access':'access','routing':'routing',
             'legal':'contractnli','science':'scifact3'}
    for name,family in domains.items():
        pairs=sorted({k[1] for k in first if k[0]==family and k[2]==('action' if name in FAMILIES else 'answer') and k[3]=='base'})
        qid='action' if name in FAMILIES else 'answer'
        assert len(pairs)==(96 if name in FAMILIES else 144 if name=='legal' else 339)
        groups=defaultdict(list)
        for pair in pairs:
            k=family,pair,qid,'base'
            groups[first[k]['group']].append(k)
        group_names=sorted(groups)
        numerator=np.array([[sum(results[model][k]['correct'] for k in groups[g]) for model in MODELS]
                            for g in group_names],dtype=float)
        denominator=np.array([len(groups[g]) for g in group_names],dtype=float)
        draw=rng.integers(0,len(group_names),(BOOTSTRAPS,len(group_names)))
        boot[name]=numerator[draw].sum(axis=1)/denominator[draw].sum(axis=1)[:,None]
    domain_policy=(boot['refund']+boot['access']+boot['routing'])/3
    return (domain_policy+boot['legal']+boot['science'])/3

def cell(correct,n):
    return dict(correct=int(correct),n=int(n),score=float(correct/n))

def rank(scores):
    values=list(scores.values())
    return {m:1+sum(v>scores[m]+1e-12 for v in values) for m in scores}

def format_report(data):
    items=data['models']
    ordered=lambda metric:sorted(MODELS,key=lambda m:(-items[m]['metrics'][metric]['score'],MODELS.index(m)))
    pct=lambda v:f'{100*v:.1f}%'
    def table(metrics,headers):
        rows=['| 排名 | 模型 | '+' | '.join(headers)+' |','|---:|---|'+'|'.join(['---:']*len(metrics))+'|']
        lead=metrics[0]
        for m in ordered(lead):
            cells=[]
            for metric in metrics:
                x=items[m]['metrics'][metric]
                value=pct(x['score'])
                if 'correct' in x:
                    value+=f" ({x['correct']}/{x['n']})"
                cells.append(value)
            rows.append(f"| {data['rankings'][lead][m]} | {items[m]['label']} | "+' | '.join(cells)+' |')
        return '\n'.join(rows)
    leader=ordered('overall_domain_equal')[0]
    other=ordered('overall_task_equal')[0]
    text=['# 十模型排行榜：同一批题目，按领域与决策能力展开','',
        '## 先看综合榜','',
        f"三领域等权指数的样本第 1 名是 **{items[leader]['label']}，{pct(items[leader]['metrics']['overall_domain_equal']['score'])}**；",
        f"若五个任务各给相同权重，第 1 名改为 **{items[other]['label']}，{pct(items[other]['metrics']['overall_task_equal']['score'])}**。",
        '榜首取决于汇总方式，因此综合分只供浏览；具体业务、法律、科学证据应分别选择模型。','',
        '![十模型综合榜和逐任务分数](../../paper/figures/fig_leaderboard_overview.png)','',
        '三个政策领域（退款、权限、分流）的动作各 96 题，先等权平均成“业务规则”；随后业务、法律 144 题、科学 339 题各占综合指数三分之一。每个原始题目的答对为 1、错误为 0；没有用输出概率加权，也没有把同一题的重复和换序当新题。表格顺序按第一分数列排序；同分并列。','',
        table(['overall_domain_equal','policy_action','legal','science'],
              ['三领域等权综合分','业务动作','合同推断','科学证据']),
        '',
        '综合分 95% 区间和全部精确数值见 [scores.json](scores.json)。区间对政策状态、合同文档、科学主张分别配对聚类抽样 5,000 次。前几名的区间有重叠；单一榜单顺序不是模型质量的确定性结论。','',
        '## 换一种综合权重，名次怎么变','',
        '五任务等权的公式为：(退款 + 权限 + 分流 + 法律 + 科学) / 5；主榜则为：[(退款 + 权限 + 分流)/3 + 法律 + 科学] / 3。下表包含十个模型，便于检查权重造成的名次变化。','',
        table(['overall_task_equal','overall_domain_equal'],['五任务等权','三领域等权']),
        '', '## 按领域：业务规则、法律、科学证据','',
        '![按三个领域分别排序](../../paper/figures/fig_leaderboard_domains.png)','',
        '这是三张独立的榜。业务规则的参考答案可由规则程序核验；法律是来源标注一致率；科学的 NOINFO 意味着“引用摘要中无标注证据”，还未逐条得到独立人工确认。它们不能共享同一种“真值质量”。','',
        '## 业务细分：退款、权限、工单分流','',
        table(['refund','access','routing'],['退款动作','权限动作','分流动作']),
        '', '## 同一状态下的三种输出','',
        '以下每项都是三个业务的 288 个原始状态。三项一起正确另列，避免把严重度分对但动作分错算成一个正确系统。','',
        '![动作、复核与严重度排行榜](../../paper/figures/fig_leaderboard_heads.png)','',
        table(['action_head','review_head','severity_head','all_heads'],
              ['动作','需人工复核','严重度','三项同时正确']),
        '', '## 稳定与改判是两种不同能力','',
        '“换序后仍答对”只统计法律与科学中原题、换序题都答对的比例，两领域等权；“事实变后两次都对”只统计三个业务中原题与关键事实改变后的动作都答对的比例，三个业务等权。错误且不改答不算稳定成功。','',
        '![该保持与该改判的两张榜](../../paper/figures/fig_leaderboard_robustness.png)','',
        table(['natural_reversal','policy_counterfactual'],['换序前后都对','关键事实变化前后都对']),
        '', '## 可比性与复查','',
        '十个模型在本图上各对应相同的 4,905 个决策，逐请求摘要和标签均一致。原先五模型的历史运行是复用、并非此轮重新推断；Kev-4B/9B 后续额外做的新种子复测不混入榜单，因为其他八个模型没有在那批题上运行。全部输入与原始输出的逐项哈希见 [历史来源收据](../model_expansion_v1/historical_context.json)、[新增模型收据](../model_expansion_v1/verification.json) 和 [本榜校验](verification.json)。','',
        'LLM 使用固定的直接候选答案接口，Qwen 未开启思考；这里没有检验它们生成式推理的最高成绩。NanoJev 的检查点针对游戏训练；Jev 是在线 API，服务端词元化没有独立复核。不同版本的训练史与推断环境不同，速度和模型参数量不进入榜单。','',
        '下载可编辑数据：[各分类排行榜 CSV](rankings.csv) · [完整数值与置信区间 JSON](scores.json) · [计算规则](PROTOCOL.md)。图为可复现的 PDF/SVG/PNG 矢量与高分辨率版本；这是结果后的描述性组织方式，不是预先注册的获胜标准。','']
    return '\n'.join(text)

def main():
    history=read(EXP/'historical_context.json')
    expansion=read(EXP/'summary.json')
    assert history['model_expansion_manifest_sha256']==expansion['manifest_sha256']
    assert set(history['models'])==set(OLD) and set(expansion['models'])==set(NEW)
    results,receipts=load_rows(history,expansion)
    ci=cluster_bootstrap(results)
    output={'protocol':'system1bench-ten-model-leaderboard-v1',
        'protocol_sha256':sha(HERE/'PROTOCOL.md'),'builder_sha256':sha(Path(__file__)),
        'source_sha256':{'historical_context.json':sha(EXP/'historical_context.json'),
                         'model_expansion_summary.json':sha(EXP/'summary.json'),
                         'model_expansion_verification.json':sha(EXP/'verification.json')},
        'matched_decisions_per_model':4905,'models':{},'rankings':{},
        'bootstrap':dict(resamples=BOOTSTRAPS,seed=SEED,unit='policy state / legal document / science claim',
                         interval='pointwise descriptive paired-cluster 95% percentile'),
        'historical_file_receipts':receipts}
    for index,model in enumerate(MODELS):
        mapping=results[model]
        metrics={}
        def entries(family,qid,cond='base'):
            return [r for k,r in mapping.items() if k[0]==family and k[2]==qid and k[3]==cond]
        for family in FAMILIES:
            metrics[family]=cell(sum(r['correct'] for r in entries(family,'action')),96)
        metrics['policy_action']=cell(sum(metrics[f]['correct'] for f in FAMILIES),288)
        metrics['legal']=cell(sum(r['correct'] for r in entries('contractnli','answer')),144)
        metrics['science']=cell(sum(r['correct'] for r in entries('scifact3','answer')),339)
        for qid,metric in [('action','action_head'),('review','review_head'),('severity','severity_head')]:
            metrics[metric]=cell(sum(sum(r['correct'] for r in entries(f,qid)) for f in FAMILIES),288)
        assert metrics['action_head']==metrics['policy_action']
        triples=[]
        factual=[]
        for family in FAMILIES:
            groups=sorted({k[1] for k in mapping if k[0]==family and k[3]=='base'})
            assert len(groups)==96
            for group in groups:
                triples.append(all(mapping[family,group,q,'base']['correct'] for q in ('action','review','severity')))
                assert mapping[family,group,'action','base']['gold']!=mapping[family,group,'action','counterfactual']['gold']
                factual.append(mapping[family,group,'action','base']['correct'] and
                               mapping[family,group,'action','counterfactual']['correct'])
        metrics['all_heads']=cell(sum(triples),288)
        metrics['policy_counterfactual']=cell(sum(factual),288)
        stable=[]
        for family in ('contractnli','scifact3'):
            groups=sorted({k[1] for k in mapping if k[0]==family and k[3]=='base'})
            n=144 if family=='contractnli' else 339
            assert len(groups)==n
            correct=sum(mapping[family,g,'answer','base']['correct'] and
                        mapping[family,g,'answer','reverse']['correct'] for g in groups)
            stable.append(cell(correct,n))
        metrics['natural_reversal']=dict(score=sum(x['score'] for x in stable)/2,
            components=dict(legal=stable[0],science=stable[1]))
        metrics['overall_domain_equal']=dict(score=(metrics['policy_action']['score']+
            metrics['legal']['score']+metrics['science']['score'])/3,
            ci95=np.quantile(ci[:,index],[.025,.975]).tolist())
        metrics['overall_task_equal']=dict(score=sum(metrics[t]['score'] for t in
            ('refund','access','routing','legal','science'))/5)
        output['models'][model]=dict(label=LABELS[model],interface=INTERFACES[model],
            origin='historical_reused' if model in OLD else 'new_measured',
            decisions=4905,errors=0,metrics=metrics)
    for metric in output['models'][MODELS[0]]['metrics']:
        output['rankings'][metric]=rank({m:output['models'][m]['metrics'][metric]['score'] for m in MODELS})
    write(HERE/'scores.json',output)
    with (HERE/'rankings.csv').open('w',encoding='utf-8',newline='') as f:
        columns=['metric','rank','model','label','interface','score_pct','correct','n','ci95_low_pct','ci95_high_pct']
        writer=csv.DictWriter(f,fieldnames=columns,lineterminator='\n')
        writer.writeheader()
        for metric,ranks in output['rankings'].items():
            for model in sorted(MODELS,key=lambda m:(ranks[m],MODELS.index(m))):
                x=output['models'][model]['metrics'][metric]
                writer.writerow(dict(metric=metric,rank=ranks[model],model=model,label=LABELS[model],
                    interface=INTERFACES[model],score_pct=f"{100*x['score']:.6f}",
                    correct=x.get('correct',''),n=x.get('n',''),
                    ci95_low_pct=f"{100*x['ci95'][0]:.6f}" if 'ci95' in x else '',
                    ci95_high_pct=f"{100*x['ci95'][1]:.6f}" if 'ci95' in x else ''))
    (HERE/'REPORT.zh-CN.md').write_text(format_report(output),encoding='utf-8')
    print('BUILT',len(MODELS),'models',len(output['rankings']),'leaderboards',flush=True)
    for metric in ('overall_domain_equal','overall_task_equal','policy_action','legal','science',
                   'natural_reversal','policy_counterfactual'):
        sorted_models=sorted(MODELS,key=lambda m:(output['rankings'][metric][m],MODELS.index(m)))
        print(metric,[(m,round(100*output['models'][m]['metrics'][metric]['score'],2)) for m in sorted_models[:3]],flush=True)

if __name__=='__main__':
    main()
