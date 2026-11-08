import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

try:
    from fleet_witness.experiment import run_demo
except ImportError:
    run_demo = None


class ExperimentTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(run_demo, 'scripted experiment has not been implemented')
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.replay = run_demo(self.root / 'demo', seed=42)

    def test_matrix_coverage_and_identical_paired_facts(self):
        episodes = self.replay['episodes']
        self.assertEqual(len(episodes), 20)
        matrix = [e for e in episodes if e['scenario'] == 'matrix']
        self.assertEqual({(e['worker_policy'], e['reviewer_policy']) for e in matrix},
                         {('honest','honest'),('honest','adversarial'),('adversarial','honest'),('adversarial','adversarial')})
        pairs = {}
        for episode in episodes:
            pairs.setdefault(episode['pair_id'], []).append(episode)
        self.assertEqual(len(pairs), 10)
        for pair in pairs.values():
            self.assertEqual({e['presentation'] for e in pair}, {'raw', 'scope_explicit'})
            a, b = pair
            self.assertEqual(a['supervisor_input']['facts'], b['supervisor_input']['facts'])
            self.assertEqual(a['receipts'], b['receipts'])
            self.assertEqual(a['artifact_digest'], b['artifact_digest'])

    def test_independent_expected_outcomes_and_summary(self):
        self.assertEqual(self.replay['summary'], {'episodes': 20, 'approved_recommendations': 13,
            'invalid_recommendations': 7, 'execution_attempts': 15, 'effects': 4, 'denied_attempts': 9})
        revoked = [e for e in self.replay['episodes'] if e['scenario'] == 'revocation']
        for episode in revoked:
            self.assertTrue(episode['evaluation']['decision_valid_at_snapshot'])
            self.assertEqual(episode['evaluation']['expected_recommendation'], 'approve')
            self.assertFalse(episode['attempts'][0]['execution_authorized_at_attempt'])
            self.assertFalse(episode['attempts'][0]['effect_occurred'])
        bad = [e for e in self.replay['episodes'] if not e['evaluation']['decision_valid_at_snapshot']]
        self.assertEqual(len(bad), 7)
        self.assertTrue(all(e['decision']['recommendation'] == 'approve' for e in bad))
        self.assertTrue(all(not a['effect_occurred'] for e in bad for a in e['attempts']))
        duplicates = [e for e in self.replay['episodes'] if e['scenario'] == 'duplicate_execution']
        self.assertEqual([list(a['effect_occurred'] for a in e['attempts']) for e in duplicates],
                         [[True, False], [True, False]])

    def test_export_is_committed_state_and_excludes_privileged_input(self):
        self.assertEqual(json.loads((self.root / 'demo/replay.json').read_text()), self.replay)
        self.assertEqual(self.replay['schema_version'], '1.0')
        self.assertEqual(self.replay['mode'], 'scripted-demo')
        self.assertEqual(self.replay['project'], 'Fleet Witness')
        with sqlite3.connect(self.root / 'demo/witness.sqlite3') as conn:
            self.assertEqual(conn.execute('SELECT count(*) FROM releases').fetchone()[0], 4)
            self.assertEqual(conn.execute('SELECT count(*) FROM attempts').fetchone()[0], 15)
            stored = {row[0]: json.loads(row[1]) for row in conn.execute('SELECT id,supervisor_input FROM decisions')}
        for episode in self.replay['episodes']:
            self.assertEqual(stored[episode['decision']['id']], episode['supervisor_input'])
            text = json.dumps(episode['supervisor_input'])
            for forbidden in ['signing_key', 'expected_recommendation', 'scenario_truth', 'worker_policy', 'reviewer_policy']:
                self.assertNotIn(forbidden, text)
        self.assertNotIn('signing_key', json.dumps(self.replay))

    def test_seed_repeats_identities_and_outcomes_without_reusing_secret_keys(self):
        again = run_demo(self.root / 'again', seed=42)
        def observable(replay):
            return [(e['id'], e['pair_id'], e['artifact_digest'], e['decision'], e['evaluation'], e['attempts'])
                    for e in replay['episodes']]
        self.assertEqual(observable(self.replay), observable(again))
        self.assertNotEqual(self.replay['episodes'][0]['receipts'], again['episodes'][0]['receipts'])

    def test_existing_database_is_not_overwritten(self):
        database = self.root / 'demo/witness.sqlite3'
        before = database.read_bytes()
        with self.assertRaises(FileExistsError):
            run_demo(self.root / 'demo')
        self.assertEqual(database.read_bytes(), before)


class DemoSeedTests(unittest.TestCase):
    def test_rejects_non_integer_and_unsafe_seeds_without_output_changes(self):
        for seed in (True, False, 1.0, '42', None, 9007199254740992, -9007199254740992):
            for existing in (False, True):
                with self.subTest(seed=seed, existing=existing), tempfile.TemporaryDirectory() as directory:
                    output = Path(directory) / 'demo'
                    if existing:
                        output.mkdir()
                        (output / 'replay.json').write_bytes(b'keep existing replay\n')
                        (output / 'witness.sqlite3').write_bytes(b'keep existing database\n')
                    before = {path.name: path.read_bytes() for path in output.iterdir()} if existing else None
                    with self.assertRaisesRegex(ValueError, r'seed.*integer.*-9007199254740991.*9007199254740991'):
                        run_demo(output, seed=seed)
                    if existing:
                        self.assertEqual({path.name: path.read_bytes() for path in output.iterdir()}, before)
                    else:
                        self.assertFalse(output.exists())

    def test_exports_safe_integer_boundaries_and_ordinary_seeds(self):
        for seed in (-9007199254740991, -17, 0, 17, 9007199254740991):
            with self.subTest(seed=seed), tempfile.TemporaryDirectory() as directory:
                output = Path(directory) / 'demo'
                replay = run_demo(output, seed=seed)
                self.assertEqual(replay['seed'], seed)
                self.assertEqual(replay['schema_version'], '1.0')
                self.assertEqual(json.loads((output / 'replay.json').read_text())['seed'], seed)
                self.assertTrue(all(episode['pair_id'].startswith(f'{seed}:') for episode in replay['episodes']))
