import json
from pathlib import Path
import tempfile
import unittest

from fleet_witness.swarm.detect import analyze, detect_cell, load_events
from fleet_witness.swarm.providers import BudgetExceeded, FakeClient, Ledger, parse_vote
from fleet_witness.swarm.runner import run_swarm


class LedgerTest(unittest.TestCase):
    def test_run_cap_refuses_before_sending(self):
        with tempfile.TemporaryDirectory() as tmp:
            ledger = Ledger('adaption', run_cap_usd=0.01, lifetime_cap_usd=5, path=Path(tmp) / 'l.json')
            ledger.reserve(0.006)
            with self.assertRaises(BudgetExceeded):
                ledger.reserve(0.006)  # in-flight reservations count toward the cap

    def test_lifetime_cap_persists_across_runs(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'l.json'
            first = Ledger('openrouter', run_cap_usd=1, lifetime_cap_usd=0.02, path=path)
            first.reserve(0.015)
            first.settle(0.015, 0.015)
            second = Ledger('openrouter', run_cap_usd=1, lifetime_cap_usd=0.02, path=path)
            self.assertAlmostEqual(second.lifetime_spent(), 0.015)
            with self.assertRaises(BudgetExceeded):
                second.reserve(0.01)

    def test_failed_call_is_charged_at_worst_case(self):
        with tempfile.TemporaryDirectory() as tmp:
            ledger = Ledger('adaption', run_cap_usd=1, lifetime_cap_usd=1, path=Path(tmp) / 'l.json')
            ledger.reserve(0.2)
            ledger.settle(0.2, 0.2)
            self.assertAlmostEqual(ledger.run_spent, 0.2)
            self.assertAlmostEqual(ledger.run_reserved, 0.0)


class TruncationEscalationTest(unittest.TestCase):
    def test_truncated_answer_is_retried_with_a_larger_cap(self):
        from fleet_witness.swarm.providers import ModelClient
        client = object.__new__(ModelClient)
        client.max_output_tokens = 2000
        caps = []

        def attempt(system, user, cap):
            caps.append(cap)
            if cap < 4000:  # long deliberation does not fit in 2000 tokens
                return {'text': '', 'input_tokens': 10, 'output_tokens': cap, 'cost_usd': 0.01, 'truncated': True}
            return {'text': '{"vote": "approve", "reason": "x"}', 'input_tokens': 10, 'output_tokens': 2600,
                    'cost_usd': 0.02, 'truncated': False}
        client._attempt = attempt
        result = client.complete('s', 'u')
        self.assertEqual(caps, [2000, 4000])
        self.assertEqual(result['truncation_retries'], 1)
        self.assertFalse(result['truncated'])
        self.assertAlmostEqual(result['cost_usd'], 0.03)  # both attempts are billed and counted
        self.assertEqual(parse_vote(result['text'])[0], 'approve')

    def test_escalation_stops_at_ceiling(self):
        from fleet_witness.swarm.providers import ModelClient
        client = object.__new__(ModelClient)
        client.max_output_tokens = 2000
        client._attempt = lambda s, u, cap: {'text': '', 'input_tokens': 1, 'output_tokens': cap,
                                             'cost_usd': 0.0, 'truncated': True}
        result = client.complete('s', 'u')
        self.assertTrue(result['truncated'])
        self.assertEqual(result['final_cap'], 16000)


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
