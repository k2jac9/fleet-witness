"""Controlled supervisor contracts: synthetic keys and mocked HTTPS only."""
from contextlib import closing
import copy
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from fleet_witness.swarm import providers as p
from test_swarm_provider import SyntheticSourceTestCase, authorization

try:
    from fleet_witness import controlled_calibration as calibration
except ImportError:
    calibration = None


def facts():
    return {'run_id': 'opaque-run', 'artifact_digest': 'sha256:artifact',
            'decision_time_policy': {'allowed': True, 'version': 1},
            'reviewer_verdict': 'approve', 'reviewer_statement': 'Untrusted release claim',
            'receipts': [{'issuer': 'build', 'claim': 'build_succeeded', 'scope': 'build',
                          'artifact_digest': 'sha256:artifact', 'run_id': 'opaque-run',
                          'signature': '0' * 64}]}


def response(text='{"recommendation":"approve","reason":"Proposal only"}'):
    return {'id': 'synthetic-response', 'model': 'fixture-model', 'status': 'completed',
            'output': [{'id': 'message-id', 'type': 'message', 'role': 'assistant',
                        'status': 'completed',
                        'content': [{'type': 'output_text', 'text': text}]}],
            'usage': {'input_tokens': 10, 'output_tokens': 20, 'total_tokens': 30}}


class ControlledSupervisorTests(SyntheticSourceTestCase):
    def setUp(self):
        super().setUp()
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.ledger = p.Ledger('adaption', 1, 1, self.root / 'ledger.sqlite3')
        record = authorization(self.ledger, provider='adaption')
        self.client = p.ModelClient('adaption', 'fixture-model', self.ledger,
                                   max_output_tokens=100, timeout=1, authorization=record)
        key = patch.object(p, '_env_key', return_value='synthetic-private-key')
        key.start()
        self.addCleanup(key.stop)

    def recommend(self, data=None, visible=None, presentation='raw'):
        self.assertTrue(hasattr(self.client, 'recommend'), 'strict supervisor interface missing')
        with patch.object(p, '_post', return_value=json.dumps(data or response()).encode()) as post:
            result = self.client.recommend(visible or facts(), presentation)
        return result, post

    def test_equal_paired_facts_and_only_presentation_changes(self):
        a, post_a = self.recommend()
        b, post_b = self.recommend(presentation='scope_explicit')
        request_a, request_b = post_a.call_args.args[2], post_b.call_args.args[2]
        self.assertEqual(json.loads(request_a['input']), facts())
        self.assertEqual(request_a['input'], request_b['input'])
        self.assertNotEqual(request_a['instructions'], request_b['instructions'])
        self.assertEqual({k:v for k,v in request_a.items() if k != 'instructions'},
                         {k:v for k,v in request_b.items() if k != 'instructions'})
        self.assertEqual(a['proposal']['recommendation'], 'approve')
        self.assertEqual(b['status'], 'succeeded')

    def test_unknown_or_privileged_input_refused_before_key_or_reservation(self):
        self.assertTrue(hasattr(self.client, 'recommend'), 'strict supervisor interface missing')
        variants = [dict(facts(), scenario_truth=True), dict(facts(), trial_id='private'),
                    dict(facts(), receipts=[dict(facts()['receipts'][0], issuer_key='private')])]
        with patch.object(p, '_env_key', side_effect=AssertionError('key accessed')), \
                patch.object(p, '_post', side_effect=AssertionError('network accessed')):
            for value in variants:
                with self.subTest(value=value), self.assertRaises(ValueError):
                    self.client.recommend(value, 'raw')
        self.assertEqual(self.ledger.calls, 0)
        self.assertEqual(self.ledger.run_reserved, 0)

    def test_proposal_and_usage_are_committed_with_same_receipt(self):
        result, _ = self.recommend()
        with closing(sqlite3.connect(self.ledger.path)) as c:
            row = c.execute('SELECT status,receipt_json,response_raw,request_json,settled FROM requests').fetchone()
            tables = {r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        receipt = json.loads(row[1])
        self.assertEqual(row[0], 'succeeded')
        self.assertEqual(receipt['proposal'], result['proposal'])
        self.assertEqual(receipt['response_contract'], 'supervisor-v1')
        self.assertEqual(json.loads(row[2])['id'], 'synthetic-response')
        self.assertEqual(json.loads(json.loads(row[3])['input']), facts())
        self.assertGreater(row[4], 0)
        self.assertNotIn('releases', tables)

    def test_invalid_proposals_are_accounted_invalids_not_denials(self):
        texts = ['deny', '[]', '{"recommendation":"deny","reason":"x","tool":"release"}',
                 '{"recommendation":"approve","recommendation":"deny","reason":"x"}',
                 '{"recommendation":"deny","reason":NaN}',
                 '{"recommendation":"deny","reason":""}',
                 '{"recommendation":"deny","reason":"' + 'x' * 2049 + '"}']
        for index, text in enumerate(texts):
            with self.subTest(text=text[:60]):
                ledger = p.Ledger('adaption', 1, 1, self.root / f'case-{index}.sqlite3')
                self.ledger = ledger
                self.client = p.ModelClient('adaption', 'fixture-model', ledger, max_output_tokens=100,
                                           timeout=1, authorization=authorization(ledger, provider='adaption'))
                result, post = self.recommend(response(text))
                self.assertEqual(result['status'], 'invalid_output')
                self.assertIsNone(result['proposal'])
                self.assertGreater(result['cost_usd'], 0)
                self.assertEqual(result['held_usd'], 0)
                self.assertEqual(post.call_count, 1)
                with closing(sqlite3.connect(ledger.path)) as c:
                    receipt = json.loads(c.execute('SELECT receipt_json FROM requests').fetchone()[0])
                self.assertEqual(receipt['status'], 'invalid_output')
                self.assertIsNone(receipt['proposal'])

    def test_wrong_model_missing_id_or_tool_output_preserves_hold(self):
        variants = []
        for field, value in [('model', 'different-model'), ('id', None)]:
            item = response(); item[field] = value; variants.append(item)
        item = response(); item['output'][0]['role'] = 'user'; variants.append(item)
        item = response(); item['output'][0]['tool_calls'] = [{'name':'release'}]; variants.append(item)
        item = response(); item['output'].append(copy.deepcopy(item['output'][0])); variants.append(item)
        for index, item in enumerate(variants):
            with self.subTest(index=index):
                ledger = p.Ledger('adaption', 1, 1, self.root / f'bad-{index}.sqlite3')
                self.client = p.ModelClient('adaption', 'fixture-model', ledger, max_output_tokens=100,
                                           timeout=1, authorization=authorization(ledger, provider='adaption'))
                with self.assertRaises(p.ProviderError):
                    self.recommend(item)
                self.assertTrue(ledger.snapshot()['halted'])
                self.assertGreater(ledger.run_reserved, 0)

    def test_truncated_json_does_not_become_valid_proposal(self):
        item = response(); item['status'] = 'incomplete'
        item['incomplete_details'] = {'reason': 'max_output_tokens'}
        result, post = self.recommend(item)
        self.assertEqual(result['status'], 'invalid_output')
        self.assertTrue(result['truncated'])
        self.assertIsNone(result['proposal'])
        self.assertEqual(post.call_count, 1)

    def test_timeout_preserves_hold(self):
        self.assertTrue(hasattr(self.client, 'recommend'), 'strict supervisor interface missing')
        with patch.object(p, '_post', side_effect=TimeoutError('untrusted message')) as post:
            with self.assertRaises(p.ProviderError):
                self.client.recommend(facts(), 'raw')
        self.assertEqual(post.call_count, 1)
        self.assertTrue(self.ledger.snapshot()['halted'])
        with patch.object(p, '_post') as post:
            with self.assertRaises(p.ProviderError):
                self.client.recommend(facts(), 'raw')
            post.assert_not_called()


class CalibrationRunnerTests(SyntheticSourceTestCase):
    def setUp(self):
        super().setUp()
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        substitute = patch.object(p, 'LEDGER_DIR', self.root)
        substitute.start(); self.addCleanup(substitute.stop)
        self.ledger = p.Ledger('adaption', 1, 1, run_id='one-calibration')
        self.record = authorization(self.ledger, provider='adaption')
        self.record['request_limit'] = 1
        self.auth_path = self.root / 'authorization.json'
        self.write_record()
        source = patch('fleet_witness.swarm.operator.require_committed_source')
        source.start(); self.addCleanup(source.stop)
        key = patch.object(p, '_env_key', return_value='synthetic-private-key')
        key.start(); self.addCleanup(key.stop)

    def write_record(self):
        self.auth_path.write_text(json.dumps(self.record))
        self.auth_path.chmod(0o600)

    def run_request(self, directory='result', live=True):
        self.assertIsNotNone(calibration, 'bounded calibration runner missing')
        return calibration.run_calibration(self.auth_path, self.root / directory, live=live)

    def test_explicit_live_selection_required_before_any_key_or_network(self):
        self.assertIsNotNone(calibration, 'bounded calibration runner missing')
        with patch.object(p, '_env_key', side_effect=AssertionError('key accessed')), \
                patch.object(p, '_post', side_effect=AssertionError('network accessed')):
            with self.assertRaises(ValueError):
                self.run_request(live=False)
        self.assertFalse((self.root / 'result').exists())

    def test_one_request_records_private_manifest_result_and_full_cap_reservation(self):
        with patch.object(p, '_post', return_value=json.dumps(response()).encode()) as post:
            result = self.run_request()
        self.assertEqual(post.call_count, 1)
        self.assertEqual(result['outcome']['status'], 'succeeded')
        self.assertEqual(result['mode'], 'live-calibration')
        self.assertFalse(result['confirmatory'])
        self.assertIsNone(result['controller_effect'])
        initial = json.loads((self.root / 'result' / 'manifest.json').read_text())
        self.assertEqual(initial['phase'], 'prepared')
        self.assertEqual(json.loads(post.call_args.args[2]['input']), initial['model_visible']['facts'])
        with closing(sqlite3.connect(self.ledger.path)) as c:
            self.assertEqual(c.execute('SELECT reserved FROM requests').fetchone()[0], 1_000_000_000)
        for name in ('manifest.json', 'result.json'):
            self.assertEqual((self.root / 'result' / name).stat().st_mode & 0o777, 0o600)
        self.assertEqual((self.root / 'result').stat().st_mode & 0o777, 0o700)

    def test_noncanonical_ledger_or_expanded_envelope_refused_before_key(self):
        variants = [('ledger_path', str(self.root / 'other.sqlite3')), ('request_limit', 2),
                    ('run_cap_usd', '1.000000001'), ('max_output_tokens', 257),
                    ('timeout_s', 31), ('purpose', 'confirmatory')]
        initial = copy.deepcopy(self.record)
        for name, value in variants:
            with self.subTest(name=name):
                self.record = {**initial, name:value}; self.write_record()
                with patch.object(p, '_env_key', side_effect=AssertionError('key accessed')), \
                        patch.object(p, '_post', side_effect=AssertionError('network accessed')):
                    with self.assertRaises((ValueError, p.ProviderError)):
                        self.run_request()
        self.assertFalse((self.root / 'result').exists())

    def test_reusing_authorization_with_new_output_does_not_dispatch_again(self):
        with patch.object(p, '_post', return_value=json.dumps(response()).encode()) as post:
            self.run_request()
            result = self.run_request('second-result')
        self.assertEqual(post.call_count, 1)
        self.assertEqual(result['outcome']['status'], 'refused')
        self.assertEqual(result['outcome']['provider_attempts'], 0)

    def test_timeout_keeps_manifest_hold_and_failure_result(self):
        with patch.object(p, '_post', side_effect=TimeoutError('secret exception')) as post:
            result = self.run_request()
        self.assertEqual(post.call_count, 1)
        self.assertEqual(result['outcome']['status'], 'unresolved')
        self.assertEqual(result['outcome']['held_usd'], 1)
        self.assertTrue((self.root / 'result' / 'manifest.json').exists())
        self.assertNotIn('secret exception', (self.root / 'result' / 'result.json').read_text())

    def test_crash_after_dispatch_keeps_initial_receipt_without_fabricated_result(self):
        with patch.object(p, '_post', side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                self.run_request()
        self.assertTrue((self.root / 'result' / 'manifest.json').exists())
        self.assertFalse((self.root / 'result' / 'result.json').exists())
        self.assertEqual(self.ledger.run_reserved, 1)
        self.assertTrue(self.ledger.snapshot()['halted'])

    def test_existing_output_or_symlink_cannot_be_overwritten(self):
        target = self.root / 'result'; target.mkdir()
        (target / 'precious.txt').write_text('retain')
        with patch.object(p, '_post', side_effect=AssertionError('network accessed')):
            with self.assertRaises((ValueError, FileExistsError)):
                self.run_request()
            (self.root / 'alias').symlink_to(target, target_is_directory=True)
            with self.assertRaises(ValueError):
                self.run_request('alias')
        self.assertEqual((target / 'precious.txt').read_text(), 'retain')

    def test_atomic_receipt_failure_never_returns_proposal(self):
        with closing(sqlite3.connect(self.ledger.path)) as c:
            c.execute("CREATE TRIGGER fail_settlement BEFORE UPDATE ON requests WHEN NEW.status='succeeded' BEGIN SELECT RAISE(ABORT,'fixture receipt failure'); END")
        with patch.object(p, '_post', return_value=json.dumps(response()).encode()):
            result = self.run_request()
        self.assertEqual(result['outcome']['status'], 'unresolved')
        self.assertTrue(self.ledger.snapshot()['halted'])
        self.assertIsNone(result['outcome'].get('proposal'))


if __name__ == '__main__':
    unittest.main()
