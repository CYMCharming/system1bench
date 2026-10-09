"""Independently check displayed figure data and exported artifact bindings."""
import csv
import hashlib
import json
import math
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    stats=read(HERE/'corpus_statistics.json')
    manifest=read(HERE/'figure_manifest.json')
    score_path=ROOT/'research/evaluation_completion_v1/results.json'
    results=read(score_path)
    assert manifest['source_sha256']['corpus_statistics.json']==sha(HERE/'corpus_statistics.json')
    assert manifest['source_sha256']['research/evaluation_completion_v1/results.json']==sha(score_path)
    assert stats['source_sha256']['main']==read(ROOT/'research/model_expansion_v1/manifest.json')['prepared_sha256']
    expected=read(ROOT/'research/evaluation_completion_v1/manifest.json')['inputs']
    assert stats['source_sha256']['intent']==expected['intent']['sha256']
    assert stats['source_sha256']['transfer']==expected['transfer']['sha256']
    assert sum(row['n'] for row in stats['tasks'].values())==9879
    for task,row in stats['tasks'].items():
        assert len(row['reference_token_lengths'])==row['n']
        assert all(isinstance(n,int) and n>0 for n in row['reference_token_lengths'])
        assert sum(row['candidate_count_distribution'].values())==row['n']
        if row['normalized_label_entropy'] is not None:
            counts=row['gold_class_counts']
            assert sum(counts.values())==row['n']
            independently_computed=-sum((n/row['n'])*math.log(n/row['n']) for n in counts.values())/math.log(row['candidate_count'])
            assert abs(independently_computed-row['normalized_label_entropy'])<1e-12
    assert stats['tasks']['when2call']['gold_class_counts']=={'tool_call':43,'cannot_answer':43,'request_for_info':42}
    assert stats['tasks']['when2call']['observed_classes']==3
    assert stats['tasks']['cladder']['gold_class_counts']=={'no':72,'yes':72}
    assert stats['tasks']['cruxeval']['normalized_label_entropy'] is None
    for row in stats['semantic_queries'].values():
        assert row['n']==128
        assert all(0<n<=128 for n in row['retained'].values())
        assert row['maximum_wordpieces']>=1 and len(row['selected_id_sha256'])==64
    assert len(stats['semantic_encoder']['revision'])==40
    assert stats['semantic_encoder']['truncation'] is False
    assert stats['collector_sha256']==sha(HERE/'collect.py')
    similarity_path=HERE/stats['query_similarity']['path']
    assert sha(similarity_path)==stats['query_similarity']['sha256']
    with np.load(similarity_path,allow_pickle=False) as pairwise:
        assert set(pairwise.files)==set(stats['semantic_queries'])
        for task,row in stats['semantic_queries'].items():
            matrix=pairwise[task]
            assert matrix.shape==(128,128) and np.isfinite(matrix).all()
            assert np.allclose(matrix,matrix.T,atol=1e-10)
            assert np.allclose(np.diag(matrix),1,atol=1e-10)
            for threshold,count in row['retained'].items():
                retained=[]
                for index in range(128):
                    if not retained or matrix[index,retained].max()<float(threshold):
                        retained.append(index)
                assert len(retained)==count
    with (HERE/'domain_scores.csv').open(encoding='utf-8',newline='') as stream:
        rows=list(csv.DictReader(stream))
    assert len(rows)==17 and len({row['model'] for row in rows})==17
    for row in rows:
        model=results['models'][row['model']]
        values=[]
        for domain,tasks in results['domains'].items():
            value=sum(model['metrics'][t]['score'] for t in tasks)/len(tasks)
            assert abs(float(row[domain])-100*value)<1e-10
            values.append(value)
        assert abs(float(row['overall_domain_equal'])-100*sum(values)/8)<1e-10
    for path,expected_sha in manifest['outputs'].items():
        assert sha(ROOT/path)==expected_sha,path
    assert len([p for p in manifest['outputs'] if p.endswith('.pdf')])==7
    assert len([p for p in manifest['outputs'] if p.endswith('.svg')])==6
    print('PASS: corpus counts, semantic labels, entropy, source hashes, 17-model scores, 7 PDFs and 6 SVGs.')


if __name__=='__main__':main()
