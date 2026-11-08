"""Offline gateway boundaries use real SQLite accounting and an inert provider."""
import concurrent.futures
from contextlib import closing
import hashlib
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
        with closing(sqlite3.connect(self.database)) as connection, connection:
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
        with closing(sqlite3.connect(self.database)) as connection, connection:
            tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        self.assertNotIn('releases', tables)

    def test_receipt_persists_snapshot_and_result_across_restart(self):
        provider = FakeProvider([self.reply()])
        result = Gateway(self.ledger, provider).run('durable', self.facts, 'raw', 3, 128)
        self.facts['reviewer_statement'] = 'mutated after dispatch'
        reopened = BudgetLedger(self.database, 10)
        receipt = reopened.receipt('durable')
        self.assertEqual(receipt['mode'], 'offline-fake')
        self.assertEqual(receipt['model_input'], provider.calls[0]['input'])
        canonical = json.dumps(receipt['model_input'], ensure_ascii=True, sort_keys=True, separators=(',', ':'))
        self.assertEqual(receipt['input_sha256'], hashlib.sha256(canonical.encode('utf-8')).hexdigest())
        self.assertEqual(receipt['max_output_tokens'], 128)
        self.assertEqual(receipt['raw_output'], self.reply().output_text)
        self.assertEqual(receipt['result'], result)
        receipt['model_input']['facts']['reviewer_statement'] = 'local mutation'
        self.assertNotEqual(reopened.receipt('durable')['model_input']['facts']['reviewer_statement'], 'local mutation')
        self.assertIsNone(reopened.receipt('missing'))

    def test_crash_after_settlement_preserves_receipt_and_refuses_retry(self):
        original = self.ledger.settle
        def settle_then_crash(*args, **kwargs):
            original(*args, **kwargs)
            raise RuntimeError('simulated caller crash')
        self.ledger.settle = settle_then_crash
        with self.assertRaisesRegex(RuntimeError, 'simulated caller crash'):
            Gateway(self.ledger, FakeProvider([self.reply()])).run('crash-after-settle', self.facts, 'raw', 3)
        reopened = BudgetLedger(self.database, 10)
        self.assertEqual(reopened.receipt('crash-after-settle')['result']['recommendation'], 'approve')
        self.assertEqual(reopened.snapshot()['spent_units'], 2)
        with self.assertRaises(ValueError):
            Gateway(reopened, FakeProvider([self.reply()])).run('crash-after-settle', self.facts, 'raw', 3)

    def test_receipt_write_failure_rolls_back_settlement_and_retains_hold(self):
        with closing(sqlite3.connect(self.database)) as connection, connection:
            connection.execute("CREATE TRIGGER reject_receipt_update BEFORE UPDATE ON gateway_receipts BEGIN SELECT RAISE(ABORT, 'receipt unavailable'); END")
        with self.assertRaises(sqlite3.IntegrityError):
            Gateway(self.ledger, FakeProvider([self.reply()])).run('receipt-failure', self.facts, 'raw', 3)
        reopened = BudgetLedger(self.database, 10)
        self.assertEqual(reopened.snapshot()['requests']['receipt-failure']['status'], 'dispatched')
        self.assertEqual(reopened.snapshot()['held_units'], 3)
        self.assertIsNone(reopened.receipt('receipt-failure')['result'])
        with self.assertRaises(BudgetError):
            reopened.reserve('after-failure', 1)

    def test_missing_receipt_cannot_settle_and_lose_evidence(self):
        provider = FakeProvider([self.reply()])
        original = provider.generate
        def lose_receipt(payload, max_output_tokens):
            with closing(sqlite3.connect(self.database)) as connection, connection:
                connection.execute("DELETE FROM gateway_receipts WHERE request_id='missing-receipt'")
            return original(payload, max_output_tokens)
        provider.generate = lose_receipt
        with self.assertRaises(sqlite3.IntegrityError):
            Gateway(self.ledger, provider).run('missing-receipt', self.facts, 'raw', 3)
        state = BudgetLedger(self.database, 10).snapshot()
        self.assertEqual(state['requests']['missing-receipt']['status'], 'dispatched')
        self.assertEqual(state['held_units'], 3)

    def test_receipted_request_cannot_transition_without_its_result(self):
        for transition in ('settle', 'uncertain'):
            with self.subTest(transition=transition):
                ledger = BudgetLedger(self.database.with_name(transition + '.sqlite3'), 10)
                with self.assertRaises(KeyboardInterrupt):
                    Gateway(ledger, FakeProvider([KeyboardInterrupt()])).run('pending', self.facts, 'raw', 3)
                with self.assertRaises(sqlite3.IntegrityError):
                    if transition == 'settle':
                        ledger.settle('pending', 1, 'completed')
                    else:
                        ledger.uncertain('pending')
                self.assertEqual(ledger.snapshot()['requests']['pending']['status'], 'dispatched')
                self.assertEqual(ledger.snapshot()['held_units'], 3)
                self.assertIsNone(ledger.receipt('pending')['result'])

    def test_accounting_error_receipt_has_no_recommendation(self):
        result = Gateway(self.ledger, FakeProvider([self.reply(units=7)])).run('overrun', self.facts, 'raw', 3)
        receipt = BudgetLedger(self.database, 10).receipt('overrun')
        self.assertEqual(receipt['result'], result)
        self.assertEqual(result['status'], 'accounting_error')
        self.assertIsNone(result['recommendation'])
        self.assertEqual(self.ledger.snapshot()['held_units'], 7)

    def test_receipt_result_must_match_request_identity_and_mode(self):
        with self.assertRaises(KeyboardInterrupt):
            Gateway(self.ledger, FakeProvider([KeyboardInterrupt()])).run('pending', self.facts, 'raw', 3)
        for invalid in [
            {'mode': 'offline-fake', 'request_id': 'other', 'status': 'completed', 'recommendation': 'approve', 'reason': 'x'},
            {'mode': 'live-model', 'request_id': 'pending', 'status': 'completed', 'recommendation': 'approve', 'reason': 'x'},
            {'mode': 'offline-fake', 'request_id': 'pending', 'status': 'completed', 'recommendation': 'approve', 'reason': 'x', 'extra': 'bad'},
        ]:
            with self.subTest(invalid=invalid), self.assertRaises((ValueError, sqlite3.IntegrityError)):
                self.ledger.settle('pending', 1, 'completed', result=invalid)
            self.assertEqual(self.ledger.snapshot()['requests']['pending']['status'], 'dispatched')
            self.assertIsNone(self.ledger.receipt('pending')['result'])

    def test_reservation_receipt_failure_does_not_call_provider(self):
        with closing(sqlite3.connect(self.database)) as connection, connection:
            connection.execute("CREATE TRIGGER reject_receipt_insert BEFORE INSERT ON gateway_receipts BEGIN SELECT RAISE(ABORT, 'receipt unavailable'); END")
        provider = FakeProvider([self.reply()])
        with self.assertRaises(sqlite3.IntegrityError):
            Gateway(self.ledger, provider).run('reservation-failure', self.facts, 'raw', 3)
        self.assertEqual(provider.calls, [])
        self.assertEqual(self.ledger.snapshot()['requests'], {})
        self.assertIsNone(self.ledger.receipt('reservation-failure'))

    def test_audit_failure_rolls_back_unresolved_and_accounting_error(self):
        for name, reply in [('uncertain', TimeoutError('private')), ('overrun', self.reply(units=7))]:
            with self.subTest(name=name):
                ledger = BudgetLedger(self.database.with_name(name + '-audit.sqlite3'), 10)
                with closing(sqlite3.connect(ledger.database)) as connection, connection:
                    connection.execute("CREATE TRIGGER reject_outcome_audit BEFORE INSERT ON audit WHEN NEW.kind IN ('unresolved','accounting_error') BEGIN SELECT RAISE(ABORT, 'audit unavailable'); END")
                with self.assertRaises(sqlite3.IntegrityError):
                    Gateway(ledger, FakeProvider([reply])).run(name, self.facts, 'raw', 3)
                state = ledger.snapshot()
                self.assertEqual(state['requests'][name]['status'], 'dispatched')
                self.assertEqual(state['held_units'], 3)
                self.assertIsNone(ledger.receipt(name)['result'])

    def test_invalid_and_oversized_raw_outputs_are_not_persisted(self):
        for index, raw in enumerate([chr(0xD800), 'x' * 32769]):
            with self.subTest(index=index):
                ledger = BudgetLedger(self.database.with_name(f'unsafe-{index}.sqlite3'), 10)
                result = Gateway(ledger, FakeProvider([self.reply(raw)])).run('unsafe', self.facts, 'raw', 3)
                receipt = BudgetLedger(ledger.database, 10).receipt('unsafe')
                self.assertEqual(result['status'], 'invalid_output')
                self.assertEqual(receipt['result'], result)
                self.assertIsNone(receipt['raw_output'])
                self.assertEqual(ledger.snapshot()['spent_units'], 2)

    def test_unresolved_error_receipt_does_not_include_exception_message(self):
        result = Gateway(self.ledger, FakeProvider([TimeoutError('secret exception text')])).run('err', self.facts, 'raw', 3)
        reopened = BudgetLedger(self.database, 10)
        receipt = reopened.receipt('err')
        self.assertEqual(receipt['result'], result)
        self.assertIsNone(receipt['raw_output'])
        self.assertNotIn('secret exception text', json.dumps(receipt))
        self.assertEqual(reopened.snapshot()['held_units'], 3)
        self.assertTrue(reopened.snapshot()['halted'])

    def test_empty_output_and_wrong_reply_type_have_distinct_receipts(self):
        empty = Gateway(self.ledger, FakeProvider([ProviderReply('', 1)])).run('empty', self.facts, 'raw', 2)
        self.assertEqual(empty['status'], 'invalid_output')
        self.assertEqual(self.ledger.receipt('empty')['raw_output'], '')
        wrong = Gateway(self.ledger, FakeProvider([None])).run('wrong-type', self.facts, 'raw', 2)
        self.assertEqual(wrong['status'], 'accounting_error')
        self.assertEqual(self.ledger.receipt('wrong-type')['result'], wrong)
        self.assertIsNone(self.ledger.receipt('wrong-type')['raw_output'])
        self.assertEqual(self.ledger.snapshot()['requests']['wrong-type']['outcome'], 'accounting_error')

    def test_legacy_unresolved_request_survives_receipt_schema_migration(self):
        legacy = self.database.with_name('legacy.sqlite3')
        with closing(sqlite3.connect(legacy)) as connection, connection:
            connection.executescript("""
                CREATE TABLE budget (id INTEGER PRIMARY KEY CHECK(id=1), limit_units INTEGER NOT NULL, halted INTEGER NOT NULL CHECK(halted IN (0,1)));
                CREATE TABLE requests (id TEXT PRIMARY KEY, reserved_units INTEGER NOT NULL, actual_units INTEGER, status TEXT NOT NULL CHECK(status IN ('reserved','dispatched','settled','unresolved')), outcome TEXT);
                CREATE TABLE audit (seq INTEGER PRIMARY KEY AUTOINCREMENT, request_id TEXT, kind TEXT NOT NULL, details TEXT NOT NULL);
                INSERT INTO budget VALUES(1,10,1);
                INSERT INTO requests VALUES('old',4,NULL,'unresolved','provider_error');
                INSERT INTO requests VALUES('reserved',2,NULL,'reserved',NULL);
                INSERT INTO requests VALUES('dispatched',1,NULL,'dispatched',NULL);
                INSERT INTO requests VALUES('settled',3,2,'settled','completed');
                INSERT INTO audit(request_id,kind,details) VALUES('old','unresolved','{}');
            """)
        os.chmod(legacy, 0o600)
        reopened = BudgetLedger(legacy, 10)
        self.assertEqual(reopened.snapshot()['held_units'], 7)
        self.assertEqual(reopened.snapshot()['spent_units'], 2)
        self.assertTrue(reopened.snapshot()['halted'])
        self.assertEqual(reopened.snapshot()['requests']['old']['status'], 'unresolved')
        for request_id in ('old', 'reserved', 'dispatched', 'settled'):
            self.assertIsNone(reopened.receipt(request_id))
        with closing(sqlite3.connect(legacy)) as connection:
            self.assertEqual(connection.execute('SELECT request_id, kind, details FROM audit').fetchall(),
                             [('old', 'unresolved', '{}')])
        with self.assertRaises(BudgetError):
            reopened.reserve('new', 1)


if __name__ == '__main__':
    unittest.main()
