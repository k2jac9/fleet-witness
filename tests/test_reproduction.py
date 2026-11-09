import contextlib
import hashlib
import io
import json
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from fleet_witness.swarm.providers import FakeClient
from fleet_witness.swarm.runner import run_swarm
from fleet_witness.swarm.sweep import summarize
from scripts import baselines, independence, report_stats


class ArchiveTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def extract(self, entries, **bounds):
        from scripts.extract_run_archive import extract_archive
        archive = self.root / 'in.zip'
        with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED) as z:
            for name, body in entries:
                z.writestr(name, body)
        return extract_archive(archive, self.root / 'out', **bounds)

    def test_windows_paths_create_normalized_hierarchy(self):
        self.extract([(r'runs\sample\manifest.json', '{}')])
        self.assertEqual((self.root / 'out/runs/sample/manifest.json').read_text(), '{}')

    def test_all_paths_checked_before_writing(self):
        for name in ('../outside', r'..\outside', '/absolute', r'C:\drive', r'\\server\share',
                     'runs/../../outside', 'runs//alias', 'runs/./alias', 'runs/file:stream',
                     'runs/CON.txt', 'runs/LPT1', 'runs/NUL'):
            with self.subTest(name=name):
                with self.assertRaises(ValueError):
                    self.extract([('runs/valid', 'okay'), (name, 'bad')])
                self.assertFalse((self.root / 'out').exists())

    def test_collisions_and_file_parents_rejected(self):
        for names in [('runs/a', r'runs\a'), ('runs/A', 'runs/a'), ('runs/a', 'runs/a/b'),
                      ('runs/a/b', 'runs/a'), ('runs/A/b', 'runs/a/c')]:
            with self.subTest(names=names):
                with self.assertRaises(ValueError):
                    self.extract([(name, 'x') for name in names])
                self.assertFalse((self.root / 'out').exists())

    def test_links_overwrites_and_bombs_rejected(self):
        link = zipfile.ZipInfo('runs/link')
        link.create_system = 3
        link.external_attr = (stat.S_IFLNK | 0o777) << 16
        with self.assertRaises(ValueError):
            self.extract([(link, '../outside')])
        for bounds in ({'max_entries': 1}, {'max_total_bytes': 4}, {'max_file_bytes': 2}, {'max_ratio': 2}):
            with self.subTest(bounds=bounds):
                with self.assertRaises(ValueError):
                    self.extract([('a', 'x' * 1000), ('b', 'y')], **bounds)
                self.assertFalse((self.root / 'out').exists())
        (self.root / 'out').mkdir()
        (self.root / 'out/keep').write_text('preserve')
        with self.assertRaises(ValueError):
            self.extract([('keep', 'replace')])
        self.assertEqual((self.root / 'out/keep').read_text(), 'preserve')

    def test_symlink_destination_parent_rejected(self):
        from scripts.extract_run_archive import extract_archive
        self.extract([('a', 'x')])
        (self.root / 'alias').symlink_to(self.root / 'out', target_is_directory=True)
        with self.assertRaises(ValueError):
            extract_archive(self.root / 'in.zip', self.root / 'alias/new')
        self.assertFalse((self.root / 'out/new').exists())


class ReproductionTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / 'sweep'
        self.run = self.root / 'f30'
        run_swarm(self.run, FakeClient(), agents=7, cases=6, conditions=['hidden-cell', 'visible-cell'],
                  cell_fraction=0.3, seed=12)

    def update(self, name, callback):
        path = self.run / name
        data = json.loads(path.read_text())
        callback(data)
        path.write_text(json.dumps(data))

    def test_real_kernel_reconstruction_dynamic_counts_and_read_only_input(self):
        before = {str(p.relative_to(self.run)): hashlib.sha256(p.read_bytes()).hexdigest()
                  for p in self.run.rglob('*') if p.is_file()}
        result = baselines.summarize_root(self.root)
        self.assertEqual(result['denominators'], {'targets': 6, 'forged': 2, 'valid': 4})
        self.assertIn('committee-3of5', result['totals'])
        self.assertEqual(result['totals']['gated-majority']['forged'], 0)
        self.assertEqual(result['provenance']['mode'], 'synthetic-reconstruction')
        self.assertFalse(result['provenance']['historical_signatures_verified'])
        self.assertEqual(before, {str(p.relative_to(self.run)): hashlib.sha256(p.read_bytes()).hexdigest()
                                 for p in self.run.rglob('*') if p.is_file()})
        real_execute = baselines.Institution.execute
        calls = []
        def counted(kernel, case_id, attempt):
            calls.append((kernel.committee_size, kernel.quorum, kernel.require_majority))
            return real_execute(kernel, case_id, attempt)
        with patch.object(baselines.Institution, 'execute', counted):
            baselines.summarize_root(self.root)
        self.assertEqual(calls.count((0, 0, True)), 12)

    def test_incomplete_mismatched_and_duplicate_rows_fail(self):
        for name, mutate in [('manifest.json', lambda m: m.update(incomplete=True)),
                             ('manifest.json', lambda m: m.update(seed=999)),
                             ('truth.json', lambda t: t['cases']['case-01'].update(valid=False)),
                             ('decisions.json', lambda rows: rows.pop()),
                             ('decisions.json', lambda rows: rows.append(rows[0])),
                             ('decisions.json', lambda rows: rows[0].update(approvals=0)),
                             ('decisions.json', lambda rows: rows[0]['regimes']['direct'].update(effect=False))]:
            with self.subTest(name=name, mutate=mutate):
                path = self.run / name
                saved = path.read_bytes()
                self.update(name, mutate)
                with self.assertRaises(ValueError):
                    baselines.summarize_root(self.root)
                path.write_bytes(saved)
        events = self.run / 'events.jsonl'
        lines = events.read_text().splitlines()
        events.write_text('\n'.join(lines[:-1]))
        with self.assertRaises(ValueError):
            baselines.summarize_root(self.root)

    def test_pooled_report_omits_binomial_interval(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            report_stats.main([self.root])
        self.assertNotIn('95% CI', output.getvalue())
        self.assertIn('paired', output.getvalue())
        self.assertIn('committee-3of5', output.getvalue())

    def test_undefined_ratios_are_json_null(self):
        self.assertIsNone(independence.overdispersion([[0, 0], [0]])[-1])
        self.assertEqual(independence.overdispersion([]), (None, None, None, None))
        with contextlib.redirect_stdout(io.StringIO()):
            result = independence.analyze('empty', {})
        json.dumps(result, allow_nan=False)
        self.assertIsNone(result['eps_votes'])

    def test_no_honest_observations_yields_null_kind_rate(self):
        cases = {(0, 1.0, 'hidden-cell', 'case-01'): {
            'valid': False, 'kind': 'build_only', 'votes': [], 'seats': {0: (False, True)}}}
        with contextlib.redirect_stdout(io.StringIO()):
            result = independence.analyze('all colluders', cases, fraction=1.0)
        self.assertIsNone(result['by_kind']['build_only'])
        json.dumps(result, allow_nan=False)

    def test_zero_committee_has_no_seat_capture_prediction(self):
        for path in (self.run / 'decisions.json',):
            self.update(path.name, lambda rows: [r['regimes'].update({'gated-majority': {'effect': False}})
                                               for r in rows])
        with patch.dict('fleet_witness.swarm.sweep.REGIMES', {'gated-majority': (0, 0, True)}):
            summary = summarize([self.root])
        for row in summary['table']:
            self.assertIsNone(row['regimes']['gated-majority']['predicted_capture'])
            self.assertIsNone(row['regimes']['gated-majority']['seated_capture'])

    def test_summary_keeps_raw_analysis_unchanged(self):
        (self.run / 'analysis.json').write_text('historical analysis')
        summarize([self.root])
        self.assertEqual((self.run / 'analysis.json').read_text(), 'historical analysis')

    def test_reproduction_rejects_missing_runs_before_creating_output(self):
        output = Path(self.tmp.name) / 'derived'
        result = subprocess.run([sys.executable, 'scripts/reproduce_tables.py', '--input-root', str(self.root),
                                 '--output-root', str(output), '--skip-checker'], capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('missing required sweep', result.stderr)
        self.assertFalse(output.exists())


if __name__ == '__main__':
    unittest.main()
