"""Offline gateway boundaries use real SQLite accounting and an inert provider."""
import concurrent.futures
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest

try:
    from fleet_witness.gateway import BudgetLedger, BudgetError, FakeProvider, Gateway, ProviderReply, provider_input
except ImportError:
    BudgetLedger = None


class GatewayTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(BudgetLedger, 'offline gateway foundation is not implemented')
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.database = Path(temporary.name) / 'budget.sqlite3'
        self.ledger = BudgetLedger(self.database, 10)
        self.facts = dict(run_id='opaque-run', artifact_digest='sha256:artifact',
            decision_time_policy={'allowed': True, 'version': 1}, reviewer_verdict='approve',
            reviewer_statement='Untrusted evidence text', receipts=[dict(issuer='build-issuer',
            claim='build_succeeded', scope='build', artifact_digest='sha256:artifact',
            run_id='opaque-run', signature='0' * 64)])

    def reply(self, text=None, units=2, **changes):
        return ProviderReply(text or '{"recommendation":"approve","reason":"A model proposal"}',
                             units, **changes)

    def test_provider_sees_equal_paired_facts_without_orchestration_metadata(self):
        provider = FakeProvider([self.reply(), self.reply()])
        gateway = Gateway(self.ledger, provider)
        raw = gateway.run('private-raw-request', self.facts, 'raw', 3)
        scoped = gateway.run('private-scoped-request', self.facts, 'scope_explicit', 3)
        self.assertEqual(raw['status'], 'completed')
        self.assertEqual(scoped['recommendation'], 'approve')
        a, b = [call['input'] for call in provider.calls]
        self.assertEqual(a['facts'], b['facts'])
        self.assertNotEqual(a['instruction'], b['instruction'])
        self.assertEqual(set(a), {'instruction', 'facts'})
        self.assertNotIn('private-', json.dumps(provider.calls))
        self.assertEqual(self.ledger.snapshot()['spent_units'], 4)

    def test_unknown_nested_or_sealed_inputs_fail_before_reservation_or_dispatch(self):
        provider = FakeProvider()
        gateway = Gateway(self.ledger, provider)
        variants = [dict(self.facts, scenario_truth=True), dict(self.facts, trial_id='hidden'),
                    dict(self.facts, decision_time_policy={'allowed': True, 'version': True}),
                    dict(self.facts, receipts=[dict(self.facts['receipts'][0], signing_key='forbidden')]),
                    dict(self.facts, reviewer_statement='x' * 32769)]
        for index, facts in enumerate(variants):
            with self.subTest(index=index), self.assertRaises(ValueError):
                gateway.run('rejected-' + str(index), facts, 'raw', 3)
        self.assertEqual(provider.calls, [])
        self.assertEqual(self.ledger.snapshot()['requests'], {})

    def test_caller_mutation_does_not_change_provider_input(self):
        prepared = provider_input(self.facts, 'raw')
        self.facts['receipts'][0]['scope'] = 'changed'
        self.facts['decision_time_policy']['allowed'] = False
        self.assertEqual(prepared['facts']['receipts'][0]['scope'], 'build')
        self.assertTrue(prepared['facts']['decision_time_policy']['allowed'])

    def test_budget_and_reservation_units_are_strict_bounded_integers(self):
        for value in [True, 0, -1, 1.5, '10', 2**63]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                BudgetLedger(self.database.with_name('invalid.sqlite3'), value)
        for value in [False, 0, -1, 1.5, '1', 2**63]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.ledger.reserve('invalid', value)
        self.assertEqual(self.ledger.snapshot()['available_units'], 10)

    def test_concurrent_reservations_cannot_exceed_shared_envelope(self):
        def reserve(index):
            ledger = BudgetLedger(self.database, 10)
            try:
                ledger.reserve('parallel-' + str(index), 3)
                return True
            except BudgetError:
                return False
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            accepted = list(pool.map(reserve, range(8)))
        self.assertEqual(sum(accepted), 3)
        self.assertEqual(self.ledger.snapshot()['held_units'], 9)
        self.assertEqual(self.ledger.snapshot()['available_units'], 1)

    def test_duplicate_request_never_dispatches_twice_even_after_settlement(self):
        provider = FakeProvider([self.reply(), self.reply()])
        gateway = Gateway(self.ledger, provider)
        gateway.run('once', self.facts, 'raw', 3)
        with self.assertRaises(ValueError):
            gateway.run('once', self.facts, 'raw', 3)
        self.assertEqual(len(provider.calls), 1)
        self.assertEqual(self.ledger.snapshot()['spent_units'], 2)

    def test_timeout_holds_budget_and_stops_new_dispatch_across_restart(self):
        provider = FakeProvider([TimeoutError('untrusted failure text')])
        result = Gateway(self.ledger, provider).run('timeout', self.facts, 'raw', 7)
        self.assertEqual(result['status'], 'provider_error')
        self.assertIsNone(result['recommendation'])
        reopened = BudgetLedger(self.database, 10)
        state = reopened.snapshot()
        self.assertEqual(state['held_units'], 7)
        self.assertTrue(state['halted'])
        self.assertEqual(state['requests']['timeout']['status'], 'unresolved')
        with self.assertRaises(BudgetError):
            reopened.reserve('not-a-retry', 1)

    def test_crash_after_dispatch_remains_reserved_and_is_not_retried(self):
        provider = FakeProvider([KeyboardInterrupt()])
        with self.assertRaises(KeyboardInterrupt):
            Gateway(self.ledger, provider).run('crash', self.facts, 'raw', 6)
        reopened = BudgetLedger(self.database, 10)
        self.assertEqual(reopened.snapshot()['held_units'], 6)
        self.assertEqual(reopened.snapshot()['requests']['crash']['status'], 'dispatched')
        with self.assertRaises(BudgetError):
            reopened.reserve('after-crash', 1)
        with self.assertRaises(ValueError):
            Gateway(reopened, provider).run('crash', self.facts, 'raw', 6)
        self.assertEqual(len(provider.calls), 1)

    def test_missing_or_excess_usage_retains_liability_and_halts(self):
        for name, units, held in [('missing', None, 3), ('excess', 5, 5), ('boolean', True, 3)]:
            with self.subTest(name=name):
                ledger = BudgetLedger(self.database.with_name(name + '.sqlite3'), 10)
                result = Gateway(ledger, FakeProvider([self.reply(units=units)])).run(name, self.facts, 'raw', 3)
                self.assertEqual(result['status'], 'accounting_error')
                self.assertIsNone(result['recommendation'])
                self.assertTrue(ledger.snapshot()['halted'])
                self.assertEqual(ledger.snapshot()['held_units'], held)

    def test_invalid_outputs_are_billed_without_becoming_model_denials(self):
        outputs = ['not JSON', '[]', '{"recommendation":"allow","reason":"bad enum"}',
                   '{"recommendation":"deny","reason":"x","tool":"release"}',
                   '{"recommendation":"approve","reason":null}', 'x' * 32769,
                   '{"recommendation":"approve","recommendation":"deny","reason":"duplicate"}',
                   chr(0xD800), json.dumps({'recommendation': 'approve', 'reason': chr(0xD800)})]
        for index, text in enumerate(outputs):
            with self.subTest(index=index):
                ledger = BudgetLedger(self.database.with_name(str(index) + '.sqlite3'), 10)
                try:
                    result = Gateway(ledger, FakeProvider([self.reply(text)])).run('output', self.facts, 'raw', 3)
                except UnicodeError:
                    self.fail('malformed Unicode must be recorded as invalid output with accounted usage')
                self.assertEqual(result['status'], 'invalid_output')
                self.assertIsNone(result['recommendation'])
                self.assertEqual(ledger.snapshot()['spent_units'], 2)
                self.assertEqual(ledger.snapshot()['held_units'], 0)

    def test_tool_items_and_incomplete_response_never_authorize_a_proposal(self):
        for changes in [dict(tool_calls=True), dict(status='incomplete')]:
            with self.subTest(changes=changes):
                ledger = BudgetLedger(self.database.with_name(str(len(changes)) + str(changes) + '.sqlite3'), 10)
                result = Gateway(ledger, FakeProvider([self.reply(**changes)])).run('tools', self.facts, 'raw', 3)
                self.assertEqual(result['status'], 'invalid_output')
                self.assertIsNone(result['recommendation'])
                self.assertEqual(ledger.snapshot()['spent_units'], 2)

    def test_terminal_provider_failures_are_accounted_separately_from_invalid_model_output(self):
        for status in ('failed', 'cancelled'):
            with self.subTest(status=status):
                ledger = BudgetLedger(self.database.with_name(status + '.sqlite3'), 10)
                result = Gateway(ledger, FakeProvider([self.reply(status=status)])).run('failed', self.facts, 'raw', 3)
                self.assertEqual(result['status'], 'provider_error')
                self.assertIsNone(result['recommendation'])
                self.assertEqual(ledger.snapshot()['spent_units'], 2)
                self.assertEqual(ledger.snapshot()['held_units'], 0)
                self.assertEqual(ledger.snapshot()['requests']['failed']['outcome'], 'provider_error')
                ledger.reserve('new-request', 1)

    def test_nonterminal_or_unknown_status_keeps_full_hold_even_with_reported_zero_usage(self):
        for status in ('in_progress', 'queued', 'unknown', None):
            with self.subTest(status=status):
                ledger = BudgetLedger(self.database.with_name(str(status) + '.sqlite3'), 10)
                result = Gateway(ledger, FakeProvider([self.reply(units=0, status=status)])).run('pending', self.facts, 'raw', 7)
                self.assertEqual(result['status'], 'provider_error')
                self.assertIsNone(result['recommendation'])
                self.assertEqual(ledger.snapshot()['spent_units'], 0)
                self.assertEqual(ledger.snapshot()['held_units'], 7)
                self.assertTrue(ledger.snapshot()['halted'])
                self.assertEqual(ledger.snapshot()['requests']['pending']['status'], 'unresolved')
                with self.assertRaises(BudgetError):
                    ledger.reserve('another', 1)

    def test_ledger_limit_cannot_be_silently_changed_after_restart(self):
        self.ledger.reserve('held', 4)
        with self.assertRaises(ValueError):
            BudgetLedger(self.database, 100)
        self.assertEqual(BudgetLedger(self.database, 10).snapshot()['held_units'], 4)

    def test_reservation_and_audit_are_atomic(self):
        with sqlite3.connect(self.database) as connection:
            connection.execute("CREATE TRIGGER reject_audit BEFORE INSERT ON audit BEGIN SELECT RAISE(ABORT, 'audit unavailable'); END")
        with self.assertRaises(sqlite3.IntegrityError):
            self.ledger.reserve('must-roll-back', 4)
        self.assertEqual(self.ledger.snapshot()['requests'], {})
        self.assertEqual(self.ledger.snapshot()['available_units'], 10)

    def test_ledger_file_is_private_and_symlink_or_hardlink_is_refused(self):
        self.assertEqual(self.database.stat().st_mode & 0o777, 0o600)
        alias = self.database.with_name('alias.sqlite3')
        alias.symlink_to(self.database)
        with self.assertRaises((ValueError, OSError)):
            BudgetLedger(alias, 10)
        alias.unlink()
        os.link(self.database, alias)
        with self.assertRaises(ValueError):
            BudgetLedger(alias, 10)

    def test_gateway_accepts_only_fake_mode_and_never_creates_release_state(self):
        provider = FakeProvider([self.reply()])
        provider.mode = 'live-model'
        with self.assertRaises(ValueError):
            Gateway(self.ledger, provider)
        result = Gateway(self.ledger, FakeProvider([self.reply()])).run('proposal', self.facts, 'raw', 3)
        self.assertEqual(result['mode'], 'offline-fake')
        self.assertEqual(result['recommendation'], 'approve')
        with sqlite3.connect(self.database) as connection:
            tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        self.assertNotIn('releases', tables)


if __name__ == '__main__':
    unittest.main()
