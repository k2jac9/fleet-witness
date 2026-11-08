"""Boundary tests use real SQLite state; expectations are hand-derived."""
import concurrent.futures
from pathlib import Path
import sqlite3
import tempfile
import unittest

try:
    from fleet_witness.controller import Controller
    from fleet_witness.evidence import issue_receipt
except ImportError:
    Controller = None


class ControllerTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(Controller, 'trusted controller has not been implemented')
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db = Path(self.tmp.name) / 'test.sqlite3'
        self.key = b'test-only-controller-key'
        self.controller = Controller(self.db, self.key)
        self.controller.set_policy('run-1', 'sha256:artifact', True)
        self.receipt = issue_receipt(self.key, issuer='safety-issuer', claim='release_safe',
                                     scope='release', artifact_digest='sha256:artifact', run_id='run-1')

    def decide(self, receipts=None, recommendation='approve', decision_id='decision-1'):
        return self.controller.record_decision(decision_id, 'run-1', 'sha256:artifact',
            recommendation, 'scripted proposal', [self.receipt] if receipts is None else receipts)

    def count(self, table):
        with sqlite3.connect(self.db) as conn:
            return conn.execute('SELECT count(*) FROM ' + table).fetchone()[0]

    def test_valid_release_commits_one_release_and_matching_audit(self):
        self.decide()
        attempt = self.controller.execute('decision-1', 'attempt-1')
        self.assertTrue(attempt['execution_authorized_at_attempt'])
        self.assertTrue(attempt['effect_occurred'])
        self.assertEqual(self.count('releases'), 1)
        with sqlite3.connect(self.db) as conn:
            self.assertEqual(conn.execute("SELECT count(*) FROM events WHERE kind='release_committed'").fetchone()[0], 1)

    def test_receipt_failures_deny_even_approved_proposals(self):
        variants = {
            'forged': {'signature': '0' * 64},
            'wrong-artifact': {'artifact_digest': 'sha256:other'},
            'wrong-run': {'run_id': 'run-2'},
            'wrong-scope': {'scope': 'build'},
            'wrong-claim': {'claim': 'build_succeeded'},
            'wrong-issuer': {'issuer': 'untrusted-issuer'},
        }
        for name, changes in variants.items():
            with self.subTest(name=name):
                fields = {k: v for k, v in self.receipt.items() if k != 'signature'}
                fields.update({k: v for k, v in changes.items() if k != 'signature'})
                receipt = issue_receipt(self.key, **fields)
                if 'signature' in changes:
                    receipt['signature'] = changes['signature']
                self.decide([receipt], decision_id=name)
                result = self.controller.execute(name, 'attempt-' + name)
                self.assertFalse(result['execution_authorized_at_attempt'])
                self.assertFalse(result['effect_occurred'])
        self.assertEqual(self.count('releases'), 0)

    def test_missing_and_malformed_receipts_fail_closed(self):
        for i, receipts in enumerate([[], [{}], [None], [{'signature': []}], [dict(self.receipt, extra='injected')]]):
            self.decide(receipts, decision_id=str(i))
            self.assertFalse(self.controller.execute(str(i), 'a' + str(i))['effect_occurred'])
        self.assertEqual(self.count('releases'), 0)

    def test_missing_policy_denies(self):
        with sqlite3.connect(self.db) as conn:
            conn.execute('DELETE FROM policies')
        self.decide()
        result = self.controller.execute('decision-1', 'attempt-1')
        self.assertFalse(result['execution_authorized_at_attempt'])
        self.assertIsNone(result['policy_version'])

    def test_revocation_preserves_decision_snapshot_but_denies_execution(self):
        snapshot = self.decide()['policy_snapshot']
        self.controller.set_policy('run-1', 'sha256:artifact', False)
        result = self.controller.execute('decision-1', 'attempt-1')
        self.assertTrue(snapshot['allowed'])
        self.assertEqual(snapshot['version'], 1)
        self.assertEqual(result['policy_version'], 2)
        self.assertFalse(result['effect_occurred'])

    def test_denial_never_creates_release(self):
        self.decide(recommendation='deny')
        result = self.controller.execute('decision-1', 'attempt-1')
        self.assertFalse(result['effect_occurred'])
        self.assertEqual(self.count('releases'), 0)

    def test_repeated_attempt_id_is_idempotent_and_new_attempt_cannot_release_twice(self):
        self.decide()
        first = self.controller.execute('decision-1', 'attempt-1')
        self.assertEqual(first, self.controller.execute('decision-1', 'attempt-1'))
        second = self.controller.execute('decision-1', 'attempt-2')
        self.assertTrue(second['execution_authorized_at_attempt'])
        self.assertFalse(second['effect_occurred'])
        self.assertEqual(self.count('releases'), 1)
        self.assertEqual(self.count('attempts'), 2)

    def test_concurrent_attempts_commit_exactly_one_effect(self):
        self.decide()
        def execute(i):
            return Controller(self.db, self.key).execute('decision-1', 'parallel-' + str(i))
        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
            results = list(pool.map(execute, range(6)))
        self.assertEqual(sum(r['effect_occurred'] for r in results), 1)
        self.assertEqual(self.count('releases'), 1)
        self.assertEqual(self.count('attempts'), 6)

    def test_audit_insert_failure_rolls_back_effect_and_attempt(self):
        self.decide()
        with sqlite3.connect(self.db) as conn:
            conn.execute("CREATE TRIGGER reject_audit BEFORE INSERT ON events WHEN NEW.kind='release_committed' BEGIN SELECT RAISE(ABORT, 'audit unavailable'); END")
        with self.assertRaises(sqlite3.IntegrityError):
            self.controller.execute('decision-1', 'attempt-1')
        self.assertEqual(self.count('releases'), 0)
        self.assertEqual(self.count('attempts'), 0)

    def test_attempt_id_cannot_alias_another_decision(self):
        self.decide()
        self.decide(decision_id='decision-2')
        self.controller.execute('decision-1', 'attempt-1')
        with self.assertRaises(ValueError):
            self.controller.execute('decision-2', 'attempt-1')

    def test_non_ascii_signature_is_a_denial_not_an_exception(self):
        receipt = dict(self.receipt, signature='é' * 64)
        self.decide([receipt])
        result = self.controller.execute('decision-1', 'attempt-1')
        self.assertFalse(result['execution_authorized_at_attempt'])
        self.assertFalse(result['effect_occurred'])

    def test_paired_trials_have_independent_policy_and_effects(self):
        other = Controller(self.db, self.key, trial_id='paired-world')
        other.set_policy('run-1', 'sha256:artifact', True)
        other.record_decision('decision-paired', 'run-1', 'sha256:artifact',
                              'approve', 'independent trial', [self.receipt])
        self.decide()
        self.assertTrue(self.controller.execute('decision-1', 'attempt-1')['effect_occurred'])
        self.assertTrue(other.execute('decision-paired', 'attempt-paired')['effect_occurred'])
        self.assertEqual(self.count('releases'), 2)
        with self.assertRaises(ValueError):
            other.execute('decision-1', 'foreign-attempt')
        self.controller.set_policy('run-1', 'sha256:artifact', False)
        self.assertTrue(other.execute('decision-paired', 'paired-duplicate')['execution_authorized_at_attempt'])
