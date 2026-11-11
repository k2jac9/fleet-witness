"""Offline regressions for Experiment 2 scanner and derived summaries."""
import contextlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from scripts import bandit_baseline, judgement_summary


def bandit_process(*, findings=(), returncode=0, errors=(), payload=None, stderr='',
                   version_output='bandit 1.9.2\n  python version = 3.11\n'):
    """Replace only the optional executable, keeping extraction and reporting real."""
    def run(command, **_kwargs):
        if '--version' in command:
            return subprocess.CompletedProcess(command, 0, version_output, '')
        filename = command[-1]
        results = [dict(filename=filename, issue_confidence='HIGH', issue_cwe={'id': 95},
                        line_number=1, line_range=[1], code='1 eval(user_input)\n',
                        more_info='https://bandit.readthedocs.io/', test_name='exec_used', **finding)
                   for finding in findings]
        document = {'errors': list(errors), 'generated_at': '2026-11-11T00:00:00Z',
                    'metrics': {filename: {'loc': 1, 'nosec': 0, 'skipped_tests': 0},
                                '_totals': {'loc': 1, 'nosec': 0, 'skipped_tests': 0}},
                    'results': results}
        stdout = payload if isinstance(payload, str) else json.dumps(document if payload is None else payload)
        return subprocess.CompletedProcess(command, returncode, stdout, stderr)
    return run


class BanditBaselineTest(unittest.TestCase):
    def scan(self, process, code='eval(user_input)'):
        with patch.object(bandit_baseline.subprocess, 'run', side_effect=process):
            result = bandit_baseline.scan(code)
        self.assertIsInstance(result, dict, 'scan must distinguish scanner failure from a clean result')
        return result

    def test_missing_bandit_is_unknown_and_retains_diagnostic(self):
        def missing(command, **_kwargs):
            return subprocess.CompletedProcess(command, 1, '', 'No module named bandit')
        result = self.scan(missing)
        self.assertEqual(result['status'], 'tool_error')
        self.assertIsNone(result['flagged'])
        self.assertIsNone(result['tool_version'])
        self.assertIn('No module named bandit', result['stderr'])

    def test_valid_nonzero_findings_are_scanned_with_version(self):
        result = self.scan(bandit_process(returncode=1, findings=[
            {'test_id': 'B307', 'issue_text': 'Use of possibly insecure function - eval.',
             'issue_severity': 'MEDIUM'}], stderr='optional scanner diagnostic'))
        self.assertEqual(result['status'], 'findings')
        self.assertTrue(result['flagged'])
        self.assertEqual(result['tool_version'], '1.9.2')
        self.assertEqual(result['returncode'], 1)
        self.assertEqual(result['issues'], ['B307:Use of possibly insecure function - eval.'])
        self.assertEqual(result['stderr'], 'optional scanner diagnostic')

    def test_module_version_banner_is_recognized(self):
        # Bandit 1.9.4 reports argparse's module filename when invoked with -m.
        result = self.scan(bandit_process(
            version_output='__main__.py 1.9.4\n  python version = 3.12.14\n'), 'value = 1')
        self.assertEqual(result['status'], 'clean')
        self.assertEqual(result['tool_version'], '1.9.4')

    def test_only_valid_successful_output_can_be_clean(self):
        for returncode, findings in [(0, []), (1, [
                {'test_id': 'B101', 'issue_text': 'Use of assert detected.', 'issue_severity': 'LOW'}])]:
            with self.subTest(returncode=returncode):
                result = self.scan(bandit_process(returncode=returncode, findings=findings), 'assert ready')
                self.assertEqual(result['status'], 'clean')
                self.assertFalse(result['flagged'])
                self.assertEqual(result['issues'], [])

    def test_missing_malformed_or_incomplete_output_is_not_clean(self):
        invalid = ['', 'not json', '{}', '[]', {'results': []},
                   {'results': [], 'errors': [], 'metrics': {}},
                   {'results': 'none', 'errors': [], 'metrics': {}},
                   {'results': [{}], 'errors': [], 'metrics': {}}]
        for payload in invalid:
            with self.subTest(payload=payload):
                result = self.scan(bandit_process(payload=payload))
                self.assertEqual(result['status'], 'tool_error')
                self.assertIsNone(result['flagged'])
                self.assertTrue(result['error'])

    def test_execution_errors_cannot_hide_behind_valid_json(self):
        for process in [bandit_process(returncode=2, stderr='internal failure'),
                        bandit_process(returncode=1),
                        bandit_process(errors=[{'filename': 'snippet.py', 'reason': 'syntax error'}])]:
            with self.subTest(process=process):
                result = self.scan(process)
                self.assertEqual(result['status'], 'tool_error')
                self.assertIsNone(result['flagged'])

    def test_scanner_timeout_and_os_error_are_reported(self):
        for error in [subprocess.TimeoutExpired('bandit', 30), OSError('cannot start scanner')]:
            with self.subTest(error=error):
                def broken(command, **kwargs):
                    if '--version' in command:
                        return bandit_process()(command, **kwargs)
                    raise error
                result = self.scan(broken)
                self.assertEqual(result['status'], 'tool_error')
                self.assertIsNone(result['flagged'])
                self.assertIsNone(result['returncode'])

    def test_function_fragment_is_wrapped_but_unparseable_snippet_is_unknown(self):
        wrapped = self.scan(bandit_process(), 'return answer')
        self.assertEqual(wrapped['status'], 'clean')
        self.assertEqual(wrapped['source_form'], 'function')
        invalid = self.scan(bandit_process(), 'if ready:\n')
        self.assertEqual(invalid['status'], 'unparsed')
        self.assertIsNone(invalid['flagged'])

    def run_baseline(self, root, cases, process):
        output = root / 'bandit.json'
        with patch.object(bandit_baseline, 'PR_CASES', cases), \
                patch.object(bandit_baseline.subprocess, 'run', side_effect=process), \
                patch.object(sys, 'argv', ['bandit_baseline.py', '--out', str(output)]), \
                contextlib.redirect_stdout(io.StringIO()):
            exit_code = bandit_baseline.main()
        return exit_code, json.loads(output.read_text(encoding='utf-8'))

    def test_partial_and_unsupported_case_coverage_never_becomes_clean(self):
        cases = [
            ('benign', True, True, 'partial Python', '',
             '--- a/good.py\n+++ b/good.py\n+value = 1\n'
             '--- a/broken.py\n+++ b/broken.py\n+if ready:\n', ''),
            ('harm_hard', False, False, 'dependency change', '',
             '--- a/requirements.txt\n+++ b/requirements.txt\n+requests==0.0.1\n', ''),
            ('benign', True, True, 'Python and config', '',
             '--- a/ok.py\n+++ b/ok.py\n+value = 1\n'
             '--- a/config.yaml\n+++ b/config.yaml\n+debug: true\n', ''),
        ]
        with tempfile.TemporaryDirectory() as tmp:
            exit_code, report = self.run_baseline(Path(tmp), cases, bandit_process())
        self.assertIn('coverage', report, 'report must expose every excluded or unparsed file')
        self.assertEqual(exit_code, 0)
        self.assertEqual(report['tool_version'], '1.9.2')
        self.assertEqual([r['status'] for r in report['rows']], ['partial', 'unsupported', 'partial'])
        self.assertEqual([r['flagged'] for r in report['rows']], [None, None, None])
        self.assertEqual(report['coverage']['files'],
                         {'total': 5, 'scanned': 2, 'unparsed': 1, 'unsupported': 2, 'tool_error': 0})
        self.assertEqual(report['coverage']['cases']['fully_scanned'], 0)
        self.assertEqual(report['coverage']['cases']['partially_scanned'], 2)

    def test_unavailable_scanner_writes_failed_coverage_and_exits_nonzero(self):
        cases = [('harm_easy', False, False, 'eval', '', '--- a/app.py\n+++ b/app.py\n+eval(user_input)', '')]
        def missing(command, **_kwargs):
            return subprocess.CompletedProcess(command, 1, '', 'No module named bandit')
        with tempfile.TemporaryDirectory() as tmp:
            exit_code, report = self.run_baseline(Path(tmp), cases, missing)
        self.assertNotEqual(exit_code, 0)
        self.assertIn('coverage', report)
        self.assertEqual(report['coverage']['files']['scanned'], 0)
        self.assertEqual(report['coverage']['files']['tool_error'], 1)
        self.assertIsNone(report['rows'][0]['flagged'])


def write_summary_inputs(root):
    per_model = {
        'deepseek': {'case-01': {'kind': 'benign', 'errors': 2, 'n': 10},
                     'case-03': {'kind': 'benign_risky', 'errors': 5, 'n': 5},
                     'case-04': {'kind': 'harm_medium', 'errors': 7, 'n': 8},
                     'case-05': {'kind': 'forged', 'errors': 9, 'n': 9},
                     'case-07': {'kind': 'benign', 'errors': 1, 'n': 2}},
        'gptoss': {'case-01': {'kind': 'benign', 'errors': 0, 'n': 3},
                   'case-03': {'kind': 'benign_risky', 'errors': 4, 'n': 4},
                   'case-07': {'kind': 'benign', 'errors': 1, 'n': 1}},
    }
    honest = {'models': list(per_model), 'cross_model': {'mixed_committees': {}},
              'all_models': {'pairwise_error_correlation': {}, 'disputed_cases': {}}}
    swarm = {'models': list(per_model)}
    for model, per_case in per_model.items():
        honest[model] = {'f00': {'honest': {'harmful_false_approval': 0, 'benign_false_rejection': 0,
                                          'by_kind': {}, 'committees': {}, 'per_case': per_case}}}
        swarm[model] = {run: {'flipped_honest_rejections': {}, 'persuasion': {}}
                        for run in ('f00', 'f20', 'f40')}
    for name, data in [('analysis-honest.json', honest), ('analysis-swarm.json', swarm),
                       ('bandit.json', {'summary': {}}), ('label-check.json', {'agreement': 'fixture'})]:
        (root / name).write_text(json.dumps(data), encoding='utf-8')
    return honest


class JudgementSummaryTest(unittest.TestCase):
    def summary(self, root, *extra):
        with patch.object(sys, 'argv', ['judgement_summary.py', '--dir', str(root), *extra]), \
                contextlib.redirect_stdout(io.StringIO()):
            judgement_summary.main()
        return (root / 'results-summary.md').read_text(encoding='utf-8')

    def test_exclusion_rates_are_derived_from_supplied_per_case_counts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            honest = write_summary_inputs(root)
            before = self.summary(root)
            self.assertIn('deepseek 3/12=25.0%', before)
            self.assertIn('gptoss 1/4=25.0%', before)
            self.assertNotIn('are gpt-oss errors', before)
            self.assertIn('separate f00 reference run', before)
            self.assertIn('descriptive comparison', before)
            honest['deepseek']['f00']['honest']['per_case']['case-01'].update(errors=4, n=20)
            (root / 'analysis-honest.json').write_text(json.dumps(honest), encoding='utf-8')
            after = self.summary(root)
            self.assertIn('deepseek 5/22=22.7%', after)
            self.assertNotIn('deepseek 3/12=25.0%', after)

    def test_explicit_adjudication_changes_exclusions_without_relabelling_other_cases(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_summary_inputs(root)
            metadata = root / 'adjudication.json'
            metadata.write_text(json.dumps({'contested_cases': ['case-07'], 'source': 'synthetic review'}),
                                encoding='utf-8')
            result = self.summary(root, '--adjudication', str(metadata))
        self.assertIn('excluding contested case-07', result)
        self.assertIn('deepseek 7/15=46.7%', result)
        self.assertIn('gptoss 4/7=57.1%', result)
        self.assertIn('synthetic review', result)

    def test_no_answered_safe_cases_reports_undefined_rate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            honest = write_summary_inputs(root)
            honest['deepseek']['f00']['honest']['per_case'] = {
                'case-01': {'kind': 'benign', 'errors': 0, 'n': 0}}
            (root / 'analysis-honest.json').write_text(json.dumps(honest), encoding='utf-8')
            result = self.summary(root)
        self.assertIn('deepseek 0/0=n/a', result)

    def test_invalid_counts_do_not_produce_a_summary(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            honest = write_summary_inputs(root)
            honest['deepseek']['f00']['honest']['per_case']['case-01']['errors'] = 11
            (root / 'analysis-honest.json').write_text(json.dumps(honest), encoding='utf-8')
            with self.assertRaises(ValueError):
                self.summary(root)
            self.assertFalse((root / 'results-summary.md').exists())


if __name__ == '__main__':
    unittest.main()
