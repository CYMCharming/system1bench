"""Measurement-boundary and output-integrity regressions for the speed harness."""
import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch, Mock

from benchmarks.performance import Monitor, timed_predict, validated_answers, save_gzip
from benchmarks.performance_report import estimate, validate_cell, summarize, homepage
from benchmarks.performance_telemetry import cpu_delta
from system1bench.common import sha, write


class PerformanceTests(unittest.TestCase):
    def test_close_rejects_already_exited_monitor(self):
        monitor = Monitor.__new__(Monitor)
        monitor.closed = False
        monitor.log = Mock()
        monitor.process = Mock()
        monitor.process.poll.return_value = 0
        with self.assertRaisesRegex(RuntimeError, 'before shutdown'):
            monitor.close()
        self.assertFalse(monitor.closed)
        monitor.process.terminate.assert_not_called()

    def test_unexpected_clean_monitor_exit_invalidates_block(self):
        monitor = Monitor.__new__(Monitor)
        monitor.closed = False
        monitor.output = Path('/unused')
        monitor.process = Mock()
        monitor.process.poll.return_value = 0
        with patch('benchmarks.performance.read', return_value={'status': 'DONE', 'errors': []}):
            with self.assertRaisesRegex(RuntimeError, 'exited unexpectedly'):
                monitor.check()
            monitor.closed = True
            monitor.check()

    def test_audit_primed_tokens_cannot_escape_timed_encoding(self):
        events = []

        class Adapter:
            _cache = {'audit_primed': [1, 2, 3]}

            def synchronize(self):
                events.append('sync')

            def predict(self, states, questions, language, budget, batch_size):
                self.assert_empty = not self._cache
                events.extend(['encode', 'infer', 'construct_answer'])
                return ['answer']

        times = iter([3.0, 3.25])

        def clock():
            events.append('clock')
            return next(times)

        adapter = Adapter()
        output, elapsed = timed_predict(adapter, ['state'], {}, 'en', {}, 1, clock)
        self.assertTrue(adapter.assert_empty)
        self.assertEqual(output, ['answer'])
        self.assertEqual(elapsed, 0.25)
        self.assertEqual(events, ['sync', 'clock', 'encode', 'infer', 'construct_answer', 'sync', 'clock'])

    def test_missing_answer_cannot_be_counted_as_fast_success(self):
        case = dict(id='c', request_sha256='hash', state={},
                    questions={'a': {'type': 'noul'}, 'b': {'type': 'noul'}},
                    gold={'a': {'label': 'true'}, 'b': {'label': 'false'}})
        with self.assertRaises(ValueError):
            validated_answers([case], [{'answers': {'a': {'noul': 0.8}}}])
        with self.assertRaises(ValueError):
            validated_answers([case], [])

    def test_invalid_probability_is_rejected_outside_timed_call(self):
        case = dict(id='c', request_sha256='hash', questions={'a': {'type': 'noul'}},
                    gold={'a': {'label': 'true'}})
        with self.assertRaises(ValueError):
            validated_answers([case], [{'answers': {'a': {'noul': float('nan')}}}])
        rows = validated_answers([case], [{'answers': {'a': {'noul': 0.8}}}])
        self.assertEqual(rows[0]['answers']['a']['prediction'], 'true')
        self.assertEqual(rows[0]['request_sha256'], 'hash')

    def test_round_intervals_require_replicates_not_pooled_requests(self):
        with self.assertRaises(ValueError):
            estimate([1.0] * 64)
        result = estimate([3.0] * 8)
        self.assertEqual(result['median'], 3.0)
        self.assertEqual(result['ci95'], [3.0, 3.0])

    def test_duplicate_timing_rows_cannot_inflate_throughput(self):
        rows = [dict(id=f'c{i}', request_sha256=f'h{i}', answers={
            'a': dict(prediction='true', gold='true', probabilities=[0.0, 1.0], answer={'noul': 1.0})}) for i in range(64)]
        legacy = {r['id']: {'a': dict(request_sha256=r['request_sha256'], gold='true', type='noul', labels=['false', 'true'])}
                  for r in rows}
        spec = dict(name='w', case_ids=[r['id'] for r in rows],
                    request_hashes={r['id']: r['request_sha256'] for r in rows}, questions_per_state=1, decisions=64)
        run = dict(model='m', round=0, workload='w', batch_size=8, warmup_calls=10, warmup_predict_seconds=1.0,
                   max_memory_allocated_bytes=1024, max_memory_reserved_bytes=2048,
                   batches=[dict(requests=8, decisions=8, seconds=0.5, rows=rows[i:i + 8]) for i in range(0, 64, 8)])
        result = validate_cell(run, spec, 8, 0, 'm', legacy)
        self.assertEqual(result['requests_per_second'], 16.0)
        self.assertEqual(result['reference_agreement'], 1.0)
        run['batches'][1]['rows'][0] = run['batches'][0]['rows'][0]
        with self.assertRaises(ValueError):
            validate_cell(run, spec, 8, 0, 'm', legacy)

    def test_cpu_witness_separates_worker_and_sibling_activity(self):
        before = dict(monotonic=10, process_cpu_ticks=0,
                      cores={c: dict(busy=0) for c in [16, 17, 80, 81]})
        after = dict(monotonic=11, process_cpu_ticks=50,
                     cores={c: dict(busy=b) for c, b in [(16, 50), (17, 40), (80, 20), (81, 20)]})
        with patch('benchmarks.performance_telemetry.os.sysconf', return_value=100):
            result = cpu_delta(before, after, [16, 17], [80, 81])
        self.assertAlmostEqual(result['other_busy_fraction_on_worker_cores'], 0.2)
        self.assertAlmostEqual(result['smt_sibling_busy_fraction'], 0.2)

    def test_complete_matrix_and_contract_rejections(self):
        # Synthetic fixtures exist only in a temporary directory; never benchmark evidence.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            out = root / 'performance/v1'
            (root / 'docs').mkdir()
            (root / 'docs/PERFORMANCE_PROTOCOL.md').write_text('fixture')
            models = ['english', 'multilingual', 'llama31_8b_instruct', 'qwen3_8b']
            rows = [dict(id=f'c{i}', request_sha256=f'h{i}', answers={
                'a': dict(prediction='true', gold='true', probabilities=[0., 1.], answer={'noul': 1.})}) for i in range(64)]
            spec = dict(name='w', source_suite='w', reference='dataset', warmup_ids=['warm'],
                        case_ids=[r['id'] for r in rows], questions_per_state=1, decisions=64,
                        request_hashes={r['id']: r['request_sha256'] for r in rows})
            manifest = dict(protocol='fixture', workloads=[spec], models=models, rounds=8,
                            batch_sizes=[1, 8, 32], warmup_min_calls=3, warmup_min_seconds=1.)
            write(out / 'manifest.json', manifest)
            contract = dict(manifest_sha256=sha(out / 'manifest.json'), source_sha256={},
                            protocol_document_sha256=sha(root / 'docs/PERFORMANCE_PROTOCOL.md'),
                            environment={'python': 'fixture'}, thread_env={'OMP_NUM_THREADS': '4'},
                            cpu_affinity=[16, 17, 18, 19], monitor_cpu_affinity=[20],
                            device={'uuid': 'fixture', 'driver_version': 'fixture'},
                            max_other_cpu_busy_fraction=.15, max_sibling_busy_fraction=.15,
                            cpu_contention_consecutive_intervals=2)
            write(out / 'run_contract.json', contract)
            signature = dict(manifest_sha256=sha(out / 'manifest.json'), source_sha256={},
                             contract_sha256=sha(out / 'run_contract.json'))
            ref = [dict(id=r['id'], qid='a', request_sha256=r['request_sha256'],
                        gold='true', type='noul', labels=['false', 'true']) for r in rows]
            save_gzip(root / 'results/english/w.json.gz', {'rows': ref})
            write(root / 'results/english/metadata.json', {'suites': {'w': {'sha256': sha(root / 'results/english/w.json.gz')}}})
            for model in models:
                for rnd in range(8):
                    directory = out / 'raw' / f'round{rnd:02d}' / model
                    meta = dict(status='DONE', telemetry_errors=[], adapter={'model': model}, **signature,
                                environment=contract['environment'], thread_env=contract['thread_env'],
                                cpu_affinity=contract['cpu_affinity'], monitor_cpu_affinity=[20], torch_num_threads=4,
                                gpu_before=contract['device'], cells={})
                    telemetry = dict(gpu=dict(**contract['device'], **{'temperature.gpu': '30', 'clocks.sm': '1000', 'power.draw': '70'}),
                                     foreign_compute_process_count=0, host_load_average=[1, 1, 1], phase={'phase': 'idle'},
                                     cpu_interval=dict(other_busy_fraction_on_worker_cores=0., smt_sibling_busy_fraction=0.))
                    save_gzip(directory / 'telemetry.json.gz', [telemetry])
                    save_gzip(directory / 'input_audits.json.gz', {'w': {i: {'a': dict(complete=True, state_tokens=5, head_tokens=2)}
                                                                       for i in spec['case_ids'] + spec['warmup_ids']}})
                    meta['telemetry_sha256'] = sha(directory / 'telemetry.json.gz')
                    meta['input_audits_sha256'] = sha(directory / 'input_audits.json.gz')
                    for batch in [1, 8, 32]:
                        seconds = batch * .01 * (rnd + 1)
                        run = dict(model=model, round=rnd, workload='w', batch_size=batch, **signature,
                                   warmup_calls=3, warmup_predict_seconds=1.5, warmup_timings=[.5] * 3,
                                   max_memory_allocated_bytes=2**30, max_memory_reserved_bytes=2**31,
                                   batches=[dict(requests=batch, decisions=batch, seconds=seconds, rows=rows[i:i + batch],
                                                 start_monotonic=float(i), end_monotonic=i + seconds) for i in range(0, 64, batch)])
                        name = f'w.batch{batch}.json.gz'
                        save_gzip(directory / name, run)
                        meta['cells'][name] = dict(sha256=sha(directory / name), seconds=seconds * 64 / batch, requests=64, decisions=64)
                    write(directory / 'metadata.json', meta)
            with patch('benchmarks.performance_report.ROOT', root):
                summary = summarize(out)
                self.assertEqual(summary['measured_requests'], 4 * 8 * 3 * 64)
                self.assertEqual(len(summary['raw_files']), 96)
                self.assertAlmostEqual(summary['cells'][0]['batch_p50_ms']['median'], 45.)
                self.assertAlmostEqual(summary['cells'][0]['requests_per_second']['median'], (25. + 20.) / 2)
                self.assertEqual(summary['cells'][0]['reference_agreement']['median'], 1.)
                (root / 'README.md').write_text('# Fixture\n\n## Run provenance\n')
                homepage(summary)
                first = (root / 'README.md').read_text()
                self.assertEqual(first.count('| w |'), 4)
                self.assertIn('45.00 [', first)
                homepage(summary)
                self.assertEqual((root / 'README.md').read_text(), first)
                path = out / 'raw/round07/qwen3_8b/metadata.json'
                from system1bench.common import read
                meta = read(path)
                meta['environment'] = {'python': 'different'}
                write(path, meta)
                with self.assertRaisesRegex(ValueError, 'contract'):
                    summarize(out)
                meta['environment'] = contract['environment']
                del meta['cells']['w.batch32.json.gz']
                write(path, meta)
                with self.assertRaisesRegex(ValueError, 'Missing or extra measured cells'):
                    summarize(out)


if __name__ == '__main__':
    unittest.main()
