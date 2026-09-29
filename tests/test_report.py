import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from system1bench import report
from system1bench.common import ROOT, read


class ReportIntegrityTests(unittest.TestCase):
    def test_homepage_has_every_suite_once_with_dynamic_model_columns(self):
        source = read(ROOT / 'results/summary.json')
        base = next(iter(source['models'].values()))
        # Four named fixtures exercise rendering only; never written as run artifacts.
        models = ['fixture_a', 'fixture_b', 'fixture_c', 'fixture_d']
        summary = {'models': {m: base for m in models}}
        manifest = read(ROOT / 'protocol_manifest.json')
        with tempfile.TemporaryDirectory() as temp, patch.object(report, 'ROOT', Path(temp)):
            rendered = report.homepage(summary, manifest, models)
        for suite in manifest['suites']:
            lines = [line for line in rendered.splitlines() if line.startswith('| ' + suite['name'] + ' |')]
            self.assertEqual(len(lines), 1, suite['name'])
            self.assertEqual(len(lines[0].split('|')), len(models) + 5)
        self.assertIn('fixture_d', rendered)
        self.assertIn('Ordinal scoring', rendered)

    def test_hosted_column_uses_actual_source_scores(self):
        path = ROOT / 'api_results/jev-1.13.0/summary.json'
        if not path.exists():
            self.skipTest('Hosted artifacts not present')
        summary = read(ROOT / 'results/summary.json')
        models = list(summary['models'])
        manifest = read(ROOT / 'protocol_manifest.json')
        rendered = report.homepage(summary, manifest, models)
        hosted = read(path)
        for suite in manifest['suites']:
            row = next(line for line in rendered.splitlines() if line.startswith('| '+suite['name']+' |'))
            self.assertEqual(len(row.split('|')), len(models)+6)
            self.assertEqual(row.split('|')[-3].strip(), report.percent(hosted['suites'][suite['name']]['accuracy']))

    def test_report_refuses_omitted_model_directory(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            results = root / 'results'
            (results / 'new_model').mkdir(parents=True)
            (results / 'new_model/metadata.json').write_text('{}')
            (results / 'summary.json').write_text(json.dumps({'models': {}}))
            with patch.object(report, 'ROOT', root), patch('sys.argv', ['report']):
                with self.assertRaisesRegex(ValueError, 'omits model'):
                    report.main()


if __name__ == '__main__':
    unittest.main()
