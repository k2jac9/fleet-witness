"""Behavioral checks for the offline runner; no Nix installation required."""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


RUNNER = Path(__file__).resolve().parents[1] / 'nix' / 'offline-task.sh'


class OfflineTaskTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / 'source with spaces'
        (self.source / 'tests').mkdir(parents=True)
        (self.source / 'fleet_witness').mkdir()
        (self.source / 'fleet_witness' / '__init__.py').write_text('')
        (self.source / 'tests' / 'test_sample.py').write_text(
            'import unittest\nclass Sample(unittest.TestCase):\n'
            '    def test_ok(self): self.assertTrue(True)\n')
        (self.source / 'fleet_witness' / '__main__.py').write_text(
            'import argparse\nfrom pathlib import Path\n'
            'p=argparse.ArgumentParser(); p.add_argument("command"); '
            'p.add_argument("--output"); p.add_argument("--seed"); a=p.parse_args()\n'
            'Path(a.output).mkdir(); (Path(a.output)/"replay.json").write_text("{}")\n'
            'print("scripted fixture demo")\n')
        self.workspace = self.root / 'new workspace'

    def run_task(self):
        return subprocess.run(['bash', str(RUNNER), str(self.source), str(self.workspace)],
                              text=True, capture_output=True, timeout=30)

    def test_success_copies_source_and_records_logs_and_demo(self):
        result = self.run_task()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('exit_code=0', (self.workspace/'results/report.txt').read_text())
        self.assertIn('Ran 1 test', (self.workspace/'results/tests.log').read_text())
        self.assertTrue((self.workspace/'results/demo/replay.json').is_file())
        self.assertFalse((self.source/'results').exists())

    def test_test_failure_is_nonzero_and_does_not_run_demo(self):
        (self.source/'tests/test_sample.py').write_text(
            'import unittest\nclass Sample(unittest.TestCase):\n'
            '    def test_bad(self): self.fail("deliberate failure")\n')
        result = self.run_task()
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue((self.workspace/'results/report.txt').is_file())
        report = (self.workspace/'results/report.txt').read_text()
        self.assertIn('stage=python-tests', report)
        self.assertNotIn('exit_code=0', report)
        self.assertIn('deliberate failure', (self.workspace/'results/tests.log').read_text())
        self.assertFalse((self.workspace/'results/demo').exists())

    def test_demo_failure_propagates_exact_status(self):
        (self.source/'fleet_witness/__main__.py').write_text(
            'import sys\nprint("broken demo", file=sys.stderr)\nsys.exit(7)\n')
        result = self.run_task()
        self.assertEqual(result.returncode, 7, result.stderr)
        self.assertIn('stage=demo', (self.workspace/'results/report.txt').read_text())
        self.assertIn('exit_code=7', (self.workspace/'results/report.txt').read_text())
        self.assertIn('broken demo', (self.workspace/'results/demo.log').read_text())

    def test_existing_workspace_is_untouched(self):
        self.assertEqual(self.run_task().returncode, 0)
        shutil.rmtree(self.workspace)
        self.workspace.mkdir()
        sentinel = self.workspace/'keep'
        sentinel.write_text('preserve me')
        result = self.run_task()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(sentinel.read_text(), 'preserve me')
        self.assertEqual(list(self.workspace.iterdir()), [sentinel])

    def test_dangling_workspace_symlink_is_refused(self):
        target = self.root/'outside'
        self.workspace.symlink_to(target, target_is_directory=True)
        result = self.run_task()
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(target.exists())

    @unittest.skipUnless(shutil.which('node'), 'Node is needed for optional viewer checks')
    def test_viewer_failure_prevents_demo(self):
        (self.source/'tests/viewer.test.mjs').write_text('process.exit(9);\n')
        result = self.run_task()
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue((self.workspace/'results/report.txt').is_file())
        self.assertIn('stage=viewer-tests', (self.workspace/'results/report.txt').read_text())
        self.assertFalse((self.workspace/'results/demo').exists())
