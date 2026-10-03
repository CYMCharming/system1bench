"""Same source-aware metrics as v1, with new matched-size Kev/Qwen contrasts."""

import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from system1bench.common import read, sha, write
from research.model_expansion_v1.analyze import (
    analyze, case_key, compare_models, correct, cross_head_patterns, norm_condition,
)

HERE = ROOT / 'research/model_expansion_v2'
OLD = ROOT / 'research/model_expansion_v1'
NEW_MODELS = ('kev_27b', 'qwen35_08b', 'qwen35_4b', 'qwen38_27b')
COMPARISONS = (
    ('kev_27b', 'qwen38_27b'),
    ('kev_08b', 'qwen35_08b'),
    ('kev_4b', 'qwen35_4b'),
    ('kev_9b', 'qwen35_9b'),
)
LABELS = {
    'kev_27b': 'Kev-27B v2',
    'qwen38_27b': 'Qwen3.8-27B',
    'qwen35_08b': 'Qwen3.5-0.8B',
    'qwen35_4b': 'Qwen3.5-4B',
    'kev_08b': 'Kev-0.8B',
    'kev_4b': 'Kev-4B',
    'kev_9b': 'Kev-9B (earlier pinned release)',
    'qwen35_9b': 'Qwen3.5-9B',
}
TASKS = ('refund/action', 'access/action', 'routing/action',
         'contractnli/answer', 'scifact3/answer')


def rows(model):
    directory = HERE if model in NEW_MODELS else OLD
    path = directory / 'results' / model / 'raw.jsonl'
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines()]


def complementary_base(left_rows, right_rows):
    """Count paired base outcomes; oracle figures are upper bounds, not routers."""
    def index(records):
        return {(row['family'] + '/' + row['qid'], case_key(row)): row
                for row in records if norm_condition(row) == 'base'}
    left, right = index(left_rows), index(right_rows)
    assert set(left) == set(right)
    output = {}
    for task in TASKS:
        matched = [(left[key], right[key]) for key in left if key[0] == task]
        assert len(matched) == (96 if task.split('/')[0] in ('refund', 'access', 'routing')
                                else 144 if task.startswith('contractnli') else 339)
        assert all(a['request_sha256'] == b['request_sha256'] and a['gold'] == b['gold']
                   for a, b in matched)
        both = sum(correct(a) and correct(b) for a, b in matched)
        left_only = sum(correct(a) and not correct(b) for a, b in matched)
        right_only = sum(correct(b) and not correct(a) for a, b in matched)
        neither = len(matched) - both - left_only - right_only
        output[task] = dict(n=len(matched), both_correct=both,
                            kev_only=left_only, qwen_only=right_only,
                            neither_correct=neither,
                            oracle_upper_bound=1 - neither / len(matched))
    return output


def report(summary):
    cells = summary['models']
    lines = [
        '# Kev-27B 与 Qwen 官方模型：同题实测', '',
        '每个新模型都完成与上一轮完全相同的 4,905 个决策；它们不是 4,905 道独立题。'
        '下表列出原题正确率和整数分子/分母。法律与科学是来源标注一致率，业务动作可由规则程序校验。', '',
        '| 模型 | 退款动作 | 权限动作 | 分流动作 | 合同推断 | 科学证据 |',
        '|---|---:|---:|---:|---:|---:|',
    ]
    for model in (*NEW_MODELS, 'kev_08b', 'kev_4b', 'kev_9b', 'qwen35_9b'):
        panel = cells[model]['panels']
        values = [panel[key]['base'] for key in TASKS]
        lines.append('| ' + LABELS[model] + ' | ' + ' | '.join(
            f"{item['accuracy']:.1%} ({item['correct']}/{item['n']})" for item in values) + ' |')
    lines += ['',
              '## 同尺寸直接决策比较', '',
        '下表的百分比点差值均为 Kev 减 Qwen，正值表示该 Kev 检查点在本批题上更高；'
              '它不能单独证明架构或微调的因果效果。', '',
              '| 对照 | 业务动作差值 | 合同差值 | 科学差值 |',
              '|---|---:|---:|---:|']
    for kev, qwen in COMPARISONS:
        comparisons = summary['paired_model_comparisons'][kev + '-minus-' + qwen]
        policy = sum(comparisons[f'{family}/action']['base']['delta'] for family in ('refund', 'access', 'routing')) / 3
        legal = comparisons['contractnli/answer']['base']['delta']
        science = comparisons['scifact3/answer']['base']['delta']
        lines.append(f'| {LABELS[kev]} − {LABELS[qwen]} | {100*policy:+.1f} pp | '
                     f'{100*legal:+.1f} pp | {100*science:+.1f} pp |')
    lines += ['', '### 27B 同基座对照的逐任务配对区间', '',
              '这里的 95% 区间按政策状态、合同文档或科学主张聚类自助抽样，逐项描述，不做多重比较校正。'
              '百分比点差值和区间不构成训练方法的因果证明。', '',
              '| 原题任务 | Kev − Qwen 差值 | 95% 配对区间（百分点） |',
              '|---|---:|---:|']
    for task in TASKS:
        cell = summary['paired_model_comparisons']['kev_27b-minus-qwen38_27b'][task]['base']
        low, high = cell.get('document_cluster_ci', cell['ci'])
        lines.append(f"| {task} | {100 * cell['delta']:+.1f} pp | "
                     f"[{100 * low:+.1f}, {100 * high:+.1f}] |")
    lines += ['',
              '## 两模型答案的互补性：仅供设计路由实验', '',
              '下表只针对 27B 同基座对照，列出原题中谁答对。最后一列是假设事后总能选对模型的**神谕上界**，'
              '并非已实现的自动路由性能。要证明实际收益，必须训练并在新题上测试独立选择器。', '',
              '| 任务 | 两者都对 | 仅 Kev 对 | 仅 Qwen 对 | 两者都错 | 神谕上界 |',
              '|---|---:|---:|---:|---:|---:|']
    for task in TASKS:
        cell = summary['complementarity']['kev_27b-minus-qwen38_27b'][task]
        lines.append(f"| {task} | {cell['both_correct']}/{cell['n']} | "
                     f"{cell['kev_only']}/{cell['n']} | {cell['qwen_only']}/{cell['n']} | "
                     f"{cell['neither_correct']}/{cell['n']} | {cell['oracle_upper_bound']:.1%} |")
    lines += ['',
              '27B 这对共享 Qwen3.8 的已后训练基座；较小的 Kev 起点则是 Qwen3.5-Base，'
              '表中的 Qwen 是后训练模型。Kev-9B 为此前固定的旧版本，不代表新发布的 Kev 1.0 版。'
              '各模型训练史不同，不能把上表当作严谨的参数规模效应。', '',
              '## 保持正确与及时改判', '',
              '换序指标要求原题与换序题都答对；事实变化指标要求原题与关键事实改写后的动作都答对。'
              '只算答案不变会奖励“稳定地答错”，因此不能替代这两种联合正确率。', '',
              '| 模型 | 法律换序两次都对 | 科学换序两次都对 | 三业务事实变化两次都对 |',
              '|---|---:|---:|---:|']
    for model in NEW_MODELS:
        panel = cells[model]['panels']
        legal = panel['contractnli/answer']['reverse']
        science = panel['scifact3/answer']['reverse']
        joint = sum(panel[f'{family}/action']['counterfactual']['both_reference_correct']['count']
                    for family in ('refund', 'access', 'routing'))
        lines.append(f"| {LABELS[model]} | {legal['correct_stable']['count']}/144 | "
                     f"{science['correct_stable']['count']}/339 | {joint}/288 |")
    lines += ['',
              '完整逐类别、置信区间、校准与风险/覆盖率数据见 [summary.json](summary.json)。'
              '生成式推理上限、训练污染风险与科学 NOINFO 参考标签质量尚未解决；'
              '概率指标仅在相同语义的接口内部解释。', '',
              '官方模型和固定版本、输入哈希及计算协议见 [manifest.json](manifest.json) 与 [PROTOCOL.md](PROTOCOL.md)。'
              '权重和受许可限制的源文本未进入仓库。', '']
    return '\n'.join(lines)


def main():
    manifest = read(HERE / 'manifest.json')
    assert sha(OLD / 'frozen.json') == manifest['prepared_sha256']
    all_rows = {}
    models = {}
    for model in (*NEW_MODELS, 'kev_08b', 'kev_4b', 'kev_9b', 'qwen35_9b'):
        directory = HERE if model in NEW_MODELS else OLD
        raw_path = directory / 'results' / model / 'raw.jsonl'
        metadata_path = raw_path.parent / 'metadata.json'
        metadata = read(metadata_path)
        assert metadata['status'] == 'DONE' and metadata['errors'] == 0
        assert sha(raw_path) == metadata['raw_sha256']
        all_rows[model] = rows(model)
        assert len(all_rows[model]) == 4905
        models[model] = dict(origin='new_measured' if model in NEW_MODELS else 'historical_reused',
                             raw_sha256=sha(raw_path), metadata_sha256=sha(metadata_path),
                             panels=analyze(all_rows[model]),
                             exploratory_cross_head=cross_head_patterns(all_rows[model]))
    comparisons = {kev + '-minus-' + qwen: compare_models(all_rows, qwen, kev)
                   for kev, qwen in COMPARISONS}
    complementarity = {kev + '-minus-' + qwen: complementary_base(all_rows[kev], all_rows[qwen])
                       for kev, qwen in COMPARISONS}
    summary = dict(protocol=manifest['protocol'], manifest_sha256=sha(HERE / 'manifest.json'),
                   analyzer_sha256=sha(Path(__file__)),
                   shared_analyzer_sha256=sha(OLD / 'analyze.py'),
                   models=models, paired_model_comparisons=comparisons,
                   complementarity=complementarity)
    write(HERE / 'summary.json', summary)
    (HERE / 'RESULTS.zh-CN.md').write_text(report(summary), encoding='utf-8')
    print('ANALYZED', len(NEW_MODELS), 'new models and', len(COMPARISONS), 'same-size pairs', flush=True)


if __name__ == '__main__':
    main()
