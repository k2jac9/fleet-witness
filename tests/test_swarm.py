import json
from pathlib import Path
import tempfile
import unittest

from fleet_witness.swarm.detect import analyze, detect_cell, load_events
from fleet_witness.swarm.providers import BudgetExceeded, FakeClient, Ledger, parse_vote
from fleet_witness.swarm.runner import run_swarm


# Provider and ledger behavioral coverage lives in test_swarm_provider.py and
# test_swarm_ledger.py. Automatic escalation is deliberately no longer supported.


class ParseVoteTest(unittest.TestCase):
    def test_parses_json_and_abstains_on_garbage(self):
        self.assertEqual(parse_vote('```json\n{"vote": "Approve", "reason": "ok"}\n```'), ('approve', 'ok'))
        self.assertEqual(parse_vote('I would deny this.')[0], 'deny')
        self.assertEqual(parse_vote('approve or deny? unsure')[0], 'abstain')
        self.assertEqual(parse_vote('')[0], 'abstain')


class SwarmRunTest(unittest.TestCase):
    def run_fake(self, tmp, **kwargs):
        output = Path(tmp) / 'run'
        manifest = run_swarm(output, FakeClient(seed=3), agents=40, cases=6, seed=3, **kwargs)
        return output, manifest

    def test_events_do_not_leak_sealed_truth(self):
        with tempfile.TemporaryDirectory() as tmp:
            output, _ = self.run_fake(tmp)
            raw = (output / 'events.jsonl').read_text(encoding='utf-8')
            self.assertNotIn('colluder', raw)
            self.assertNotIn('"valid"', raw)
            self.assertNotIn('PRIVATE INSTRUCTION', raw)

    def test_kernel_blocks_forgery_that_fools_direct_democracy(self):
        with tempfile.TemporaryDirectory() as tmp:
            output, manifest = self.run_fake(tmp)
            self.assertEqual(manifest['calls'], (40 + 7) * 6 * 4)
            report = analyze(output)
            for condition in report['conditions'].values():
                # the forged-but-plausible receipt fools the swarm majority ...
                self.assertEqual(condition['swarm_approved_invalid_cases'], '1/4')
                self.assertEqual(condition['regimes']['direct']['unsafe_effects'], 1)
                # ... but every kernel regime checks evidence integrity mechanically
                for name, regime in condition['regimes'].items():
                    if name != 'direct':
                        self.assertEqual(regime['unsafe_effects'] - regime['unsafe_on_targets'], 0, name)

    def test_detector_finds_cell_and_stays_quiet_without_one(self):
        with tempfile.TemporaryDirectory() as tmp:
            output, _ = self.run_fake(tmp)
            report = analyze(output)
            truth = set(json.loads((output / 'truth.json').read_text(encoding='utf-8'))['colluders'])
            for name in ('hidden-cell', 'visible-cell'):
                self.assertEqual(set(report['conditions'][name]['detection']['flagged']), truth)
            for name in ('hidden-clean', 'visible-clean'):
                self.assertEqual(report['conditions'][name]['detection']['flagged'], [])

    def test_refuses_to_overwrite_existing_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            output, _ = self.run_fake(tmp)
            with self.assertRaises(ValueError):
                run_swarm(output, FakeClient(), agents=8, cases=1)

    def test_budget_abort_marks_run_incomplete(self):
        class Broke(FakeClient):
            label = 'broke'

            def complete(self, system, user, meta=None):
                raise BudgetExceeded('run cap $0.00 would be exceeded')
        with tempfile.TemporaryDirectory() as tmp:
            manifest = run_swarm(Path(tmp) / 'run', Broke(), agents=8, cases=2, conditions=['hidden-clean'])
            self.assertTrue(manifest['incomplete'])
            self.assertEqual(manifest['calls'], 0)
            self.assertEqual(manifest['skipped'], (8 + 7) * 2)

    def test_repeated_provider_errors_stop_the_run(self):
        from fleet_witness.swarm.providers import ProviderError

        class Down(FakeClient):
            label = 'down'

            def complete(self, system, user, meta=None):
                raise ProviderError('network down')
        with tempfile.TemporaryDirectory() as tmp:
            manifest = run_swarm(Path(tmp) / 'run', Down(), agents=40, cases=2, conditions=['hidden-clean'], waves=4)
            self.assertTrue(manifest['incomplete'])
            self.assertIn('consecutive provider errors', manifest['abort_reason'])
            self.assertLess(manifest['errors'], 40 * 2)

    def test_detect_ignores_abstentions(self):
        events = [{'type': 'vote', 'condition': 'c', 'case_id': 'x', 'wave': 0, 'agent_id': f'A{i}',
                   'vote': 'abstain', 'reason': ''} for i in range(5)]
        self.assertEqual(detect_cell(events, 'c')['flagged'], [])


if __name__ == '__main__':
    unittest.main()
