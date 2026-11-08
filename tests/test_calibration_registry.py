"""Inert registry tests; no model, credential, provider or cloud access."""
from contextlib import closing
import os
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest

try:
    from fleet_witness.calibration_registry import FixtureRegistry
except ImportError:
    FixtureRegistry = None


class FixtureRegistryTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(FixtureRegistry, 'fixture registry is not implemented')
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.directory = Path(tmp.name)
        self.registry_path = self.directory / 'registry.sqlite3'
        self.ledger_path = self.directory / 'calibration.sqlite3'
        self.auth_id = 'a' * 32
        self.account = 'fixture-account'
        self.source = 'b' * 40
        self.registry = FixtureRegistry(self.registry_path)

    def claim(self):
        self.registry.claim(self.auth_id, self.account, self.source, self.ledger_path)

    def test_claim_is_immutable_and_bound_to_canonical_identities(self):
        self.claim()
        state = FixtureRegistry(self.registry_path).snapshot(self.auth_id)
        self.assertEqual(state['mode'], 'offline-authorization-fixture')
        self.assertEqual(state['status'], 'claimed')
        self.assertEqual(state['account_id'], self.account)
        self.assertEqual(state['source_commit'], self.source)
        self.assertEqual(state['ledger_path'], str(self.ledger_path))
        for account, source, ledger in [(self.account, self.source, self.ledger_path),
                                         ('different', self.source, self.ledger_path),
                                         (self.account, 'c' * 40, self.ledger_path),
                                         (self.account, self.source, self.directory/'other.sqlite3')]:
            with self.subTest(account=account, source=source, ledger=ledger), self.assertRaises(ValueError):
                self.registry.claim(self.auth_id, account, source, ledger)
        self.assertEqual(self.registry.snapshot(self.auth_id), state)

    def test_consumption_survives_restart_and_cannot_repeat(self):
        self.claim()
        self.registry.consume(self.auth_id)
        reopened = FixtureRegistry(self.registry_path)
        self.assertEqual(reopened.snapshot(self.auth_id)['status'], 'consumed')
        with self.assertRaises(ValueError): reopened.consume(self.auth_id)
        with self.assertRaises(ValueError): reopened.claim(self.auth_id, self.account, self.source, self.ledger_path)

    def test_separate_processes_can_consume_only_once(self):
        self.claim()
        program = '''import sys
from fleet_witness.calibration_registry import FixtureRegistry
r=FixtureRegistry(sys.argv[1])
try:
 r.consume(sys.argv[2]); print('consumed')
except ValueError:
 print('refused')
'''
        children = [subprocess.Popen([sys.executable, '-c', program, str(self.registry_path), self.auth_id],
                                     stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                    for _ in range(4)]
        results = [p.communicate(timeout=15) for p in children]
        self.assertTrue(all(p.returncode == 0 for p in children), results)
        self.assertEqual([out.strip() for out, _ in results].count('consumed'), 1)
        self.assertEqual([out.strip() for out, _ in results].count('refused'), 3)

    def test_audit_failure_rolls_back_consumption(self):
        self.claim()
        with closing(sqlite3.connect(self.registry_path)) as c, c:
            c.execute("CREATE TRIGGER reject_consumed BEFORE INSERT ON audit WHEN NEW.kind='consumed' BEGIN SELECT RAISE(ABORT,'audit failure'); END")
        with self.assertRaises(sqlite3.IntegrityError): self.registry.consume(self.auth_id)
        self.assertEqual(self.registry.snapshot(self.auth_id)['status'], 'claimed')

    def test_audit_failure_rolls_back_claim(self):
        with closing(sqlite3.connect(self.registry_path)) as c, c:
            c.execute("CREATE TRIGGER reject_claim BEFORE INSERT ON audit WHEN NEW.kind='claimed' BEGIN SELECT RAISE(ABORT,'audit failure'); END")
        with self.assertRaises(sqlite3.IntegrityError): self.claim()
        self.assertIsNone(self.registry.snapshot(self.auth_id))

    def test_snapshot_is_detached_from_the_registry(self):
        self.claim()
        snapshot = self.registry.snapshot(self.auth_id)
        snapshot['account_id'] = 'changed'
        snapshot['status'] = 'consumed'
        self.assertEqual(self.registry.snapshot(self.auth_id)['account_id'], self.account)
        self.assertEqual(self.registry.snapshot(self.auth_id)['status'], 'claimed')

    def test_unknown_or_malformed_identities_are_refused(self):
        cases = [('not-an-id', self.account, self.source, self.ledger_path),
                 (self.auth_id, '', self.source, self.ledger_path),
                 (self.auth_id, self.account, 'x' * 40, self.ledger_path),
                 (self.auth_id, self.account, self.source, Path('relative.sqlite3'))]
        for auth, account, source, path in cases:
            with self.subTest(auth=auth, account=account, source=source, path=path), self.assertRaises(ValueError):
                self.registry.claim(auth, account, source, path)
        self.assertIsNone(self.registry.snapshot(self.auth_id))
        with self.assertRaises(ValueError): self.registry.consume(self.auth_id)

    def test_registry_refuses_symlink_and_nonprivate_directory(self):
        link = self.directory / 'link.sqlite3'
        link.symlink_to(self.registry_path)
        with self.assertRaises((ValueError, OSError)): FixtureRegistry(link)
        public = self.directory / 'public'
        public.mkdir(mode=0o755)
        public.chmod(0o755)  # The test must not depend on the operator's umask.
        with self.assertRaises(ValueError): FixtureRegistry(public/'registry.sqlite3')
        self.assertEqual(self.registry_path.stat().st_mode & 0o777, 0o600)
        alias = self.directory / 'hardlink.sqlite3'
        os.link(self.registry_path, alias)
        with self.assertRaises(ValueError): FixtureRegistry(alias)

    def test_registry_rejects_relative_and_noncanonical_paths(self):
        with self.assertRaises(ValueError):
            FixtureRegistry(Path('registry.sqlite3'))
        with self.assertRaises(ValueError):
            FixtureRegistry(self.directory / '..' / self.directory.name / 'registry.sqlite3')
        alias = self.directory / 'parent-alias'
        alias.symlink_to(self.directory, target_is_directory=True)
        with self.assertRaises(ValueError):
            FixtureRegistry(alias / 'registry.sqlite3')

    def test_relative_registry_is_refused_even_in_a_private_working_directory(self):
        program = '''from fleet_witness.calibration_registry import FixtureRegistry
try:
 FixtureRegistry('relative.sqlite3')
except ValueError:
 print('refused')
else:
 print('accepted')
'''
        env = dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parent.parent))
        child = subprocess.run([sys.executable, '-c', program], cwd=self.directory,
                               env=env, capture_output=True, text=True, check=True)
        self.assertEqual(child.stdout.strip(), 'refused')

    def test_ledger_path_cannot_be_symlink(self):
        alias = self.directory / 'ledger-link'
        alias.symlink_to(self.ledger_path)
        with self.assertRaises(ValueError):
            self.registry.claim(self.auth_id, self.account, self.source, alias)

    def fixture_runner(self, response=None):
        from fleet_witness.live_gateway import LiveLedger, FixtureRunner, FixtureTransport, new_authorization
        authorization = new_authorization(int(time.time()) + 300, 'a' * 64)
        ledger = LiveLedger(self.ledger_path, authorization)
        if response is None:
            text = '{"recommendation":"deny","reason":"No safety evidence"}'
            response = json.dumps({'id': 'resp_fixture', 'object': 'response', 'status': 'completed',
                'model': 'gemma-4-31b-it', 'output': [{'type': 'message', 'role': 'assistant',
                'content': [{'type': 'output_text', 'text': text}]}], 'output_text': text,
                'usage': {'input_tokens': 100, 'output_tokens': 20, 'total_tokens': 120}}).encode()
        transport = FixtureTransport([response])
        return FixtureRunner(ledger, transport), transport

    def fixture_facts(self):
        return dict(run_id='opaque-run', artifact_digest='sha256:synthetic',
                    decision_time_policy={'allowed': True, 'version': 1}, receipts=[],
                    reviewer_verdict='deny', reviewer_statement='Synthetic statement')

    def test_bound_fixture_runner_consumes_claim_before_fixture_and_cannot_repeat(self):
        from fleet_witness.calibration_registry import BoundFixtureRunner
        self.claim()
        runner, transport = self.fixture_runner()
        bound = BoundFixtureRunner(self.registry, runner, self.auth_id, self.account, self.source)
        result = bound.run('fixture-request', self.fixture_facts(), 'raw')
        self.assertEqual(result['mode'], 'offline-calibration-fixture')
        self.assertEqual(self.registry.snapshot(self.auth_id)['status'], 'consumed')
        self.assertEqual(len(transport.requests), 1)
        with self.assertRaises(ValueError): bound.run('second', self.fixture_facts(), 'raw')
        self.assertEqual(len(transport.requests), 1)

    def test_bound_runner_rejects_wrong_binding_without_consuming(self):
        from fleet_witness.calibration_registry import BoundFixtureRunner
        self.claim()
        runner, transport = self.fixture_runner()
        for account, source in [('other-account', self.source), (self.account, 'c' * 40)]:
            with self.subTest(account=account, source=source), self.assertRaises(ValueError):
                BoundFixtureRunner(self.registry, runner, self.auth_id, account, source).run(
                    'fixture-request', self.fixture_facts(), 'raw')
        self.assertEqual(self.registry.snapshot(self.auth_id)['status'], 'claimed')
        self.assertEqual(transport.requests, [])

    def test_invalid_fixture_input_does_not_consume_authorization(self):
        from fleet_witness.calibration_registry import BoundFixtureRunner
        self.claim()
        runner, transport = self.fixture_runner()
        bound = BoundFixtureRunner(self.registry, runner, self.auth_id, self.account, self.source)
        with self.assertRaises(ValueError):
            bound.run('fixture-request', dict(self.fixture_facts(), sealed_truth='secret'), 'raw')
        with self.assertRaises(ValueError):
            bound.run('invalid request id', self.fixture_facts(), 'raw')
        self.assertEqual(self.registry.snapshot(self.auth_id)['status'], 'claimed')
        self.assertEqual(transport.requests, [])

    def test_bound_runner_rejects_different_ledger_without_consuming(self):
        from fleet_witness.calibration_registry import BoundFixtureRunner
        from fleet_witness.live_gateway import LiveLedger, FixtureRunner, FixtureTransport, new_authorization
        self.claim()
        ledger = LiveLedger(self.directory / 'other.sqlite3', new_authorization(int(time.time()) + 300, 'a' * 64))
        transport = FixtureTransport([])
        bound = BoundFixtureRunner(self.registry, FixtureRunner(ledger, transport), self.auth_id, self.account, self.source)
        with self.assertRaises(ValueError):
            bound.run('fixture-request', self.fixture_facts(), 'raw')
        self.assertEqual(self.registry.snapshot(self.auth_id)['status'], 'claimed')
        self.assertEqual(transport.requests, [])

    def test_failed_fixture_still_consumes_authorization_and_holds_budget(self):
        from fleet_witness.calibration_registry import BoundFixtureRunner
        self.claim()
        runner, transport = self.fixture_runner(b'not JSON')
        bound = BoundFixtureRunner(self.registry, runner, self.auth_id, self.account, self.source)
        result = bound.run('fixture-request', self.fixture_facts(), 'raw')
        self.assertEqual(result['status'], 'unresolved')
        self.assertEqual(self.registry.snapshot(self.auth_id)['status'], 'consumed')
        self.assertEqual(runner.ledger.snapshot()['held_microcredits'], 1_000_000)
        self.assertEqual(len(transport.requests), 1)


if __name__ == '__main__':
    unittest.main()
