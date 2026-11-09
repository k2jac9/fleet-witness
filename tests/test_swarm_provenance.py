"""Offline behavior at the public/private experiment evidence boundary."""
import json
import os
from pathlib import Path
import stat
import tempfile
import threading
import unittest
import subprocess
import sys
from unittest.mock import patch

from fleet_witness.swarm.providers import FakeClient, ProviderError
from fleet_witness.swarm.runner import run_swarm
from test_swarm_provider import SyntheticSourceTestCase


class RecordedClient(FakeClient):
    """Synthetic provider boundary; real runner and filesystem are exercised."""
    label = 'test:synthetic-accounting'
    temperature = 0.7
    timeout = 30

    def __init__(self, fail=False):
        super().__init__()
        self.fail = fail
        self.count = 0
        self.lock = threading.Lock()

    def complete(self, system, user, meta=None):
        with self.lock:
            self.count += 1
            number = self.count
        attempt = {'attempt_id': f'attempt-{number}', 'provider': 'test', 'model': 'synthetic',
                   'provider_attempts': 1,
                   'status': 'unresolved' if self.fail else 'settled',
                   'provider_request_id': f'response-{number}', 'input_tokens': 12, 'output_tokens': 8,
                   'cost_usd': 0.0001, 'held_usd': 0.0002 if self.fail else 0.0,
                   'reserved_usd': 0.0002, 'request_sha256': '1' * 64,
                   'response_sha256': '2' * 64, 'latency_s': 0.01,
                   'finish_reason': 'stop', 'truncated': False,
                   'raw_request': system, 'raw_response': 'PRIVATE-EXTRA-MUST-NOT-BE-PUBLIC'}
        if self.fail:
            error = ProviderError('synthetic unresolved charge')
            error.attempts = [attempt]
            error.provider_attempts = 1
            error.cost_usd = 0.0001
            error.held_usd = 0.0002
            error.status = 'unresolved'
            raise error
        result = super().complete(system, user, meta)
        result.update(cost_usd=0.0001, attempts=[attempt], provider_attempts=1,
                      held_usd=0.0, status='completed', truncated=False)
        return result


class RunProvenanceTest(SyntheticSourceTestCase):
    def run_fixture(self, root, client):
        return run_swarm(root / 'run', client, agents=7, cases=1,
                         conditions=['hidden-cell'], cell_fraction=0.3, seed=42)

    def test_attempts_and_private_prompt_receipts_are_recorded_without_public_leaks(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            manifest = self.run_fixture(root, RecordedClient())
            events = [json.loads(line) for line in (root / 'run/events.jsonl').read_text().splitlines()]
            self.assertEqual(manifest.get('provider_attempts'), 14)
            self.assertEqual(manifest.get('logical_responses_completed'), 14)
            self.assertEqual(manifest['abstentions'], 0)
            self.assertAlmostEqual(manifest['cost_usd'], 0.0014)
            self.assertTrue(all(len(event.get('attempts', [])) == 1 for event in events))
            self.assertNotIn('PRIVATE INSTRUCTION', json.dumps(events))
            self.assertNotIn('PRIVATE-EXTRA-MUST-NOT-BE-PUBLIC', json.dumps(events))
            private_path = root / 'run/private/requests.jsonl'
            self.assertTrue(private_path.is_file())
            self.assertEqual(stat.S_IMODE(private_path.stat().st_mode), 0o600)
            self.assertEqual(stat.S_IMODE(private_path.parent.stat().st_mode), 0o700)
            receipts = [json.loads(line) for line in private_path.read_text().splitlines()]
            self.assertEqual(len(receipts), 14)
            self.assertTrue(any('PRIVATE INSTRUCTION' in r['request']['system'] for r in receipts))
            self.assertTrue(all(r['response_text'] for r in receipts))
            self.assertEqual({r['logical_request_id'] for r in receipts},
                             {e['logical_request_id'] for e in events})

    def test_failed_attempts_retain_charges_and_stop_the_run(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            client = RecordedClient(fail=True)
            manifest = self.run_fixture(root, client)
            self.assertTrue(manifest['incomplete'])
            self.assertEqual(manifest['calls'], 0)
            self.assertGreater(manifest.get('provider_attempts', 0), 0)
            self.assertEqual(manifest['provider_attempts'], client.count)
            self.assertAlmostEqual(manifest['cost_usd'], client.count * 0.0001)
            self.assertAlmostEqual(manifest['held_usd'], client.count * 0.0002)
            receipts = [json.loads(line) for line in (root / 'run/private/requests.jsonl').read_text().splitlines()]
            attempted = [r for r in receipts if r['attempts']]
            self.assertEqual(len(attempted), client.count)
            self.assertTrue(all(r['status'] == 'unresolved' for r in attempted))

    def test_manifest_binds_source_runtime_configuration_and_fake_attempt_count(self):
        with tempfile.TemporaryDirectory() as temp:
            manifest = self.run_fixture(Path(temp), FakeClient())
            self.assertEqual(manifest.get('schema_version'), 'swarm-run-2')
            self.assertEqual(manifest.get('provider_attempts'), 0)
            self.assertEqual(manifest.get('logical_responses_completed'), 14)
            self.assertEqual(len(manifest.get('source', {}).get('source_sha256', '')), 64)
            self.assertIn('fleet_witness/swarm/runner.py', manifest['source']['source_files'])
            self.assertTrue(manifest.get('runtime', {}).get('python_version'))
            self.assertIn('temperature', manifest.get('model_config', {}))
            self.assertEqual(manifest.get('scheduled_logical_requests'), 14)

    def test_new_run_executes_gated_majority_without_a_committee(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.run_fixture(root, FakeClient())
            rows = json.loads((root / 'run/decisions.json').read_text())
            self.assertIn('gated-majority', rows[0]['regimes'])
            self.assertEqual(rows[0]['regimes']['gated-majority']['effect'], rows[0]['majority_approve'])

    def test_real_provider_boundary_serializes_and_accounts_complete_run(self):
        from fleet_witness.swarm import providers as p
        from test_swarm_provider import authorization
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            ledger = p.Ledger('openrouter', 1, 1, root / 'ledger.sqlite3')
            record = authorization(ledger)
            record['request_limit'] = 14
            client = p.ModelClient('openrouter', 'fixture-model', ledger, authorization=record,
                                   max_output_tokens=100, timeout=1)
            def transport(url, key, body, timeout, **kwargs):
                import time
                time.sleep(.005)  # Exercise overlapping runner submissions.
                answer = ('{"sign":true}' if 'audit committee' in body['messages'][0]['content']
                          else '{"vote":"approve"}')
                return json.dumps({'id': 'synthetic', 'choices': [{'message': {'content': answer},
                                    'finish_reason': 'stop'}],
                                   'usage': {'prompt_tokens': 10, 'completion_tokens': 10}}).encode()
            with patch.object(p, '_post', transport), patch.object(p, '_env_key', return_value='synthetic-key'):
                manifest = self.run_fixture(root, client)
            self.assertFalse(manifest['incomplete'])
            self.assertEqual(manifest['provider_attempts'], 14)
            self.assertEqual(manifest['abstentions'], 0)
            self.assertEqual(manifest['settled_cost_usd'], .00028)
            self.assertEqual(manifest['budget_liability_usd'], .00028)
            self.assertEqual(manifest['ledger_before']['run']['provider_attempts'], 0)
            self.assertEqual(manifest['ledger_after']['run']['provider_attempts'], 14)
            self.assertEqual(manifest['ledger_after']['run']['settled_usd'], .00028)
            self.assertEqual(len(manifest['authorization']['sha256']), 64)
            self.assertTrue(json.loads((root / 'run/decisions.json').read_text())[0]['majority_approve'])


class PaidEntryPointTest(unittest.TestCase):
    def test_uncommitted_source_is_rejected_before_paid_operator_use(self):
        from fleet_witness.swarm import operator
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            def git(*args):
                return subprocess.run(['git', '-C', str(root), *args], check=True,
                                      capture_output=True, text=True)
            git('init')
            (root / 'source.py').write_text('accepted = True\n')
            git('add', 'source.py')
            git('-c', 'user.name=Offline Test', '-c', 'user.email=test@example.invalid',
                'commit', '-m', 'synthetic source')
            self.assertTrue(hasattr(operator, 'require_committed_source'))
            operator.require_committed_source(root)
            (root / 'source.py').write_text('accepted = False\n')
            with self.assertRaisesRegex(ValueError, 'committed'):
                operator.require_committed_source(root)

    def test_missing_judge_authorization_prevents_any_swarm_output(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            result = subprocess.run([sys.executable, '-m', 'fleet_witness', 'swarm',
                                     '--provider', 'fake', '--agents', '7', '--cases', '1',
                                     '--judge-model', 'test/judge', '--output', str(root / 'output')],
                                    cwd=Path(__file__).resolve().parents[1],
                                    capture_output=True, text=True, timeout=10)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse((root / 'output').exists())

    def test_missing_authorization_fails_before_creating_ledger_or_reading_credentials(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            environment = dict(os.environ, HOME=str(root), OPENROUTER_API_KEY='', ADAPTION_API_KEY='')
            result = subprocess.run([sys.executable, '-m', 'fleet_witness', 'swarm',
                                     '--provider', 'openrouter', '--model', 'test/model',
                                     '--output', str(root / 'output'), '--dry-run'],
                                    cwd=Path(__file__).resolve().parents[1], env=environment,
                                    capture_output=True, text=True, timeout=10)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse((root / '.fleet_witness').exists(),
                             'a missing authorization must not initialize accounting')
            self.assertFalse((root / 'output').exists())
            self.assertIn('authorization', result.stderr.lower())

    def test_review_scripts_require_authorization_before_creating_outputs(self):
        for script in ('peer_review.py', 'reviewer_speedtest.py'):
            with self.subTest(script=script), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                environment = dict(os.environ, HOME=str(root), OPENROUTER_API_KEY='', ADAPTION_API_KEY='')
                args = [sys.executable, 'scripts/' + script, '--paper', str(root / 'absent-paper.md'),
                        '--out', str(root / 'output')]
                if script == 'peer_review.py':
                    args += ['--data', str(root / 'absent-data.md')]
                result = subprocess.run(args, cwd=Path(__file__).resolve().parents[1], env=environment,
                                        capture_output=True, text=True, timeout=10)
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse((root / '.fleet_witness').exists())
                self.assertFalse((root / 'output').exists())
                self.assertIn('authorization', result.stderr.lower())


class JudgeAccountingTest(unittest.TestCase):
    def test_paid_malformed_judge_answer_retains_settled_cost(self):
        from fleet_witness.swarm.judge import judge_run
        class MalformedClient(RecordedClient):
            def complete(self, *args, **kwargs):
                result = super().complete(*args, **kwargs)
                result['text'] = '{"suspects": BROKEN}'
                return result
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'events.jsonl').write_text('')
            (root / 'manifest.json').write_text(json.dumps({'conditions': ['hidden-clean']}))
            (root / 'truth.json').write_text(json.dumps({'colluders': []}))
            entry = judge_run(root, MalformedClient())['conditions']['hidden-clean']
            self.assertEqual(entry['provider_attempts'], 1)
            self.assertEqual(entry['cost_usd'], .0001)
            self.assertIn('error', entry)

    def test_judge_failure_retains_attempt_and_cost_evidence(self):
        from fleet_witness.swarm.judge import judge_run
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'events.jsonl').write_text('')
            (root / 'manifest.json').write_text(json.dumps({'conditions': ['hidden-clean']}))
            (root / 'truth.json').write_text(json.dumps({'colluders': []}))
            result = judge_run(root, RecordedClient(fail=True))
            entry = result['conditions']['hidden-clean']
            self.assertEqual(entry.get('provider_attempts'), 1)
            self.assertAlmostEqual(entry.get('cost_usd', 0), 0.0001)
            self.assertAlmostEqual(entry.get('held_usd', 0), 0.0002)
            self.assertEqual(entry.get('attempts', [{}])[0].get('attempt_id'), 'attempt-1')
            self.assertNotIn('PRIVATE-EXTRA-MUST-NOT-BE-PUBLIC', json.dumps(result))


class ReviewAccountingTest(SyntheticSourceTestCase):
    def test_unsent_reservation_is_preserved_but_not_counted_as_dispatch(self):
        from fleet_witness.swarm import providers as p
        from fleet_witness.swarm.run_records import PrivateRunLog, public_attempts
        from test_swarm_provider import authorization
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            ledger = p.Ledger('openrouter', 1, 1, root / 'ledger.sqlite3')
            client = p.ModelClient('openrouter', 'fixture-model', ledger, authorization=authorization(ledger),
                                   max_output_tokens=100, timeout=1)
            receipts = PrivateRunLog(root)
            try:
                with patch.object(ledger, 'dispatch', side_effect=OSError('synthetic persistence failure')), \
                        patch.object(p, '_env_key', return_value='synthetic-key'), \
                        patch.object(p, '_post', side_effect=AssertionError('network called')):
                    with self.assertRaises(ProviderError) as caught:
                        client.complete('s', 'u')
                error = caught.exception
                receipts.write('logical-1', 's', 'u', None, error.status, public_attempts(error.attempts))
                self.assertEqual(error.provider_attempts, 0)
                self.assertEqual(ledger.calls, 0)
                self.assertEqual(receipts.summary()['provider_attempts'], 0)
                self.assertEqual(len(receipts.summary()['attempt_ids']), 1)
                self.assertGreater(receipts.summary()['held_usd'], 0)
            finally:
                receipts.close()

    def test_review_receipts_preserve_failed_and_truncated_attempts(self):
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
        import peer_review
        from fleet_witness.swarm.run_records import PrivateRunLog
        class TruncatedClient(RecordedClient):
            def complete(self, *args, **kwargs):
                result = super().complete(*args, **kwargs)
                result.update(status='truncated', truncated=True)
                result['attempts'][0]['status'] = 'truncated'
                return result
        for client in (RecordedClient(fail=True), TruncatedClient()):
            with self.subTest(client=type(client).__name__), tempfile.TemporaryDirectory() as temp:
                receipts = PrivateRunLog(Path(temp))
                try:
                    with self.assertRaises(ProviderError):
                        peer_review.call(client, 'synthetic prompt', receipts)
                    summary = receipts.summary()
                    self.assertEqual(summary['provider_attempts'], 1)
                    self.assertEqual(summary['cost_usd'], .0001)
                finally:
                    receipts.close()

    def test_speedtest_parse_failure_preserves_settled_attempt(self):
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
        import reviewer_speedtest
        from fleet_witness.swarm.run_records import PrivateRunLog
        class MalformedClient(RecordedClient):
            def complete(self, *args, **kwargs):
                result = super().complete(*args, **kwargs)
                result['text'] = '{"concerns": 123}'
                return result
        with tempfile.TemporaryDirectory() as temp:
            receipts = PrivateRunLog(Path(temp))
            try:
                row = reviewer_speedtest.run('synthetic', MalformedClient(), 'synthetic paper', receipts)
                self.assertFalse(row['ok'])
                self.assertEqual(row['provider_attempts'], 1)
                self.assertEqual(row['cost_usd'], .0001)
                self.assertEqual(receipts.summary()['provider_attempts'], 1)
            finally:
                receipts.close()


if __name__ == '__main__':
    unittest.main()
