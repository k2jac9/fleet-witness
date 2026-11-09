import collections
import json
import unittest

from fleet_witness.evidence import verify_receipt
from fleet_witness.gateway import provider_input
try:
    from fleet_witness import pilot_design as pilot
except ImportError:
    pilot = None


class PilotDesignTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(pilot, 'paired pilot design must be implemented')
        self.key = b'synthetic-private-issuer-key-0000'
        self.plan = pilot.make_plan(self.key)

    def test_complete_balanced_schedule_with_identical_opaque_paired_facts(self):
        pairs = self.plan['pairs']; schedule = self.plan['schedule']
        self.assertEqual(len(pairs), 80); self.assertEqual(len(schedule), 160)
        self.assertEqual(len({p['pair_id'] for p in pairs}), 80)
        self.assertEqual(len({p['facts']['run_id'] for p in pairs}), 80)
        self.assertEqual(len({s['trial_id'] for s in schedule}), 160)
        counts = collections.Counter(p['family'] for p in pairs)
        self.assertEqual(set(counts.values()), {10}); self.assertEqual(len(counts), 8)
        first = collections.Counter()
        for pair in pairs:
            calls = [s for s in schedule if s['pair_id'] == pair['pair_id']]
            self.assertEqual({s['presentation'] for s in calls}, {'raw', 'scope_explicit'})
            first[pair['family'], calls[0]['presentation']] += 1
            a = provider_input(pair['facts'], 'raw'); b = provider_input(pair['facts'], 'scope_explicit')
            self.assertEqual(a['facts'], b['facts']); self.assertNotEqual(a['instruction'], b['instruction'])
            for identity in (pair['pair_id'], pair['facts']['run_id']): self.assertRegex(identity, r'^[0-9a-f]{32}$')
            visible = json.dumps(a)
            self.assertNotIn(self.key.decode(), visible)
            self.assertNotIn('evidence_valid_at_snapshot', visible)
            self.assertNotIn(pair['pair_id'], visible)
            self.assertNotIn('expected_recommendation', visible)
        self.assertEqual(set(first.values()), {5})

    def test_sealed_truth_matches_literal_fixture_families_and_all_applicability_strata(self):
        valid = {'complete', 'revocation', 'duplicate', 'mixed'}
        strata = collections.Counter()
        orders = collections.Counter()
        for p in self.plan['pairs']:
            expected = p['family'] in valid
            self.assertIs(p['evidence_valid_at_snapshot'], expected)
            self.assertIs(p['permission_at_snapshot'], True)
            facts = p['facts']
            checks = [verify_receipt(r, self.key, facts['run_id'], facts['artifact_digest'])[0] for r in facts['receipts']]
            self.assertEqual(any(checks), expected)
            if p['family'] == 'wrong_applicability': strata[p['stratum']] += 1
            if p['family'] == 'mixed': orders[checks[0]] += 1
        self.assertEqual(strata, {'issuer': 2, 'claim': 2, 'scope': 2, 'artifact': 2, 'run': 2})
        self.assertEqual(orders, {True: 5, False: 5})

    def test_fixed_schedule_design_with_random_opaque_identifiers_and_bounded_inputs(self):
        other = pilot.make_plan(self.key)
        def shape(plan):
            pairs = {p['pair_id']: p for p in plan['pairs']}
            return [(pairs[s['pair_id']]['family'], pairs[s['pair_id']]['repetition'], s['presentation']) for s in plan['schedule']]
        self.assertEqual(shape(self.plan), shape(other))
        self.assertNotEqual(self.plan['study_id'], other['study_id'])
        self.assertEqual(self.plan['design_sha256'], pilot.design_sha256())
        for p in self.plan['pairs']:
            for presentation in ('raw', 'scope_explicit'):
                visible = provider_input(p['facts'], presentation)
                self.assertLessEqual(len(visible['instruction'].encode()) + len(json.dumps(visible['facts'],sort_keys=True,separators=(',',':')).encode()), 4096)
