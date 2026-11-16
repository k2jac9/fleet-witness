import contextlib
import hashlib
import io
import json
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile
from types import SimpleNamespace
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


class CheckerReportingTest(unittest.TestCase):
    def test_valid_structured_checker_pass_is_retained(self):
        from fleet_witness.verify_institution import MUTANTS
        from scripts.reproduce_tables import _run_checker
        def entry(verified, mutations):
            return {'depth': 6, 'mutations': mutations, 'distinct_states': 1, 'transitions_checked': 1,
                    'verified': verified, 'violations': [] if verified else [{'trace': ['test'], 'problems': ['found']}],
                    'seconds': 0.0}
        data = {'schema_version': 'institution-check-v1', 'depth': 6,
                'base': {'hybrid': entry(True, []), 'committee_only': entry(True, [])},
                'mutants': {name: entry(False, [name]) for name in MUTANTS}, 'passed': True}
        with tempfile.TemporaryDirectory() as tmp:
            def run(command, **kwargs):
                kwargs['stdout'].write(json.dumps(data))
                return SimpleNamespace(returncode=0)
            with patch('scripts.reproduce_tables.subprocess.run', side_effect=run):
                result = _run_checker(Path(tmp))
            self.assertTrue(result['passed'])
            self.assertEqual(json.loads((Path(tmp) / 'verify-depth6.json').read_text()), data)
        data['mutants'][MUTANTS[0]]['violations'] = [None]
        from scripts.reproduce_tables import _checker_report_passed
        self.assertFalse(_checker_report_passed(data))

    def test_checker_process_failure_and_malformed_json_are_retained_as_failures(self):
        from scripts.reproduce_tables import _run_checker
        for response, returncode in (('not-json', 0), ('{}', 1)):
            with self.subTest(response=response, returncode=returncode), tempfile.TemporaryDirectory() as tmp:
                def run(command, **kwargs):
                    kwargs['stdout'].write(response)
                    kwargs['stderr'].write('synthetic diagnostic')
                    return SimpleNamespace(returncode=returncode)
                with patch('scripts.reproduce_tables.subprocess.run', side_effect=run):
                    result = _run_checker(Path(tmp))
                self.assertTrue(result['executed'])
                self.assertFalse(result['passed'])
                self.assertEqual((Path(tmp) / 'verify-depth6.json').read_text(), response)
                self.assertEqual((Path(tmp) / 'verify-depth6.stderr').read_text(), 'synthetic diagnostic')

    def test_checker_launch_failure_is_recorded_and_not_a_pass(self):
        from scripts.reproduce_tables import _run_checker
        with tempfile.TemporaryDirectory() as tmp, \
                patch('scripts.reproduce_tables.subprocess.run', side_effect=OSError('synthetic failure')):
            result = _run_checker(Path(tmp))
            self.assertTrue(result['executed'])
            self.assertFalse(result['passed'])
            self.assertIn('synthetic failure', (Path(tmp) / 'verify-depth6.stderr').read_text())


class TreatmentBoundaryReviewTest(unittest.TestCase):
    def test_partial_strict_sweep_refuses_changed_visible_comments_before_dispatch(self):
        from fleet_witness.swarm.sweep import run_sweep
        class Counting(FakeClient):
            calls = 0
            def complete(self, *args, **kwargs):
                self.calls += 1
                return super().complete(*args, **kwargs)
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / 'sweep'
            client = Counting()
            run_swarm(root / 'f00', client, agents=7, cases=1, conditions=['visible-cell'],
                      cell_fraction=0.0, seed=0, recent_comments=0)
            client.calls = 0
            with self.assertRaisesRegex(ValueError, 'configuration'):
                run_sweep(root, client, fractions=(0.0, 0.1), agents=7, cases=1,
                          conditions=('visible-cell',))
            self.assertEqual(client.calls, 0)
            self.assertFalse((root / 'f10').exists())

    def extract_historical_run(self, root, relative='sweep-deepseek2k/f00'):
        archive = Path(__file__).resolve().parents[1] / 'data/fleet-witness-runs-2026-11-08.zip'
        run = root / relative
        run.mkdir(parents=True)
        with zipfile.ZipFile(archive) as source:
            for name in ('manifest.json', 'events.jsonl', 'truth.json', 'decisions.json'):
                member = 'runs\\' + relative.replace('/', '\\') + '\\' + name
                (run / name).write_bytes(source.read(member))
        return run

    def test_official_historical_run_is_summarizable_and_cannot_be_manifest_spoofed(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            run = self.extract_historical_run(root)
            result = summarize([run.parent])
            self.assertEqual(result['parser_treatment'], 'legacy-recorded')
            with (run / 'events.jsonl').open('a') as handle:
                handle.write('\n')
            with self.assertRaisesRegex(ValueError, 'treatment|historical'):
                summarize([run.parent])

    def test_historical_run_works_with_swarm_summary_cli(self):
        with tempfile.TemporaryDirectory() as temp:
            run = self.extract_historical_run(Path(temp))
            result = subprocess.run([sys.executable, '-m', 'fleet_witness', 'swarm-summary', str(run.parent)],
                                    text=True, capture_output=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stderr)
            summary = json.loads((run.parent / 'sweep-summary.json').read_text())
            self.assertEqual(summary['parser_treatment'], 'legacy-recorded')

    def test_other_analysis_paths_reject_unknown_treatment(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / 'sweep'
            run = root / 'f00'
            run_swarm(run, FakeClient(), agents=7, cases=1, conditions=['hidden-cell'],
                      cell_fraction=0.0, seed=2, case_mode='ambiguous')
            path = run / 'manifest.json'
            data = json.loads(path.read_text())
            data['parser_treatment'] = 'unknown-treatment'
            path.write_text(json.dumps(data))
            for analyze in (lambda: baselines.load_root(root), lambda: report_stats.statistics(root),
                            lambda: independence.load([run])):
                with self.assertRaisesRegex(ValueError, 'treatment'):
                    analyze()

    def test_partial_legacy_sweep_refuses_new_calls_before_dispatch(self):
        from fleet_witness.swarm.sweep import run_sweep
        class Counting(FakeClient):
            calls = 0
            def complete(self, *args, **kwargs):
                self.calls += 1
                return super().complete(*args, **kwargs)
        with tempfile.TemporaryDirectory() as temp:
            run = self.extract_historical_run(Path(temp))
            client = Counting()
            with self.assertRaisesRegex(ValueError, 'treatment|sweep'):
                run_sweep(run.parent, client, fractions=(0.0, 0.1), agents=7, cases=1)
            self.assertEqual(client.calls, 0)
            self.assertFalse((run.parent / 'f10').exists())

    def test_partial_strict_sweep_refuses_changed_source_before_dispatch(self):
        from fleet_witness.swarm.sweep import run_sweep
        class Counting(FakeClient):
            calls = 0
            def complete(self, *args, **kwargs):
                self.calls += 1
                return super().complete(*args, **kwargs)
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / 'sweep'
            client = Counting()
            run_sweep(root, client, fractions=(0.0,), agents=7, cases=1,
                      conditions=('hidden-cell', 'visible-cell'))
            client.calls = 0
            with patch('fleet_witness.swarm.providers.source_identity', return_value={'source_sha256': 'changed'}):
                with self.assertRaisesRegex(ValueError, 'source|configuration'):
                    run_sweep(root, client, fractions=(0.0, 0.1), agents=7, cases=1,
                              conditions=('hidden-cell', 'visible-cell'))
            self.assertEqual(client.calls, 0)
            self.assertFalse((root / 'f10').exists())

    def test_partial_strict_sweep_refuses_changed_temperature_before_dispatch(self):
        from fleet_witness.swarm.sweep import run_sweep
        class Counting(FakeClient):
            calls = 0
            temperature = 0.0
            timeout = 30
            def complete(self, *args, **kwargs):
                self.calls += 1
                return super().complete(*args, **kwargs)
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / 'sweep'
            client = Counting()
            run_sweep(root, client, fractions=(0.0,), agents=7, cases=1)
            client.calls = 0
            client.temperature = 2.0
            with self.assertRaisesRegex(ValueError, 'configuration'):
                run_sweep(root, client, fractions=(0.0, 0.1), agents=7, cases=1)
            self.assertEqual(client.calls, 0)
            self.assertFalse((root / 'f10').exists())


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

    def test_strict_summary_rejects_missing_and_malformed_source_identities(self):
        paths = [self.run / 'manifest.json', self.run / 'run-start.json']
        originals = [json.loads(path.read_text()) for path in paths]
        malformed = [None, {}, {'source_sha256': 'not-a-digest'},
                     {**originals[0]['source'], 'source_sha256': '0' * 64},
                     {**originals[0]['source'], 'source_files': {}},
                     {**originals[0]['source'], 'digest_algorithm': 'other'}]
        try:
            for index, source in enumerate(malformed):
                with self.subTest(case=index):
                    for path, original in zip(paths, originals):
                        path.write_text(json.dumps({**original, 'source': source}))
                    with self.assertRaisesRegex(ValueError, 'source|treatment'):
                        summarize([self.root])
            for path, original in zip(paths, originals):
                record = dict(original)
                record.pop('source')
                path.write_text(json.dumps(record))
            with self.assertRaisesRegex(ValueError, 'source|treatment'):
                summarize([self.root])
        finally:
            for path, original in zip(paths, originals):
                path.write_text(json.dumps(original))
        self.assertEqual(summarize([self.root])['parser_treatment'], 'swarm-strict-v1')

    def test_strict_summary_accepts_well_formed_source_outside_git(self):
        for path in (self.run / 'manifest.json', self.run / 'run-start.json'):
            record = json.loads(path.read_text())
            record['source']['source_commit'] = None
            path.write_text(json.dumps(record))
        self.assertEqual(summarize([self.root])['parser_treatment'], 'swarm-strict-v1')

    def test_reproduction_receipt_identifies_transitive_source_files(self):
        from scripts import reproduce_tables
        inputs = Path(self.tmp.name) / 'empty-input'
        inputs.mkdir()
        output = Path(self.tmp.name) / 'derived'
        with patch.object(reproduce_tables, 'MAIN_ROOTS', ()), \
                patch.object(reproduce_tables, 'AMBIG_ROOTS', {}), \
                patch.object(reproduce_tables.independence, 'mixed'), \
                contextlib.redirect_stdout(io.StringIO()):
            receipt = reproduce_tables.reproduce(inputs, output, skip_checker=True)
        for name in ('fleet_witness/swarm/run_records.py', 'fleet_witness/swarm/providers.py'):
            self.assertEqual(receipt['source_files_sha256'][name],
                             hashlib.sha256((reproduce_tables.REPO / name).read_bytes()).hexdigest())
        self.assertEqual(json.loads((output / 'reproduction-provenance.json').read_text()), receipt)

    def test_reproduction_rejects_source_change_during_run(self):
        from scripts import reproduce_tables
        base = Path(self.tmp.name)
        source = base / 'source'
        source.mkdir()
        for name in ('scripts', 'fleet_witness'):
            shutil.copytree(reproduce_tables.REPO / name, source / name,
                            ignore=shutil.ignore_patterns('__pycache__'))
        inputs = base / 'empty-input'
        inputs.mkdir()
        output = base / 'derived'
        def modify_source(*args):
            (source / 'fleet_witness/swarm/run_records.py').write_text('# changed during run\n')
        with patch.object(reproduce_tables, 'REPO', source), \
                patch.object(reproduce_tables, 'MAIN_ROOTS', ()), \
                patch.object(reproduce_tables, 'AMBIG_ROOTS', {}), \
                patch.object(reproduce_tables.independence, 'mixed', side_effect=modify_source), \
                patch.object(reproduce_tables.subprocess, 'check_output', return_value='test\n'), \
                contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaisesRegex(ValueError, 'source.*changed'):
                reproduce_tables.reproduce(inputs, output, skip_checker=True)
        self.assertTrue(output.exists())

    def test_reproduction_rejects_commit_change_during_run(self):
        from scripts import reproduce_tables
        inputs = Path(self.tmp.name) / 'empty-input'
        inputs.mkdir()
        output = Path(self.tmp.name) / 'derived'
        def git(command, **kwargs):
            if command[1:3] == ['rev-parse', 'HEAD']:
                git.count += 1
                return ('a' if git.count == 1 else 'b') * 40 + '\n'
            return ''
        git.count = 0
        with patch.object(reproduce_tables, 'MAIN_ROOTS', ()), \
                patch.object(reproduce_tables, 'AMBIG_ROOTS', {}), \
                patch.object(reproduce_tables.independence, 'mixed'), \
                patch.object(reproduce_tables.subprocess, 'check_output', side_effect=git), \
                contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaisesRegex(ValueError, 'source.*changed'):
                reproduce_tables.reproduce(inputs, output, skip_checker=True)
        self.assertTrue(output.exists())

    def test_summary_refuses_unknown_and_mixed_parser_treatments(self):
        manifest = self.run / 'manifest.json'
        saved = manifest.read_bytes()
        data = json.loads(saved)
        data.pop('parser_treatment', None)
        manifest.write_text(json.dumps(data))
        fingerprint = {name: hashlib.sha256((self.run / name).read_bytes()).hexdigest()
                       for name in ('manifest.json', 'truth.json', 'events.jsonl', 'decisions.json')}
        trusted = {(self.root.name, self.run.name): fingerprint}
        with self.assertRaisesRegex(ValueError, 'treatment'):
            summarize([self.root])
        with patch('fleet_witness.swarm.run_records._historical_fingerprints', return_value=trusted):
            legacy = summarize([self.root])
            self.assertEqual(legacy['parser_treatment'], 'legacy-recorded')
            run_swarm(self.root / 'f40', FakeClient(), agents=7, cases=1,
                      conditions=['hidden-cell'], cell_fraction=0.4, seed=13)
            with self.assertRaisesRegex(ValueError, 'treatment'):
                summarize([self.root])

    def test_reproduction_rejects_missing_runs_before_creating_output(self):
        output = Path(self.tmp.name) / 'derived'
        result = subprocess.run([sys.executable, 'scripts/reproduce_tables.py', '--input-root', str(self.root),
                                 '--output-root', str(output), '--skip-checker'], capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('missing required sweep', result.stderr)
        self.assertFalse(output.exists())

    def test_reproduction_rejects_wrong_model_and_configuration_before_output(self):
        from scripts.reproduce_tables import reproduce
        for model, error in [('openrouter:openai/gpt-oss-20b', 'model'),
                             ('openrouter:deepseek/deepseek-v4-flash-0731', 'configuration')]:
            with self.subTest(model=model), tempfile.TemporaryDirectory() as temp:
                inputs = Path(temp) / 'inputs'
                for i, fraction in enumerate((0, .1, .2, .3, .4, .5)):
                    directory = inputs / 'sweep-deepseek2k' / f'f{i * 10:02d}'
                    run_swarm(directory, FakeClient(), agents=7, cases=1,
                              conditions=['hidden-cell', 'visible-cell'], cell_fraction=fraction, seed=1000+i)
                    path = directory / 'manifest.json'
                    manifest = json.loads(path.read_text())
                    manifest['model'] = model  # Synthetic fixture with deliberately wrong report identity.
                    path.write_text(json.dumps(manifest))
                output = Path(temp) / 'derived'
                with self.assertRaisesRegex(ValueError, error):
                    reproduce(inputs, output, skip_checker=True)
                self.assertFalse(output.exists())


if __name__ == '__main__':
    unittest.main()
