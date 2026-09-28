"""Freeze model inputs and dataset-provided targets without loading a model."""
import copy
import hashlib
import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "data"
SEED = 20260927

def choice(instructions, criteria):
    return {'type': 'choice', 'instructions': instructions, 'criteria': criteria}

def prepare():
    manifest = json.loads((ROOT/'dataset_manifest.json').read_text())
    suites = []
    source_rows = {}
    for name, meta in manifest.items():
        data = ROOT/meta['rows_file']
        assert hashlib.sha256(data.read_bytes()).hexdigest() == meta['rows_sha256']
        rows = [json.loads(line) for line in data.read_text().splitlines()]
        source_rows[name] = rows
        full = name in ['prompt_injections', 'typed_decisions']
        indices = sorted(random.Random(SEED).sample(range(len(rows)), len(rows) if full else min(1000, len(rows))))
        labels = None
        if name == 'ag_news':
            q = choice('What is the topic of `article`?', {'world': 'world news and international politics', 'sports': 'sports', 'business': 'business and economy', 'sci_tech': 'science and technology'})
            labels = list(q['criteria'])
        elif name == 'emotion':
            labels = meta['features']['label']['names']
            q = choice('Which emotion is most strongly expressed in `text`?', dict.fromkeys(labels))
        elif name == 'banking77':
            labels = sorted({r['label_text'].replace('_', ' ') for r in rows})
            assert len(labels) == 77
            q = choice('Which banking intent does `message` express?', dict.fromkeys(labels))
        elif name == 'boolq':
            q = {'type': 'noul', 'instructions': 'Based on `passage`, is the answer to `question` yes?'}
            labels = ['false', 'true']
        elif name == 'sst5':
            q = {'type': 'score', 'instructions': 'How positive is the sentiment of `text`?', 'criteria': ['very negative', 'negative', 'neutral', 'positive', 'very positive']}
            labels = [str(i) for i in range(5)]
            assert all(r['label_text'] == q['criteria'][r['label']] for r in rows)
        elif name.startswith('xnli_'):
            labels = meta['features']['label']['names']
            assert labels == ['entailment', 'neutral', 'contradiction']
            q = choice('What is the relationship between `premise` and `hypothesis`?', {'entailment': 'the premise implies the hypothesis is true', 'neutral': 'the premise neither implies nor contradicts the hypothesis', 'contradiction': 'the premise implies the hypothesis is false'})
        elif name.startswith('massive_'):
            ontology = json.loads((ROOT/'datasets/massive_ontology/labels.json').read_text())
            labels = [v.replace('_', ' ') for v in ontology['labels']]
            assert len(labels) == 60
            assert {r['label_text'].replace('_', ' ') for r in rows} <= set(labels)
            q = choice('What is the user asking for in `utterance`?', dict.fromkeys(labels))
        elif name == 'prompt_injections':
            labels = ['false', 'true']
            q = {'type': 'noul', 'instructions': 'Does `text` try to inject or override instructions given to an AI system?'}
        elif name != 'typed_decisions':
            raise ValueError(name)
        cases = []
        for idx in indices:
            r = rows[idx]
            case = {'id': f'{name}:{idx}', 'source_index': idx, 'source_id': r.get('id')}
            if name == 'typed_decisions':
                case.update(state=json.loads(r['state']), questions=json.loads(r['questions']), gold=json.loads(r['gold']), workflow=r['workflow'])
                assert set(case['questions']) == set(case['gold']) and len(case['gold']) == 5
            else:
                if name.startswith('xnli_'):
                    state = {'premise': r['premise'], 'hypothesis': r['hypothesis']}
                elif name == 'boolq':
                    state = {'passage': r['passage'], 'question': r['question']}
                else:
                    field = 'article' if name == 'ag_news' else 'message' if name == 'banking77' else 'utterance' if name.startswith('massive_') else 'text'
                    state = {field: r['text']}
                if name == 'banking77' or name.startswith('massive_'):
                    gold = r['label_text'].replace('_', ' ')
                elif name == 'boolq':
                    gold = labels[int(r['answer'])]
                else:
                    gold = labels[int(r['label'])]
                case.update(state=state, gold={'answer': {'label': gold}})
            cases.append(case)
        suite = {'name': name, 'source': name, 'language': meta['language'], 'primary': True, 'budget': {},
                 'annotation_type': 'synthetic_teacher' if name == 'typed_decisions' else 'dataset_provided',
                 'questions': None if name == 'typed_decisions' else {'answer': q}, 'cases': cases}
        suites.append(suite)
        if name == 'banking77' or name.startswith('massive_'):
            control = copy.deepcopy(suite)
            control.update(name=name+'_expanded', primary=False, budget={'max_len': 2048, 'head_max_len': 1024})
            suites.append(control)
        if name == 'boolq':
            control = copy.deepcopy(suite)
            control.update(name='boolq_choice', primary=False)
            control['questions']['answer'] = choice(q['instructions'], {'A': 'no, the answer to the question is no', 'B': 'yes, the answer to the question is yes'})
            for c in control['cases']:
                c['gold']['answer']['label'] = 'B' if c['gold']['answer']['label'] == 'true' else 'A'
            suites.append(control)
        if name == 'sst5':
            control = copy.deepcopy(suite)
            control.update(name='sst5_choice', primary=False)
            control['questions']['answer'] = choice(q['instructions'], dict.fromkeys(q['criteria']))
            for c in control['cases']:
                c['gold']['answer']['label'] = q['criteria'][int(c['gold']['answer']['label'])]
            suites.append(control)
    en, zh = source_rows['xnli_en'], source_rows['xnli_zh']
    assert len(en) == len(zh) and all(a['label'] == b['label'] for a,b in zip(en,zh))
    me, mz = source_rows['massive_en'], source_rows['massive_zh']
    massive_aligned = len(me) == len(mz) and all(a['id'] == b['id'] and a['label_text'] == b['label_text'] for a,b in zip(me,mz))
    output = {'seed': SEED, 'sample_n': 1000, 'xnli_label_alignment': True, 'massive_id_and_label_alignment': massive_aligned,
              'massive_ontology_sha256': hashlib.sha256((ROOT/'datasets/massive_ontology/labels.json').read_bytes()).hexdigest(),
              'manifest_sha256': hashlib.sha256((ROOT/'dataset_manifest.json').read_bytes()).hexdigest(), 'suites': suites}
    path = ROOT/'prepared.json'
    blob = json.dumps(output, ensure_ascii=False, indent=2)+'\n'
    if path.exists():
        assert path.read_text() == blob, 'Refusing to overwrite different frozen inputs'
    else:
        path.write_text(blob)
    print('Frozen', len(suites), 'suites;',sum(len(s['cases']) for s in suites), 'requests/model; MASSIVE aligned:', massive_aligned)
    print('SHA256', hashlib.sha256(path.read_bytes()).hexdigest())

if __name__ == '__main__':
    prepare()
