"""Offline behavioral tests; these never read a real key or contact a provider."""
import concurrent.futures
from contextlib import closing
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest

try:
    from fleet_witness.live_gateway import LiveBudgetError, LiveLedger, new_authorization
except ImportError:
    LiveLedger = None


class LiveLedgerTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(LiveLedger, 'live accounting is not implemented')
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.directory = Path(temp.name)
        self.path = self.directory / 'live-ledger.sqlite3'
        self.authorization = new_authorization(int(time.time()) + 300, 'a' * 64)
        self.facts = dict(run_id='opaque-run', artifact_digest='sha256:synthetic',
                          decision_time_policy={'allowed': True, 'version': 1},
                          receipts=[], reviewer_verdict='deny', reviewer_statement='Synthetic statement')
        self.ledger = LiveLedger(self.path, self.authorization)

    def test_authorization_is_closed_small_and_provider_specific(self):
        auth = self.authorization
        self.assertEqual(auth['model'], 'gemma-4-31b-it')
        self.assertEqual(auth['mode'], 'offline-calibration-fixture')
        self.assertEqual(auth['budget_microcredits'], 1_000_000)
        self.assertEqual(auth['request_limit'], 1)
        self.assertEqual(auth['timeout_seconds'], 30)
        self.assertEqual(auth['context_tokens'], 256_000)
        self.assertEqual(auth['input_rate_microcredits_per_million'], 90_000)
        self.assertEqual(auth['output_rate_microcredits_per_million'], 340_000)
        for bad in ('', 'A' * 64, 'a' * 63):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                new_authorization(int(time.time()) + 100, bad)

    def test_reserve_persists_exact_closed_input_and_full_one_credit_hold(self):
        self.ledger.reserve('private-request', self.facts, 'raw')
        self.facts['reviewer_statement'] = 'changed later'
        state = LiveLedger(self.path, self.authorization).snapshot()
        self.assertEqual(state['held_microcredits'], 1_000_000)
        self.assertEqual(state['available_microcredits'], 0)
        request = state['requests']['private-request']
        self.assertEqual(request['status'], 'reserved')
        self.assertEqual(request['model_input']['facts']['reviewer_statement'], 'Synthetic statement')
        self.assertNotIn('private-request', str(request['model_input']))
        self.assertEqual(set(request['model_input']), {'instruction', 'facts'})

    def test_concurrent_connections_cannot_each_reserve_the_single_budget(self):
        def reserve(index):
            ledger = LiveLedger(self.path, self.authorization)
            try:
                ledger.reserve(f'request-{index}', self.facts, 'raw')
                return True
            except LiveBudgetError:
                return False
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
            accepted = list(pool.map(reserve, range(5)))
        self.assertEqual(sum(accepted), 1)
        self.assertEqual(self.ledger.snapshot()['held_microcredits'], 1_000_000)

    def test_separate_processes_share_the_single_calibration_budget(self):
        program = '''import json,sys
from fleet_witness.live_gateway import LiveBudgetError, LiveLedger
ledger=LiveLedger(sys.argv[1],json.loads(sys.argv[2]))
try:
 ledger.reserve(sys.argv[3],json.loads(sys.argv[4]),'raw')
 print('accepted')
except LiveBudgetError:
 print('rejected')
'''
        children = [subprocess.Popen([sys.executable, '-c', program, str(self.path), json.dumps(self.authorization),
                                      f'process-{index}', json.dumps(self.facts)],
                                     stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                    for index in range(4)]
        results = [child.communicate(timeout=15) for child in children]
        self.assertTrue(all(child.returncode == 0 for child in children), results)
        self.assertEqual([out.strip() for out, _ in results].count('accepted'), 1)
        self.assertEqual([out.strip() for out, _ in results].count('rejected'), 3)
        self.assertEqual(self.ledger.snapshot()['held_microcredits'], 1_000_000)

    def test_dispatch_survives_restart_and_refuses_retries(self):
        self.ledger.reserve('once', self.facts, 'raw')
        self.ledger.dispatch('once')
        reopened = LiveLedger(self.path, self.authorization)
        self.assertEqual(reopened.snapshot()['requests']['once']['status'], 'dispatched')
        self.assertEqual(reopened.snapshot()['held_microcredits'], 1_000_000)
        with self.assertRaises((ValueError, LiveBudgetError)):
            reopened.reserve('once', self.facts, 'raw')
        with self.assertRaises(LiveBudgetError):
            reopened.reserve('different', self.facts, 'raw')

    def test_audit_failure_rolls_back_reservation(self):
        with closing(sqlite3.connect(self.path)) as c, c:
            c.execute("CREATE TRIGGER reject_audit BEFORE INSERT ON audit BEGIN SELECT RAISE(ABORT, 'audit failure'); END")
        with self.assertRaises(sqlite3.IntegrityError):
            self.ledger.reserve('fail', self.facts, 'raw')
        self.assertEqual(self.ledger.snapshot()['requests'], {})
        self.assertEqual(self.ledger.snapshot()['available_microcredits'], 1_000_000)

    def test_existing_authorization_cannot_be_replaced(self):
        changed = dict(self.authorization, budget_microcredits=2_000_000)
        with self.assertRaises(ValueError):
            LiveLedger(self.path, changed)
        self.assertEqual(LiveLedger(self.path, self.authorization).snapshot()['budget_microcredits'], 1_000_000)

    def test_expired_authorization_cannot_dispatch(self):
        expired = new_authorization(int(time.time()) - 1, 'a' * 64)
        ledger = LiveLedger(self.directory / 'expired.sqlite3', expired)
        with self.assertRaises(LiveBudgetError):
            ledger.reserve('expired', self.facts, 'raw')
        self.assertEqual(ledger.snapshot()['requests'], {})

    def test_rejects_unknown_fields_before_reservation(self):
        with self.assertRaises(ValueError):
            self.ledger.reserve('invalid', dict(self.facts, hidden_truth='secret'), 'raw')
        self.assertEqual(self.ledger.snapshot()['requests'], {})

    def test_owner_private_ledger_refuses_unsafe_file(self):
        self.assertEqual(self.path.stat().st_mode & 0o777, 0o600)
        alias = self.directory / 'alias.sqlite3'
        alias.symlink_to(self.path)
        with self.assertRaises((ValueError, OSError)):
            LiveLedger(alias, self.authorization)
        alias.unlink()
        os.link(self.path, alias)
        with self.assertRaises(ValueError):
            LiveLedger(alias, self.authorization)

    def reply(self, *, input_tokens=100, output_tokens=20, text=None):
        if text is None:
            text = '{"recommendation":"deny","reason":"No valid evidence"}'
        return {'id': 'resp_123', 'object': 'response', 'status': 'completed',
                'model': 'gemma-4-31b-it',
                'output': [{'type': 'message', 'role': 'assistant',
                            'content': [{'type': 'output_text', 'text': text}]}],
                'output_text': text,
                'usage': {'input_tokens': input_tokens, 'output_tokens': output_tokens,
                          'total_tokens': input_tokens + output_tokens}}

    def pending(self, request='pending'):
        self.ledger.reserve(request, self.facts, 'raw')
        self.ledger.dispatch(request)

    def test_valid_response_settles_fixed_point_cost_and_preserves_result(self):
        self.pending()
        result = self.ledger.settle('pending', self.reply())
        self.assertEqual(result['mode'], 'offline-calibration-fixture')
        self.assertEqual(result['status'], 'completed')
        self.assertEqual(result['recommendation'], 'deny')
        self.assertEqual(result['usage'], {'input_tokens': 100, 'output_tokens': 20, 'total_tokens': 120})
        self.assertEqual(result['estimated_microcredits'], 16)
        reopened = LiveLedger(self.path, self.authorization).snapshot()
        self.assertEqual(reopened['spent_microcredits'], 16)
        self.assertEqual(reopened['held_microcredits'], 0)
        self.assertEqual(reopened['requests']['pending']['result'], result)

    def test_reported_cached_and_reasoning_details_survive_for_reconciliation(self):
        self.pending()
        response = self.reply()
        response['usage']['input_tokens_details'] = {'cached_tokens': 10}
        response['usage']['output_tokens_details'] = {'reasoning_tokens': 5}
        result = self.ledger.settle('pending', response)
        self.assertEqual(result['usage']['input_tokens_details'], {'cached_tokens': 10})
        self.assertEqual(result['usage']['output_tokens_details'], {'reasoning_tokens': 5})
        self.assertEqual(LiveLedger(self.path, self.authorization).snapshot()['requests']['pending']['result'], result)

    def test_mutating_returned_authorization_cannot_change_spending_or_rates(self):
        self.pending()
        exposed = self.ledger.authorization
        exposed['input_rate_microcredits_per_million'] = 0
        exposed['output_rate_microcredits_per_million'] = 0
        result = self.ledger.settle('pending', self.reply())
        self.assertEqual(result['estimated_microcredits'], 16)
        self.assertEqual(self.ledger.authorization['input_rate_microcredits_per_million'], 90_000)

    def test_persisted_authorization_change_is_detected_before_settlement(self):
        self.pending()
        with closing(sqlite3.connect(self.path)) as c, c:
            altered = dict(self.authorization, output_rate_microcredits_per_million=0)
            c.execute('UPDATE authorization SET data=? WHERE id=1', (json.dumps(altered, sort_keys=True, separators=(',', ':')),))
        with self.assertRaises(ValueError):
            self.ledger.settle('pending', self.reply())
        with closing(sqlite3.connect(self.path)) as c:
            self.assertEqual(c.execute("SELECT status FROM requests WHERE id='pending'").fetchone()[0], 'dispatched')

    def test_snapshot_has_consistent_shape_before_and_after_completion(self):
        self.pending()
        before = self.ledger.snapshot()['requests']['pending']
        self.ledger.settle('pending', self.reply())
        after = self.ledger.snapshot()['requests']['pending']
        self.assertEqual(set(before), set(after))
        self.assertNotIn('result_json', before)

    def test_invalid_model_output_is_not_a_correct_denial_but_usage_settles(self):
        self.pending()
        result = self.ledger.settle('pending', self.reply(text='not JSON'))
        self.assertEqual(result['status'], 'invalid_output')
        self.assertIsNone(result['recommendation'])
        self.assertEqual(self.ledger.snapshot()['spent_microcredits'], 16)

    def test_tool_call_is_invalid_output_and_never_becomes_a_proposal(self):
        self.pending()
        reply = self.reply()
        reply['output'].append({'type': 'function_call', 'name': 'release'})
        result = self.ledger.settle('pending', reply)
        self.assertEqual(result['status'], 'invalid_output')
        self.assertIsNone(result['recommendation'])

    def test_completed_status_with_error_or_nonfinal_item_retains_hold(self):
        for index, change in enumerate(('error', 'incomplete', 'nonfinal_item')):
            with self.subTest(change=change):
                ledger = LiveLedger(self.directory / f'contradiction-{index}.sqlite3', self.authorization)
                ledger.reserve('contradiction', self.facts, 'raw')
                ledger.dispatch('contradiction')
                response = self.reply()
                if change == 'error': response['error'] = {'code': 'server_error'}
                if change == 'incomplete': response['incomplete_details'] = {'reason': 'max_output_tokens'}
                if change == 'nonfinal_item': response['output'][0]['status'] = 'in_progress'
                with self.assertRaises(LiveBudgetError): ledger.settle('contradiction', response)
                state = ledger.snapshot()
                self.assertEqual(state['requests']['contradiction']['status'], 'unresolved')
                self.assertEqual(state['held_microcredits'], 1_000_000)

    def test_unresolved_response_preserves_sanitized_reconciliation_fields(self):
        self.pending()
        response = self.reply()
        response['model'] = 'different-model'
        response['error'] = {'message': 'untrusted secret exception text'}
        with self.assertRaises(LiveBudgetError): self.ledger.settle('pending', response)
        receipt = LiveLedger(self.path, self.authorization).snapshot()['requests']['pending']['result']
        self.assertEqual(receipt['provider_response_id'], 'resp_123')
        self.assertEqual(receipt['reported_model'], 'different-model')
        self.assertEqual(receipt['usage']['input_tokens'], 100)
        self.assertEqual(receipt['estimated_microcredits'], 16)
        self.assertNotIn('untrusted secret exception text', json.dumps(receipt))

    def test_missing_bad_or_excess_usage_halts_and_retains_liability(self):
        for index, change in enumerate(['missing', 'boolean', 'zero_input', 'zero_output', 'context', 'overflow']):
            with self.subTest(change=change):
                ledger = LiveLedger(self.directory / f'{index}.sqlite3', self.authorization)
                ledger.reserve('request', self.facts, 'raw')
                ledger.dispatch('request')
                reply = self.reply()
                if change == 'missing': del reply['usage']
                if change == 'boolean': reply['usage']['input_tokens'] = True
                if change == 'zero_input': reply = self.reply(input_tokens=0, output_tokens=20)
                if change == 'zero_output': reply = self.reply(input_tokens=100, output_tokens=0)
                if change == 'context': reply = self.reply(input_tokens=256_001, output_tokens=0)
                if change == 'overflow': reply = self.reply(input_tokens=0, output_tokens=4_000_000)
                with self.assertRaises(LiveBudgetError): ledger.settle('request', reply)
                state = LiveLedger(ledger.path, self.authorization).snapshot()
                self.assertTrue(state['halted'])
                self.assertGreaterEqual(state['held_microcredits'], 1_000_000)
                self.assertEqual(state['requests']['request']['status'], 'unresolved')
                if change == 'overflow': self.assertGreater(state['held_microcredits'], 1_000_000)

    def test_timeout_is_unresolved_after_restart_and_cannot_retry(self):
        self.pending()
        self.ledger.uncertain('pending', 'timeout')
        state = LiveLedger(self.path, self.authorization).snapshot()
        self.assertTrue(state['halted'])
        self.assertEqual(state['requests']['pending']['status'], 'unresolved')
        self.assertEqual(state['held_microcredits'], 1_000_000)
        with self.assertRaises(LiveBudgetError): self.ledger.reserve('retry', self.facts, 'raw')

    def test_audit_failure_rolls_back_settlement(self):
        self.pending()
        with closing(sqlite3.connect(self.path)) as c, c:
            c.execute("CREATE TRIGGER reject_settle BEFORE INSERT ON audit WHEN NEW.kind='settled' BEGIN SELECT RAISE(ABORT, 'audit failure'); END")
        with self.assertRaises(sqlite3.IntegrityError): self.ledger.settle('pending', self.reply())
        state = self.ledger.snapshot()
        self.assertEqual(state['requests']['pending']['status'], 'dispatched')
        self.assertEqual(state['held_microcredits'], 1_000_000)
        self.assertIsNone(state['requests']['pending']['result'])


class ProviderWireTests(unittest.TestCase):
    def setUp(self):
        self.facts = dict(run_id='opaque-run', artifact_digest='sha256:synthetic',
                          decision_time_policy={'allowed': True, 'version': 1},
                          receipts=[], reviewer_verdict='deny', reviewer_statement='Synthetic statement')

    def test_request_is_closed_and_turns_off_tools_memory_and_storage(self):
        from fleet_witness.live_gateway import build_provider_request
        request = build_provider_request(self.facts, 'raw')
        self.assertEqual(request['model'], 'gemma-4-31b-it')
        self.assertEqual(request['max_output_tokens'], 256)
        self.assertEqual(request['tools'], [])
        self.assertEqual(request['tool_choice'], 'none')
        self.assertIs(request['store'], False)
        self.assertIs(request['agentic_memory'], False)
        self.assertEqual(set(request), {'model', 'input', 'max_output_tokens', 'tools',
                                        'tool_choice', 'store', 'agentic_memory', 'background'})
        visible = json.loads(request['input'])
        self.assertEqual(set(visible), {'instruction', 'facts'})
        self.assertNotIn('private-request', request['input'])
        self.assertNotIn('hidden_truth', request['input'])

    def test_unallowlisted_input_is_rejected_before_request(self):
        from fleet_witness.live_gateway import build_provider_request
        with self.assertRaises(ValueError):
            build_provider_request(dict(self.facts, hidden_truth='secret'), 'raw')

    def test_response_parser_rejects_duplicate_keys_invalid_bytes_and_nonobjects(self):
        from fleet_witness.live_gateway import parse_provider_response
        for raw in [b'{"status":"ok","status":"bad"}', b'\xff', b'[]', b'{"x":NaN}', b'{"x":1e999}']:
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                parse_provider_response(raw)

    def test_response_parser_enforces_byte_and_depth_caps(self):
        from fleet_witness.live_gateway import parse_provider_response
        with self.assertRaises(ValueError):
            parse_provider_response(b' ' * 65_537)
        deep = b'{"a":' * 40 + b'0' + b'}' * 40
        with self.assertRaises(ValueError):
            parse_provider_response(deep)

    def test_response_parser_returns_detached_json_object(self):
        from fleet_witness.live_gateway import parse_provider_response
        self.assertEqual(parse_provider_response(b'{"status":"completed","usage":{"input_tokens":1}}'),
                         {'status': 'completed', 'usage': {'input_tokens': 1}})


class FixtureRunnerTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.path = Path(temp.name) / 'fixture.sqlite3'
        self.auth = new_authorization(int(time.time()) + 300, 'a' * 64)
        self.ledger = LiveLedger(self.path, self.auth)
        self.facts = dict(run_id='opaque-run', artifact_digest='sha256:synthetic',
                          decision_time_policy={'allowed': True, 'version': 1},
                          receipts=[], reviewer_verdict='deny', reviewer_statement='Synthetic statement')
        text = '{"recommendation":"deny","reason":"No safety evidence"}'
        self.response = {'id': 'resp_fixture', 'object': 'response', 'status': 'completed',
                         'model': 'gemma-4-31b-it',
                         'output': [{'type': 'message', 'role': 'assistant',
                                     'content': [{'type': 'output_text', 'text': text}]}],
                         'output_text': text,
                         'usage': {'input_tokens': 100, 'output_tokens': 20, 'total_tokens': 120}}

    def test_fixture_response_flows_through_budget_and_is_never_labeled_live(self):
        from fleet_witness.live_gateway import FixtureRunner, FixtureTransport
        transport = FixtureTransport([json.dumps(self.response).encode()])
        result = FixtureRunner(self.ledger, transport).run('fixture-1', self.facts, 'raw')
        self.assertEqual(result['mode'], 'offline-calibration-fixture')
        self.assertEqual(result['recommendation'], 'deny')
        self.assertEqual(len(transport.requests), 1)
        self.assertEqual(json.loads(transport.requests[0]['input']),
                         self.ledger.snapshot()['requests']['fixture-1']['model_input'])
        self.assertEqual(self.ledger.snapshot()['spent_microcredits'], 16)

    def test_malformed_fixture_response_is_unresolved_and_never_retried(self):
        from fleet_witness.live_gateway import FixtureRunner, FixtureTransport
        transport = FixtureTransport([b'{bad json'])
        result = FixtureRunner(self.ledger, transport).run('fixture-2', self.facts, 'raw')
        self.assertEqual(result['mode'], 'offline-calibration-fixture')
        self.assertEqual(result['status'], 'unresolved')
        self.assertEqual(self.ledger.snapshot()['held_microcredits'], 1_000_000)
        self.assertTrue(self.ledger.snapshot()['halted'])
        with self.assertRaises((ValueError, LiveBudgetError)):
            FixtureRunner(self.ledger, transport).run('fixture-2', self.facts, 'raw')
        self.assertEqual(len(transport.requests), 1)

    def test_arbitrary_transport_is_refused_before_reservation(self):
        from fleet_witness.live_gateway import FixtureRunner
        with self.assertRaises(ValueError):
            FixtureRunner(self.ledger, object())
        self.assertEqual(self.ledger.snapshot()['requests'], {})


if __name__ == '__main__':
    unittest.main()
