"""Deterministic, gold-whitelisted source adaptation; no inference involved."""
import ast
from collections import Counter, defaultdict
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import random
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from system1bench.common import digest, request, sha

HERE = Path(__file__).resolve().parent
DATA = ROOT / 'data/startlux_transfer_v1'
RAW = DATA / 'raw'
SEED = 20261004
PINS = {
 'startlux_4b': {'repo':'startlux-models/StartLux-Decision-4B','revision':'9302aedb7f7bd889994336f2ae919dffbf5dbee1'},
 'startlux_9b': {'repo':'startlux-models/StartLux-Decision-9B','revision':'342aad64840be8eee314455428a5a775f18ef547'},
 'startlux_27b': {'repo':'startlux-models/StartLux-Decision-27B','revision':'95e31cda814fec2a7dc4ac4f8b9b832aa1c9c2e6'},
 'intern_4b': {'repo':'internlm/Intern-Decision-4B','revision':'0e5e6aa7d6d750e2b1504ba11a8136cb58aeb3cd'},
}
COHORT = [*PINS, 'kev_08b','kev_4b','kev_9b','kev_27b','qwen35_08b','qwen35_4b','qwen35_9b','qwen38_27b','jev']

def load(name):
    return json.loads((RAW / name).read_text(encoding='utf-8'))

def lines(name):
    return [json.loads(line) for line in (RAW / name).read_text(encoding='utf-8').splitlines()]

def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)+'\n', encoding='utf-8')

def priority(case):
    return hashlib.sha256(f"{SEED}:{case['id']}".encode()).hexdigest()

def select(candidates, quotas, distinct=False):
    result, used, counts = [], set(), Counter()
    for case in sorted(candidates, key=priority):
        cell = case['stratum']
        if counts[cell] >= quotas[cell] or (distinct and case['group'] in used):
            continue
        result.append(case)
        counts[cell] += 1
        used.add(case['group'])
    assert dict(counts) == quotas, (counts, quotas)
    return sorted(result, key=lambda c:c['id'])

def make(source, sid, group, state, instructions, options, gold, stratum, **meta):
    entries = list(options.items())
    random.Random(f'{SEED}:{source}:{sid}').shuffle(entries)
    return dict(id=f'{source}/{sid}',group=str(group),source=source,stratum=stratum,
                state=state,questions={'decision':dict(type='choice',instructions=instructions,criteria=dict(entries))},
                gold={'decision':{'label':gold}},metadata=meta)

def main():
    receipt = load('source_receipt.json')
    # Every downloaded file is byte-bound to the immutable source receipt.
    for name, item in receipt.items():
        assert sha(RAW/name) == item['sha256']
    reports, suites = {}, []
    z = zipfile.ZipFile(RAW/'cladder.zip')
    models = {m['model_id']:m for m in json.loads(z.read('cladder-v1-meta-models.json'))}
    causal = []
    for q in json.loads(z.read('cladder-v1-q-balanced.json')):
        meta=q['meta']; rung=meta['rung']; answer=q['answer']
        assert answer in {'yes','no'} and rung in {1,2,3}
        causal.append(make('cladder',q['question_id'],meta['model_id'],
            {'background':models[meta['model_id']]['background'],'given_information':q['given_info']},
            q['question'],{'option_0':'Yes','option_1':'No'},'option_0' if answer=='yes' else 'option_1',
            f'{rung}:{answer}',rung=rung,query_type=meta['query_type'],story=meta['story_id'],gold_class=answer))
    chosen=select(causal,{f'{r}:{a}':24 for r in (1,2,3) for a in ('yes','no')})
    suites.append(dict(name='cladder',domain='causal_reasoning',cases=chosen))
    reports['cladder']=dict(source_count=len(causal),selected=len(chosen),strata=dict(Counter(c['stratum'] for c in chosen)))
    crux, excluded=[],Counter()
    generations, flags=load('crux_generations.json'),load('crux_flags.json')['raw_scored_generations']
    for q in lines('cruxeval.jsonl'):
        try:
            correct=ast.literal_eval(q['output'])
        except (ValueError,SyntaxError):
            excluded['unparseable_gold']+=1; continue
        values=[correct]; display=[repr(correct)]
        if q['id'] not in generations:
            excluded['no_published_distractors']+=1; continue
        assert len(generations[q['id']])==len(flags[q['id']])
        for text, ok in zip(generations[q['id']],flags[q['id']]):
            if ok: continue
            try: value=ast.literal_eval(text)
            except (ValueError,SyntaxError): continue
            if any(value==x for x in values): continue
            values.append(value); display.append(repr(value))
            if len(values)==10: break
        if len(values)<2:
            excluded['no_distinct_literal_distractor']+=1; continue
        crux.append(make('cruxeval',q['id'],q['id'],{'code':q['code'],'input_arguments':q['input']},
            'What is the return value of f called with the stated input arguments? Select the exact Python output.',
            {f'option_{i}':v for i,v in enumerate(display)},'option_0','all',candidate_count=len(values)))
    chosen=select(crux,{'all':128})
    suites.append(dict(name='cruxeval',domain='code_execution_choice',cases=chosen))
    reports['cruxeval']=dict(source_count=800,eligible=len(crux),excluded=dict(excluded),selected=128,
                            candidate_counts=dict(Counter(str(len(c['questions']['decision']['criteria'])) for c in chosen)))
    fin, issues=[],Counter()
    for doc in load('finentity.json'):
        text=doc['content']; group=hashlib.sha256(text.encode()).hexdigest()
        spans=defaultdict(set)
        for a in doc['annotations']: spans[(a['start'],a['end'])].add(a['tag'])
        seen=set()
        for a in doc['annotations']:
            span=(a['start'],a['end'])
            if len(spans[span])!=1: issues['conflicting_span']+=1; continue
            if span in seen: issues['duplicate_span']+=1; continue
            seen.add(span)
            if text[a['start']:a['end']]!=a['value'] or a['tag']!=a['label']:
                issues['invalid_span_or_label']+=1; continue
            assert a['tag'] in {'Negative','Neutral','Positive'}
            fin.append(make('finentity',f"{group}:{a['start']}:{a['end']}",group,
                {'document':text,'entity':a['value'],'span_start':a['start'],'span_end':a['end']},
                'Classify the financial sentiment toward the supplied entity in this document, not the overall tone.',
                {'option_0':'Negative','option_1':'Neutral','option_2':'Positive'},
                {'Negative':'option_0','Neutral':'option_1','Positive':'option_2'}[a['tag']],a['tag'],gold_class=a['tag']))
    chosen=select(fin,{'Negative':43,'Neutral':42,'Positive':43},distinct=True)
    suites.append(dict(name='finentity',domain='financial_entity_sentiment',cases=chosen))
    reports['finentity']=dict(documents=len(load('finentity.json')),eligible=len(fin),issues=dict(issues),selected=128,
                             distinct_documents=len({c['group'] for c in chosen}))
    when=[]
    for q in lines('when2call.jsonl'):
        assert set(q['answers'])=={'direct','tool_call','request_for_info','cannot_answer'}
        keys=list(q['answers']); target=q['correct_answer']; assert target in keys
        group=f"{q['source']}:{q['source_id'].split('-')[0]}"
        when.append(make('when2call',q['uuid'],group,{'tools':[json.loads(t) for t in q['tools']],'user_question':q['question']},
            'Given only the available tools and the user request, choose the most appropriate next assistant response.',
            {f'option_{i}':q['answers'][k] for i,k in enumerate(keys)},f'option_{keys.index(target)}',target,
            gold_class=target,option_classes={f'option_{i}':k for i,k in enumerate(keys)},upstream_source=q['source']))
    chosen=select(when,{'tool_call':43,'cannot_answer':43,'request_for_info':42},distinct=True)
    suites.append(dict(name='when2call',domain='tool_use_timing',cases=chosen))
    reports['when2call']=dict(source_count=len(when),source_gold_classes=dict(Counter(c['stratum'] for c in when)),
                             selected=128,distinct_problem_groups=len({c['group'] for c in chosen}))
    for suite in suites:
        originals=suite['cases']; suite['source']=suite['name']; expanded=[]
        for case in originals:
            for condition in ('original','reversed'):
                c=json.loads(json.dumps(case)); c['base_id']=c['id']; c['id']+='/'+condition
                c['expansion_condition']=condition; c['family']=suite['domain']
                if condition=='reversed':
                    c['questions']['decision']['criteria']=dict(reversed(list(c['questions']['decision']['criteria'].items())))
                c['request_sha256']=digest(request(c)); expanded.append(c)
        suite['cases']=expanded
    refs={q['id']:q for q in lines('pilot_references.jsonl')}; pilot=[]
    for q in lines('pilot_inputs.jsonl'):
        ref=refs[q['id']]; gold={k:float(Fraction(v)) for k,v in ref['gold_fractions'].items()}
        assert sum(Fraction(v) for v in ref['gold_fractions'].values())==1
        assert all(abs(gold[k]-ref['gold_probs'][k])<1e-12 for k in gold)
        assert set(gold)==set(q['questions'][ref['field']]['criteria'])
        c=dict(q,group=ref['group'],base_id=q['id'],expansion_condition=ref['variant'],family=ref['family'],
               gold={ref['field']:{'label':max(gold,key=gold.get),'distribution':gold}},
               metadata={k:ref[k] for k in ('category','family','difficulty')})
        c['request_sha256']=digest(request(c)); pilot.append(c)
    assert len(pilot)==96 and len({c['group'] for c in pilot})==48
    suites.append(dict(name='known_distribution',source='intern_pilot96',domain='probability_reasoning',cases=pilot))
    frozen={'suites':suites}; assert sum(len(c['questions']) for s in suites for c in s['cases'])==1152
    save(DATA/'frozen.json',frozen)
    save(HERE/'source_quality.json',dict(seed=SEED,sources=receipt,reports=reports,pilot=dict(cases=96,paired_settings=48),
        coverage='Focused samples/adaptations; not native benchmark reproduction',
        training_overlap='StartLux declares ContractNLI train usage; absence from declared list does not establish contamination-free data.'))
    manifest=dict(seed=SEED,expected_decisions=1152,frozen_sha256=sha(DATA/'frozen.json'),
                  protocol_sha256=sha(HERE/'PROTOCOL.md'),freeze_sha256=sha(__file__),model_pins=PINS,cohort=COHORT,
                  code_sha256={p:sha(HERE/p) for p in ('adapter.py','run.py')},source_quality_sha256=sha(HERE/'source_quality.json'))
    save(HERE/'manifest.json',manifest)
    print(json.dumps(dict(decisions=1152,reports=reports),ensure_ascii=False))

if __name__=='__main__': main()
