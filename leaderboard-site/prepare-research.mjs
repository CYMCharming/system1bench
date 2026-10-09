// Export only reviewed, aggregate paper-figure evidence. No private questions.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import assert from 'node:assert/strict';
import {fileURLToPath} from 'node:url';
const here=path.dirname(fileURLToPath(import.meta.url)),root=path.dirname(here);
const read=p=>JSON.parse(fs.readFileSync(path.join(root,p),'utf8'));
const hash=p=>crypto.createHash('sha256').update(fs.readFileSync(path.join(root,p))).digest('hex');
const source='research/paper_compass_v1/',stats=read(source+'corpus_statistics.json'),manifest=read(source+'figure_manifest.json');
const catalog=read('leaderboard-site/data/catalog.json');
for(const[p,h]of Object.entries(manifest.source_sha256))assert.equal(hash(p==='corpus_statistics.json'?source+p:p),h);
for(const[p,h]of Object.entries(manifest.outputs))assert.equal(hash(p),h);
assert.equal(stats.scored_population,9879);assert.equal(catalog.comprehensive.complete_models,17);
const repo='https://github.com/CYMCharming/system1bench/blob/main/';
const asset=p=>'/assets/paper/'+path.basename(p);
const assets=stem=>Object.fromEntries(['svg','pdf','png'].map(ext=>[ext,asset(stem+'.'+ext)]));
const meta=(id,letter,kicker,title,stem,group)=>({id,letter,kicker,title,group,assets:assets(stem),source:repo+source+'figure_manifest.json'});
const number=v=>(v*100).toFixed(2)+'%';
const domainKeys=['policy','legal','science','causal','code','finance','tools','intent'];
const domainTitles=['政策','法律','科学','因果','代码','金融','工具','意图'];
const name={clinc150_full:'CLINC150 + OOS',banking77_full:'BANKING77',science:'SciFact',cladder:'CLadder',when2call:'When2Call',legal:'ContractNLI'};
const queryOrder=manifest.derived.c_semantic_query_diversity;
const figures=[{
 ...meta('profiles','a','DOMAIN PROFILES','模型的八领域成绩','a_radial_decision_profiles','models'),
 description:'六个代表模型在相同的八个领域上的成绩。每个扇区均使用 0–100% 尺度；精确表格保留全部 17 个完整模型。',
 caveat:'综合榜按八领域等权，不按样本量加权。这是当前评测的点估计，尚无新版综合分置信区间；六个代表模型不构成独立排行榜。',
 definition:'图中只画六个代表模型，表中展示全部完整模型。领域成绩与综合榜 catalog.json 完全一致；政策内三个任务、意图内两个任务分别等权。总体综合分是八领域成绩的平均值。',
 alt:'六个代表模型的八领域径向分组柱图，各扇区使用相同零起点准确率尺度。精确数值可在下方展开。',
 columns:['模型',...domainTitles,'领域等权综合分'],
 rows:Object.values(catalog.comprehensive.models).sort((a,b)=>b.metrics.overall_domain_equal.score-a.metrics.overall_domain_equal.score).map(m=>[m.label.replace(/ \(Unsloth BF16 distribution\)/,''),...domainKeys.map(k=>number(m.domain_scores[k].score)),number(m.metrics.overall_domain_equal.score)])
},{
 ...meta('lengths','b','INPUT STRUCTURE','评测输入有多长','b_input_length_distribution','data'),
 description:'政策、证据与推理、意图识别三组输入的长度分布。包含候选选项，排除重复题、换序题与其他输出字段。',
 caveat:'统一用 Qwen3.8-27B 的参考 tokenizer 计数，不是各模型的原生 token 费用或延迟。每组曲线单独归一化，曲线面积不表示该组样本量。',
 definition:'9,879 条原始样本。将 state 与目标 question 序列化为紧凑 JSON，排除 gold、聊天模板和其他字段头。横轴为对数 token 长度；密度采用固定带宽，不移除已评分输入。',
 alt:'三组评测输入在对数 token 长度轴上的密度曲线：政策、证据与推理、意图识别。各组样本量和中位数列于表格。',
 columns:['输入组','原始样本数','中位 token 数','最短','最长'],
 rows:manifest.derived.b_input_length_distribution.map((g,i)=>[['政策','证据与推理','意图识别'][i],g.n,g.median,g.min,g.max])
},{
 ...meta('queries','c','QUERY TEXT','问题文本去重保留率','c_semantic_query_diversity','data'),
 description:'每个任务抽取 128 条查询文本，进行语义去重。这里只比较问题的问法，不比较合同、证据或整道题的多样性。',
 caveat:'ContractNLI 的 10.2% = 13 / 128：固定命题用于不同合同，问法重复而证据不同。不是模型准确率，也不是数据集质量评分。细线为阈值敏感性范围，不是置信区间。',
 definition:'MiniLM 语义编码器；哈希确定性抽样；余弦相似度阈值 0.80 的贪心去重。保留率 = 保留条数 / 128。0.75 与 0.85 仅检验阈值敏感性。不使用合同正文等证据；各任务的查询粒度也不同。',
 alt:'六个任务的问题文本去重保留率。ContractNLI 保留 13/128，即 10.2%，统计不包含合同正文，也不表示模型正确率。',
 columns:['任务','抽样查询数','阈值 0.80 保留数','保留率','阈值 0.75 保留数','阈值 0.85 保留数'],
 rows:queryOrder.map(k=>{const q=stats.semantic_queries[k];return [name[k],q.n,q.retained['0.8'],(q.retained['0.8']/q.n*100).toFixed(1)+'%',q.retained['0.75'],q.retained['0.85']];})
},{
 ...meta('labels','d','REFERENCE LABELS','标准答案的类别分布','d_reference_label_balance','data'),
 description:'衡量冻结评测集的标准答案是否集中在少数类别。这里比较的是参考标签，不是模型的预测分布。',
 caveat:'均衡度不是准确率。When2Call 有 4 个候选类别，但当前 128 条冻结样本只出现其中 3 类；CLINC 的 1,000 条域外请求使其不完全均衡。',
 definition:'均衡度 = 标准答案的 Shannon 熵 / log(完整类别数)，显示为百分比；包含未出现的合法类别。按语义标签统计，不把每题换过的选项 ID 当成固定类别。100% 表示所有类别数量相同。',
 alt:'六个数据集的标准答案类别均衡度，使用归一化标签熵；不是模型分数。样本数、候选类别数与实际出现类别数可查。',
 columns:['任务','完整冻结样本数','候选类别数','出现类别数','标签均衡度'],
 rows:queryOrder.map(k=>{const t=stats.tasks[k];return [name[k],t.n,t.candidate_count,t.observed_classes,(t.normalized_label_entropy*100).toFixed(1)+'%'];})
},{
 ...meta('taxonomy','e','EVALUATION MAP','评测任务与诊断指标','e_evaluation_taxonomy','data'),
 description:'分类任务与独立诊断分开组织：综合榜只用分类准确率，稳健性、概率误差和速度另行展示。',
 caveat:'扇区宽度按任务或指标个数绘制，不代表样本占比、领域权重或模型覆盖。分类任务由 17 个完整模型覆盖，诊断项的覆盖范围以各自榜单为准。',
 definition:'分类分支：八领域、11 个分类任务。诊断分支：11 个叶节点。图中分类与诊断各占半圈，仅为层级结构呈现；综合榜依然按八个分类领域等权。',
 alt:'同心层级图，将八领域的 11 个分类任务与稳健性、概率和速度等独立诊断指标分开。角度不表示样本量或评分权重。',
 columns:['分支','领域 / 诊断组','叶节点数量','内容'],
 rows:[['分类','政策',3,'退款、访问控制、工单分流'],['分类','法律',1,'ContractNLI'],['分类','科学',1,'SciFact'],['分类','因果',1,'CLadder'],['分类','代码',1,'CRUXEval'],['分类','金融',1,'FinEntity'],['分类','工具',1,'When2Call'],['分类','意图',2,'CLINC150 + OOS、BANKING77'],['诊断','不变性',3,'重复、选项换序、改写'],['诊断','响应性',1,'关键事实反转'],['诊断','联合决策',1,'全部字段正确'],['诊断','概率误差',3,'Brier、NLL、TV'],['诊断','效率',3,'P50、P95、吞吐量']]
}];
for(const f of figures)f.asset_sha256=Object.fromEntries(Object.entries(f.assets).map(([ext,url])=>[ext,hash('paper/figures/compass_v1/'+path.basename(url))]));
assert.equal(figures[0].rows.length,17);
assert.equal(figures[2].rows.find(r=>r[0]==='ContractNLI')[3],'10.2%');
const data={version:1,modelCount:17,domainCount:8,taskCount:11,population:stats.scored_population,
 book:asset('System1Bench_Compass_Figures.pdf'),protocol:repo+source+'README.zh-CN.md',reference:manifest.design_reference,
 source:{figure_manifest_sha256:hash(source+'figure_manifest.json'),statistics_sha256:hash(source+'corpus_statistics.json'),catalog_source_sha256:manifest.source_sha256['research/evaluation_completion_v1/results.json'],semantic_encoder:stats.semantic_encoder,reference_tokenizer:stats.reference_tokenizer},figures};
assert(!/hf_[A-Za-z0-9]{25,}|apikey_[A-Za-z0-9_]+/.test(JSON.stringify(data)));
fs.mkdirSync(path.join(here,'assets/paper'),{recursive:true});
for(const p of Object.keys(manifest.outputs))fs.copyFileSync(path.join(root,p),path.join(here,'assets/paper',path.basename(p)));
fs.copyFileSync(path.join(root,source+'domain_scores.csv'),path.join(here,'assets/paper/domain_scores.csv'));
fs.writeFileSync(path.join(here,'data/research.json'),JSON.stringify(data,null,2)+'\n');
console.log('Prepared 5 source-verified research figures, 17 model rows and exact dataset statistics.');
