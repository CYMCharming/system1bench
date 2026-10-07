"""Verify the public, text-free projection and all aggregate metrics."""
import math
from pathlib import Path

from research.public_intent_pilot_v1.analyze import digest, paired_comparison, read, sha, summarize

HERE = Path(__file__).resolve().parent


def verify():
    results = read(HERE / 'results.json')
    rows = read(HERE / 'prediction_projection.json')
    if results['projection_sha256'] != digest(rows):
        raise ValueError('Projection hash mismatch')
    for model, result in results['models'].items():
        manifest = read(HERE / (model + '_data_manifest.json'))
        if sha(HERE / (model + '_data_manifest.json')) != result['receipt']['binding']['data_manifest_sha256']:
            raise ValueError('Run source manifest hash mismatch')
        if sha(HERE / (model + '_runner_original.py')) != result['receipt']['binding']['runner_sha256']:
            raise ValueError('Historical runner hash mismatch')
        for suite, stored in result['metrics'].items():
            selected = [row for row in rows if row['model'] == model and row['suite'] == suite]
            if len(selected) != manifest['suites'][suite]['n'] or len({row['id'] for row in selected}) != len(selected):
                raise ValueError('Projection count mismatch')
            labels = [f'option_{i:03d}' for i in range(manifest['suites'][suite]['classes'])]
            actual = summarize(selected, labels)
            for key, value in actual.items():
                expected = stored[key]
                if isinstance(value, float):
                    if not math.isclose(value, expected, abs_tol=1e-12):
                        raise ValueError('Metric replay mismatch: ' + key)
                elif value != expected:
                    raise ValueError('Metric replay mismatch: ' + key)
    if paired_comparison(rows) != results['paired']:
        raise ValueError('Pairwise replay mismatch')
    if not results['pilot'] or results['official_full_test'] or not results['latency_not_reported']:
        raise ValueError('Pilot scope changed')
    replay = read(HERE / 'nano_native_replay.json')
    if sha(HERE / 'check_nano_native.py') != replay['script_sha256']:
        raise ValueError('Nano native replay script hash mismatch')
    checks = replay['checks']
    if replay['model'] != 'nanojev' or replay['sampled_cases'] != 6 or len(checks) != 6:
        raise ValueError('Nano native replay scope mismatch')
    for check in checks:
        matching = [row for row in rows if row['model'] == 'nanojev' and row['id'] == check['id']]
        if len(matching) != 1 or check['suite'] != matching[0]['suite']:
            raise ValueError('Nano replay case mismatch')
        if check['candidate_count'] != len(matching[0]['probabilities']):
            raise ValueError('Nano replay candidate count mismatch')
        if not check['prediction_matches'] or check['max_probability_delta'] != 0:
            raise ValueError('Nano direct native replay differs')
    print(f'PASS: {len(results["models"])} completed pilots; {len(rows)} predictions; exact public replay')


if __name__ == '__main__':
    verify()
