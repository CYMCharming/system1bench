"""Aggregate paper-only corpus statistics; never change inference or scores.

Run on gpu29 with the existing model-expansion Python environment. Embeddings
run on CPU. Only aggregate statistics and hashed selections leave this script.
"""
import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path

import numpy as np
import torch
from transformers import AutoModel, AutoTokenizer
from huggingface_hub import snapshot_download

SEED = 20261009
MINILM = 'sentence-transformers/all-MiniLM-L6-v2'
MINILM_REVISION = '1110a243fdf4706b3f48f1d95db1a4f5529b4d41'
N_SEMANTIC = 128


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + '\n', encoding='utf-8')


def corpus(root):
    paths = dict(main=root/'research/model_expansion_v1/frozen.json',
                 transfer=root/'data/startlux_transfer_v1/frozen.json',
                 intent=root/'.aris/public_expansion_v1/full.frozen.json')
    tasks = {}
    for suite in read(paths['main'])['suites']:
        name = suite['name']
        if name.startswith('policy_'):
            task = name.removeprefix('policy_')
            cases = [c for c in suite['cases'] if c.get('expansion_condition') == 'original']
            qid = 'action'
        elif name.endswith('_base'):
            task = {'contractnli_base':'legal', 'scifact3_base':'science'}[name]
            cases = suite['cases']
            qid = 'answer'
        else:
            continue
        tasks[task] = [(c, qid) for c in cases]
    for suite in read(paths['transfer'])['suites']:
        if suite['name'] == 'known_distribution':
            continue
        tasks[suite['name']] = [(c, 'decision') for c in suite['cases'] if c['expansion_condition'] == 'original']
    for suite in read(paths['intent'])['suites']:
        tasks[suite['name']] = [(c, 'decision') for c in suite['cases']]
    expected = dict(refund=96, access=96, routing=96, legal=144, science=339,
                    cladder=144, cruxeval=128, finentity=128, when2call=128,
                    clinc150_full=5500, banking77_full=3080)
    assert {k:len(v) for k,v in tasks.items()} == expected
    return tasks, {name:sha(path) for name,path in paths.items()}


def query_text(task, case, qid):
    state = case['state']
    if task.endswith('_full'):
        return state['user_query']
    if task == 'legal':
        return state['hypothesis']
    if task == 'science':
        return state['claim']
    if task == 'when2call':
        return state['user_question']
    if task == 'cladder':
        return case['questions'][qid]['instructions']
    raise KeyError(task)


def embed_complete(texts, tokenizer, model):
    # MiniLM's default sentence-transformers budget is 256. Retain every
    # wordpiece through nonoverlapping chunks, not silent truncation.
    chunks, owners, weights = [], [], []
    lengths = []
    for i, text in enumerate(texts):
        tokens = tokenizer.encode(text, add_special_tokens=False)
        lengths.append(len(tokens))
        for offset in range(0, max(1,len(tokens)), 254):
            part = tokens[offset:offset+254]
            chunks.append([tokenizer.cls_token_id, *part, tokenizer.sep_token_id])
            owners.append(i)
            weights.append(max(1,len(part)))
    results = np.zeros((len(texts),384), dtype=np.float64)
    totals = np.zeros(len(texts))
    with torch.inference_mode():
        for start in range(0,len(chunks),32):
            current = chunks[start:start+32]
            input_ids = torch.full((len(current),max(map(len,current))), tokenizer.pad_token_id, dtype=torch.long)
            attention_mask = torch.zeros_like(input_ids)
            for i, ids in enumerate(current):
                input_ids[i,:len(ids)] = torch.tensor(ids)
                attention_mask[i,:len(ids)] = 1
            batch = dict(input_ids=input_ids, attention_mask=attention_mask)
            hidden = model(**batch).last_hidden_state
            mask = batch['attention_mask'].unsqueeze(-1)
            pooled = (hidden*mask).sum(1)/mask.sum(1).clamp(min=1)
            values = pooled.numpy()
            for j,value in enumerate(values):
                idx = start+j
                results[owners[idx]] += weights[idx]*value
                totals[owners[idx]] += weights[idx]
    results /= totals[:,None]
    results /= np.maximum(np.linalg.norm(results,axis=1,keepdims=True),1e-12)
    assert np.isfinite(results).all()
    return results, lengths, len(chunks)


def greedy_retention(embeddings, threshold):
    keep = []
    for i,row in enumerate(embeddings):
        if not keep or float(np.max(embeddings[keep]@row)) < threshold:
            keep.append(i)
    return keep


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    tasks, inputs = corpus(args.root)
    torch.set_num_threads(4)
    tokenizer_dir = args.root/'.aris/models/expansion_v2/qwen38_27b'
    reference_tokenizer = AutoTokenizer.from_pretrained(tokenizer_dir, local_files_only=True)
    rows = {}
    for task, cases in tasks.items():
        lengths, labels, cardinalities = [], [], []
        for case, qid in cases:
            question = case['questions'][qid]
            # Common reference serialization: target head only, no gold,
            # native chat templates, repeated conditions or server overhead.
            payload = json.dumps(dict(state=case['state'], questions={qid:question}), ensure_ascii=False, separators=(',',':'))
            lengths.append(len(reference_tokenizer.encode(payload, add_special_tokens=False)))
            gold = str(case['gold'][qid]['label'])
            # Candidate IDs are blinded independently for each transfer case.
            # Count semantic classes, never positional option_0/option_1 IDs.
            semantic_gold = case.get('metadata',{}).get('gold_class')
            if semantic_gold is None:
                semantic_gold = question['criteria'][gold]
            labels.append(str(semantic_gold))
            cardinalities.append(len(question['criteria']))
        counts = Counter(labels)
        k = cardinalities[0] if len(set(cardinalities)) == 1 else None
        entropy = -sum((n/len(cases))*math.log(n/len(cases)) for n in counts.values())
        rows[task] = dict(n=len(cases), reference_token_lengths=lengths, candidate_count=k,
                          candidate_count_distribution=dict(Counter(cardinalities)),
                          observed_classes=(len(counts) if task != 'cruxeval' else None),
                          gold_class_counts=(dict(counts) if task != 'cruxeval' else None),
                          class_semantics=('case-specific output literals; no shared class-entropy metric' if task == 'cruxeval' else 'semantic gold class, not blinded candidate ID'),
                          normalized_label_entropy=(entropy/math.log(k) if k and task != 'cruxeval' else None))
    print('Reference token lengths complete for 9,879 original requests.', flush=True)
    # A fixed, equal-size query-only sample makes retention less dominated by
    # benchmark size. These statistics never subset the scored evaluation.
    selected_tasks = ['clinc150_full','banking77_full','science','cladder','when2call','legal']
    revision = MINILM_REVISION
    encoder_path = Path(snapshot_download(MINILM, revision=revision,
                        cache_dir=args.root/'.aris/paper_compass_v1/hf',
                        allow_patterns=['config.json','model.safetensors','tokenizer.json',
                                        'tokenizer_config.json','vocab.txt','special_tokens_map.json']))
    tokenizer = AutoTokenizer.from_pretrained(encoder_path, local_files_only=True)
    model = AutoModel.from_pretrained(encoder_path, local_files_only=True).eval().cpu()
    semantic = {}
    similarities = {}
    for task in selected_tasks:
        selected = sorted(tasks[task], key=lambda item: hashlib.sha256(f'{SEED}:{task}:{item[0]["id"]}'.encode()).hexdigest())[:N_SEMANTIC]
        texts = [query_text(task,c,qid) for c,qid in selected]
        embeddings, lengths, chunks = embed_complete(texts,tokenizer,model)
        retained = {str(threshold):len(greedy_retention(embeddings,threshold)) for threshold in (.75,.8,.85)}
        similarities[task] = embeddings@embeddings.T
        semantic[task] = dict(n=N_SEMANTIC, retained=retained, maximum_wordpieces=max(lengths), chunks=chunks,
                              selected_id_sha256=hashlib.sha256(json.dumps([c['id'] for c,_ in selected]).encode()).hexdigest(),
                              selection='SHA256(seed:task:id) ascending; seed=20261009')
        print(task, retained, flush=True)
    similarity_path=args.output.with_name('query_similarity.npz')
    similarity_path.parent.mkdir(parents=True,exist_ok=True)
    np.savez_compressed(similarity_path,**similarities)
    output = dict(version=1, collector_sha256=sha(Path(__file__)), source_sha256=inputs, scored_population=9879, tasks=rows,
                  query_similarity=dict(path='query_similarity.npz',sha256=sha(similarity_path),text_included=False),
                  reference_tokenizer=dict(repo='Qwen/Qwen3.8-27B', revision='1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0',
                      files_sha256={name:sha(tokenizer_dir/name) for name in ['tokenizer.json','tokenizer_config.json']},
                      serialization='compact JSON of state plus target question; no gold, chat template or other heads'),
                  semantic_queries=semantic,
                  semantic_encoder=dict(repo=MINILM, revision=revision, cpu=True, dtype='float32',
                      pooling='attention-mask mean pooling; weighted aggregation of all 254-wordpiece chunks; L2 normalization',
                      files_sha256={p.name:sha(p) for p in encoder_path.iterdir() if p.is_file()},
                      truncation=False, threshold=.8, sensitivity_thresholds=[.75,.8,.85]),
                  caveats=['Semantic retention is an encoder/threshold-dependent query-only proxy, not task difficulty or pretraining-cleanliness.',
                      'Label entropy describes the full frozen reference-label distribution, not model performance.',
                      'Full intent tests; historical tasks are frozen evaluation subsets, not all original corpus rows.'])
    save(args.output,output)
    print('Saved aggregate-only paper statistics.',flush=True)


if __name__ == '__main__':
    main()
