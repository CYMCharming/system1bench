"""Expand immutable v2 only with complete, same-request new model runs."""
import csv
import json
from pathlib import Path
import sys
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from research.leaderboard_v2 import build as old
from research.startlux_transfer_v1 import analyze as transfer
from research.startlux_transfer_v1.run import read,save
from system1bench.common import sha

HERE=Path(__file__).resolve().parent
EXP=ROOT/'research/startlux_transfer_v1'
NEW=tuple(transfer.LABELS)[:4]
MODELS=tuple(old.MODELS)+NEW
LABELS=dict(old.LABELS,**{m:transfer.LABELS[m] for m in NEW})

def model_metrics(mapping):
    def entries(family,qid,cond='base'):
        return [r for k,r in mapping.items() if k[0]==family and k[2]==qid and k[3]==cond]
    metrics={f:old.cell(sum(r['correct'] for r in entries(f,'action')),96) for f in old.FAMILIES}
    metrics['policy_action']=old.cell(sum(metrics[f]['correct'] for f in old.FAMILIES),288)
    metrics['legal']=old.cell(sum(r['correct'] for r in entries('contractnli','answer')),144)
    metrics['science']=old.cell(sum(r['correct'] for r in entries('scifact3','answer')),339)
    for qid,metric in [('action','action_head'),('review','review_head'),('severity','severity_head')]:
        metrics[metric]=old.cell(sum(sum(r['correct'] for r in entries(f,qid)) for f in old.FAMILIES),288)
    triples,factual=[],[]
    for family in old.FAMILIES:
        groups=sorted({k[1] for k in mapping if k[0]==family and k[3]=='base'});assert len(groups)==96
        for g in groups:
            triples.append(all(mapping[family,g,q,'base']['correct'] for q in ('action','review','severity')))
            assert mapping[family,g,'action','base']['gold']!=mapping[family,g,'action','counterfactual']['gold']
            factual.append(mapping[family,g,'action','base']['correct'] and mapping[family,g,'action','counterfactual']['correct'])
    metrics['all_heads']=old.cell(sum(triples),288)
    metrics['policy_counterfactual']=old.cell(sum(factual),288)
    stable=[]
    for family,n in [('contractnli',144),('scifact3',339)]:
        groups={k[1] for k in mapping if k[0]==family and k[3]=='base'};assert len(groups)==n
        count=sum(mapping[family,g,'answer','base']['correct'] and mapping[family,g,'answer','reverse']['correct'] for g in groups)
        stable.append(old.cell(count,n))
    metrics['natural_reversal']=dict(score=sum(x['score'] for x in stable)/2,components=dict(legal=stable[0],science=stable[1]))
    metrics['overall_domain_equal']=dict(score=sum(metrics[t]['score'] for t in ('policy_action','legal','science'))/3)
    metrics['overall_task_equal']=dict(score=sum(metrics[t]['score'] for t in ('refund','access','routing','legal','science'))/5)
    return metrics

def table(data,columns):
    rows=['| 排名 | 模型 | '+' | '.join(title for key,title in columns)+' |','|---:|---|'+'|'.join(['---:']*len(columns))+'|']
    metric=columns[0][0]
    for m in sorted(MODELS,key=lambda m:(data['rankings'][metric][m],MODELS.index(m))):
        cells=[]
        for key,title in columns:
            c=data['models'][m]['metrics'][key]
            cells.append(f"{100*c['score']:.2f}"+(f" ({c['correct']}/{c['n']})" if 'correct' in c else ''))
        rows.append(f"| {data['rankings'][metric][m]} | {LABELS[m]}{' †' if m.startswith('startlux') else ''} | "+' | '.join(cells)+' |')
    return '\n'.join(rows)

def report(data):
    text=['# 十八模型：综合与分类排行榜','','新增 StartLux-Decision-4B/9B/27B 和 Intern-Decision-4B。每个模型对应相同4,905个决策；之前14个模型复用历史实测，未重跑、未改分。',
          '综合分只用于浏览：业务动作、合同推断、科学证据各占三分之一；不加入新任务、速度或置信度。原题、反转题和同题多头不是独立样本。','',
          '![十八模型综合与领域分数](../../paper/figures/fig_leaderboard_v3_overview.png)','',
          '† StartLux 官方声明训练用过 ContractNLI 训练子集，法律分数须带这个已知训练重叠背景；这不等于已证实测试泄漏。科学 NOINFO 是缺少标注证据，未独立逐题确认。',
          '图中区间为5,000次配对聚类自助抽样的95%描述性区间，不能凭区间重叠判断模型差异显著；不同模型训练史也不构成受控架构对照。','',
          table(data,[('overall_domain_equal','综合分 /100'),('policy_action','业务动作 %'),('legal','合同 %'),('science','科学 %')]),'',
          '## 权重敏感性','',table(data,[('overall_task_equal','五任务等权 /100'),('overall_domain_equal','三领域等权 /100')]),'',
          '## 细分任务','','![各领域独立排行榜](../../paper/figures/fig_leaderboard_v3_domains.png)','',table(data,[('refund','退款 %'),('access','权限 %'),('routing','分流 %'),('legal','合同 %'),('science','科学 %')]),'',
          '## 多头决策','',table(data,[('action_head','动作 %'),('review_head','人工复核 %'),('severity_head','严重度 %'),('all_heads','三头同时正确 %')]),'',
          '## 保持正确与及时改判','',table(data,[('natural_reversal','自然任务换序两次都对 %'),('policy_counterfactual','业务事实变化两次都对 %')]),'',
          '换序指标是合同144对与科学339对的领域等权均值；业务事实变化是288个状态的联合正确率。稳定地答错不会获得正确奖励。','',
          '## 新领域另看，概率表达另看','','![四个新领域逐模型成绩](../../paper/figures/fig_transfer_v1_domains.png)',
          '![精确概率诊断](../../paper/figures/fig_transfer_v1_probability.png)','',
          '新面板只有预先固定的13个代表模型，不与18模型主榜混为相同覆盖。细分类、成对换序、精确概率误差及所有分子/分母见 [新面板结果](../startlux_transfer_v1/RESULTS.zh-CN.md)。',
          'Qwen 采用直接候选接口、未开启思考；Intern 使用官方 HF 与已发布温度。共享 GPU 和慢内核回退不支持速度结论。',
          '下载：[完整数值与区间](scores.json) · [逐分类 CSV](rankings.csv) · [协议](PROTOCOL.md) · [原始输入绑定与验证](../startlux_transfer_v1/summary.json)。','']
    text.insert(-1,'另提供正常论文宽度的独立矢量图：[业务](../../paper/figures/fig_leaderboard_v3_paper_policy_action.pdf) · [合同](../../paper/figures/fig_leaderboard_v3_paper_legal.pdf) · [科学](../../paper/figures/fig_leaderboard_v3_paper_science.pdf) · [因果](../../paper/figures/fig_transfer_v1_paper_cladder.pdf) · [代码](../../paper/figures/fig_transfer_v1_paper_cruxeval.pdf) · [金融](../../paper/figures/fig_transfer_v1_paper_finentity.pdf) · [工具](../../paper/figures/fig_transfer_v1_paper_when2call.pdf) · [概率损失](../../paper/figures/fig_transfer_v1_paper_excess_brier.pdf)。')
    text.insert(-1,'探索性研究线索：[行动与停止、事件信念与选择偏好、跨领域能力边界](../startlux_transfer_v1/INSIGHTS.zh-CN.md)。工具时机逐类别图保留所有分子/分母，不能用整体分数替代风险画像。')
    return '\n'.join(text)

def main():
    history=old.read(old.EXP/'historical_context.json');e1=old.read(old.EXP/'summary.json');e2=old.read(old.EXP2/'summary.json')
    results,receipts=old.load_rows(history,e1,e2)
    summary=read(EXP/'summary.json');assert summary['complete']
    first=results[old.MODELS[0]]
    for m in NEW:
        path=EXP/'results/main'/m/'raw.jsonl';meta=read(path.parent/'metadata.json')
        assert meta['status']=='DONE' and meta['errors']==0 and sha(path)==meta['raw_sha256']==summary['main'][m]['receipt']['raw_sha256']
        mapping={}
        for line in path.read_text(encoding='utf-8').splitlines():
            r=json.loads(line);key=old.key(r,r['suite']);assert key not in mapping and r['error'] is None
            mapping[key]=dict(r,correct=int(r['prediction']==r['gold']))
        assert set(mapping)==set(first) and len(mapping)==4905
        assert all(mapping[k]['request_sha256']==first[k]['request_sha256'] and mapping[k]['gold']==first[k]['gold'] and mapping[k]['group']==first[k]['group'] for k in first)
        results[m]=mapping
    old.MODELS=list(MODELS);ci=old.cluster_bootstrap(results)
    data=dict(protocol='eighteen-model-leaderboard-v3',models={},rankings={},matched_decisions_per_model=4905,
              protocol_sha256=sha(HERE/'PROTOCOL.md'),builder_sha256=sha(__file__),historical_file_receipts=receipts,
              transfer_summary_sha256=sha(EXP/'summary.json'),previous_scores_sha256=sha(ROOT/'research/leaderboard_v2/scores.json'),
              bootstrap=dict(draws=5000,seed=20261002,unit='policy state / contract document / science claim'))
    previous=read(ROOT/'research/leaderboard_v2/scores.json')
    for i,m in enumerate(MODELS):
        metrics=model_metrics(results[m]);metrics['overall_domain_equal']['ci95']=np.quantile(ci[:,i],[.025,.975]).tolist()
        if m not in NEW:
            for k,c in metrics.items(): assert abs(c['score']-previous['models'][m]['metrics'][k]['score'])<1e-12
        data['models'][m]=dict(label=LABELS[m],origin='new_measured' if m in NEW else 'historical_reused',metrics=metrics,
                              decisions=4905,errors=0,known_training_overlap='ContractNLI train split declared' if m.startswith('startlux') else 'not established')
    for metric in data['models'][MODELS[0]]['metrics']:
        data['rankings'][metric]=old.rank({m:data['models'][m]['metrics'][metric]['score'] for m in MODELS})
    save(HERE/'scores.json',data)
    with (HERE/'rankings.csv').open('w',encoding='utf-8',newline='') as stream:
        fields=['metric','rank','model','score_pct','correct','n','ci95_low_pct','ci95_high_pct','training_overlap']
        writer=csv.DictWriter(stream,fieldnames=fields);writer.writeheader()
        for metric in data['rankings']:
            for m in sorted(MODELS,key=lambda m:(data['rankings'][metric][m],MODELS.index(m))):
                c=data['models'][m]['metrics'][metric];bounds=c.get('ci95',['',''])
                writer.writerow(dict(metric=metric,rank=data['rankings'][metric][m],model=m,score_pct=100*c['score'],
                    correct=c.get('correct',''),n=c.get('n',''),ci95_low_pct=100*bounds[0] if bounds[0]!='' else '',
                    ci95_high_pct=100*bounds[1] if bounds[1]!='' else '',training_overlap=data['models'][m]['known_training_overlap']))
    (HERE/'REPORT.zh-CN.md').write_text(report(data),encoding='utf-8')
    print('BUILT',len(MODELS),'models',len(data['rankings']),'rankings')

if __name__=='__main__': main()
