import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


class CLITests(unittest.TestCase):
    def test_rejects_unsafe_seeds_with_clear_error_without_output_changes(self):
        for seed in ('9007199254740992', '-9007199254740992'):
            for existing in (False, True):
                with self.subTest(seed=seed, existing=existing), tempfile.TemporaryDirectory() as directory:
                    output = Path(directory) / 'demo'
                    if existing:
                        output.mkdir()
                        (output / 'replay.json').write_bytes(b'keep existing replay\n')
                        (output / 'witness.sqlite3').write_bytes(b'keep existing database\n')
                    before = {path.name: path.read_bytes() for path in output.iterdir()} if existing else None
                    result = subprocess.run(
                        [sys.executable, '-m', 'fleet_witness', 'demo', '--output', str(output), '--seed', seed],
                        capture_output=True, text=True)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertRegex(result.stderr, r'seed.*integer.*-9007199254740991.*9007199254740991')
                    self.assertNotIn('Traceback', result.stderr)
                    self.assertEqual(result.stdout, '')
                    if existing:
                        self.assertEqual({path.name: path.read_bytes() for path in output.iterdir()}, before)
                    else:
                        self.assertFalse(output.exists())

    def test_demo_is_labeled_and_refuses_existing_database(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'demo'
            command = [sys.executable, '-m', 'fleet_witness', 'demo', '--output', str(output), '--seed', '17']
            first = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertIn('scripted', first.stdout.lower())
            self.assertIn('20', first.stdout)
            replay = json.loads((output / 'replay.json').read_text())
            self.assertEqual(replay['seed'], 17)
            before = (output / 'witness.sqlite3').read_bytes()
            second = subprocess.run(command, capture_output=True, text=True)
            self.assertNotEqual(second.returncode, 0)
            self.assertIn('exist', second.stderr.lower())
            self.assertEqual((output / 'witness.sqlite3').read_bytes(), before)
