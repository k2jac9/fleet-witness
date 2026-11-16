"""Retain the judgement fixture's sealed truth and mechanical receipt boundaries."""
from collections import Counter
import json
from pathlib import Path
import sqlite3
import tempfile
import threading
import unittest
from unittest.mock import patch

from fleet_witness.evidence import verify_receipt
from fleet_witness.institution import Institution, sign_attestation
from fleet_witness.swarm.judgement_cases import PR_CASES
from fleet_witness.swarm.providers import FakeClient
from fleet_witness.swarm.runner import run_swarm
from fleet_witness.swarm.world import case_prompt, make_cases


KEY = b'offline-judgement-fixture-signing-key'


class JudgementCasesTest(unittest.TestCase):
    def test_fixture_composition_and_attack_targets(self):
        cases = make_cases(48, 7000, KEY, mode='judgement')
        self.assertEqual(len(cases), 48)
        self.assertEqual(len({case['id'] for case in cases}), 48)
        self.assertEqual(Counter(case['kind'] for case in cases),
                         {'benign': 10, 'benign_risky': 6, 'harm_easy': 8,
                          'harm_medium': 8, 'harm_hard': 8, 'forged': 8})
        self.assertEqual(sum(case['valid'] for case in cases), 16)
        self.assertEqual(sum(not case['valid'] and not case['looks_valid'] for case in cases), 24)
        self.assertEqual(sum(not case['valid'] and case['looks_valid'] for case in cases), 8)

    def test_authentic_ci_receipts_pass_mechanical_gate_and_forged_receipts_do_not(self):
        connection = sqlite3.connect(':memory:', isolation_level=None)
        self.addCleanup(connection.close)
        kernel = Institution(connection, evidence_key=KEY, auditor_keys={}, quorum=0, committee_size=0)
        effects = Counter()
        for case in make_cases(48, 7000, KEY, mode='judgement'):
            with self.subTest(case=case['id']):
                kernel.open_case(case['id'], case['run_id'], case['artifact_digest'], case['receipts'], [])
                kernel.set_policy(case['id'], True)
                kernel.record_proposal(case['id'], 1, 0)
                result = kernel.execute(case['id'], case['id'] + ':attempt')
                self.assertEqual(result['effect'], case['kind'] != 'forged')
                effects[result['effect']] += 1
        # Authenticity alone does not judge the 24 harmful changes.
        self.assertEqual(effects, {True: 40, False: 8})

    def test_case_receipts_bind_bundled_diff_and_run_identity(self):
        first = make_cases(48, 7000, KEY, mode='judgement')
        second = make_cases(48, 7001, KEY, mode='judgement')
        self.assertEqual(len({case['artifact_digest'] for case in first}), 48)
        for case, changed_seed in zip(first, second):
            with self.subTest(case=case['id']):
                receipt = case['receipts'][0]
                self.assertEqual(receipt['run_id'], case['run_id'])
                self.assertEqual(receipt['artifact_digest'], case['artifact_digest'])
                self.assertEqual((receipt['issuer'], receipt['claim'], receipt['scope']),
                                 ('ci-issuer', 'tests_passed', 'pull_request'))
                self.assertNotEqual(case['run_id'], changed_seed['run_id'])
                self.assertNotEqual(case['artifact_digest'], changed_seed['artifact_digest'])
        changed = list(PR_CASES[0])
        changed[5] += '\n+new_setting = True'
        with patch('fleet_witness.swarm.judgement_cases.PR_CASES', [tuple(changed)]):
            changed_diff = make_cases(1, 7000, KEY, mode='judgement')[0]
        self.assertEqual(first[0]['run_id'], changed_diff['run_id'])
        self.assertNotEqual(first[0]['artifact_digest'], changed_diff['artifact_digest'])
        self.assertNotEqual(first[0]['receipts'][0]['signature'], changed_diff['receipts'][0]['signature'])

    def test_tampered_receipt_fields_and_misbound_audits_cannot_release_judgement_case(self):
        case = make_cases(1, 7000, KEY, mode='judgement')[0]
        for field in ('run_id', 'artifact_digest'):
            for tamper_receipt in (True, False):
                with self.subTest(field=field, tamper_receipt=tamper_receipt):
                    connection = sqlite3.connect(':memory:', isolation_level=None)
                    self.addCleanup(connection.close)
                    kernel = Institution(connection, evidence_key=KEY, auditor_keys={'auditor': b'auditor-key'},
                                         quorum=1, committee_size=1)
                    receipt = dict(case['receipts'][0])
                    bindings = {'run_id': case['run_id'], 'artifact_digest': case['artifact_digest']}
                    if tamper_receipt:
                        receipt[field] = 'another-' + receipt[field]
                    else:
                        bindings[field] = 'another-' + bindings[field]
                    kernel.open_case(case['id'], case['run_id'], case['artifact_digest'], [receipt], ['auditor'])
                    kernel.set_policy(case['id'], True)
                    kernel.record_proposal(case['id'], 1, 0)
                    kernel.submit_attestation(case['id'], sign_attestation(b'auditor-key', 'auditor', **bindings))
                    self.assertFalse(kernel.execute(case['id'], 'attempt')['effect'])
                    self.assertEqual(connection.execute('SELECT COUNT(*) FROM releases').fetchone()[0], 0)

    def test_case_prompt_does_not_depend_on_sealed_labels_or_rationale(self):
        for case, fixture in zip(make_cases(48, 7000, KEY, mode='judgement'), PR_CASES):
            with self.subTest(case=case['id']):
                prompt = case_prompt(case)
                sealed = dict(case, kind='SEALED_KIND_MARKER', valid='SEALED_VALID_MARKER',
                              looks_valid='SEALED_LOOKS_VALID_MARKER', rationale=fixture[-1])
                self.assertEqual(case_prompt(sealed), prompt)
                self.assertIn(case['diff'], prompt)
                self.assertIn(case['receipts'][0]['signature'], prompt)
                self.assertNotIn(fixture[-1], prompt)
                self.assertNotIn(KEY.decode(), prompt)

    def test_actual_reviewer_and_auditor_prompts_keep_truth_sealed(self):
        class RecordingClient(FakeClient):
            def __init__(self):
                super().__init__(seed=3)
                self.prompts = []
                self.lock = threading.Lock()

            def complete(self, system, user, meta=None):
                with self.lock:
                    self.prompts.append((meta['case_id'], meta['role'], system, user))
                return super().complete(system, user, meta)

        client = RecordingClient()
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / 'judgement'
            manifest = run_swarm(output, client, agents=7, cases=48, conditions=['hidden-clean'],
                                 cell_fraction=0, waves=1, seed=7000, case_mode='judgement')
            truth = json.loads((output / 'truth.json').read_text(encoding='utf-8'))
            public = (output / 'events.jsonl').read_text(encoding='utf-8')
        self.assertFalse(manifest['incomplete'])
        self.assertEqual(manifest['provider_attempts'], 0)
        self.assertEqual(len(client.prompts), 672)
        self.assertEqual(len(truth['targets']), 24)
        self.assertEqual({role for _, role, _, _ in client.prompts}, {'reviewer', 'auditor'})
        for case_id, role, system, user in client.prompts:
            with self.subTest(case=case_id, role=role):
                fixture = PR_CASES[int(case_id.split('-')[1]) - 1]
                prompt = system + '\n' + user
                self.assertNotIn(fixture[-1], prompt)
                self.assertNotIn('PRIVATE INSTRUCTION', prompt)
                for sealed_key in ('"kind":', '"valid":', '"looks_valid":', '"rationale":'):
                    self.assertNotIn(sealed_key, prompt)
        self.assertNotIn('"valid":', public)
        self.assertNotIn('"colluder":', public)

    def test_existing_standard_and_ambiguous_modes_keep_strict_receipt_contract(self):
        standard = make_cases(6, 7000, KEY)
        self.assertEqual(standard, make_cases(6, 7000, KEY, mode='standard'))
        self.assertEqual([case['kind'] for case in standard],
                         ['valid', 'build_only', 'wrong_artifact', 'forged', 'wrong_run', 'valid'])
        ambiguous = make_cases(8, 7000, KEY, mode='ambiguous')
        self.assertEqual([case['kind'] for case in ambiguous],
                         ['valid', 'run_suffix', 'digest_near', 'scope_variant', 'issuer_variant',
                          'claim_variant', 'valid', 'digest_near'])
        for case in standard + ambiguous:
            with self.subTest(case=case['id'], kind=case['kind']):
                self.assertNotIn('diff', case)
                self.assertTrue(case['run_id'].startswith('swarm-run:7000:'))
                accepted, _ = verify_receipt(case['receipts'][0], KEY, case['run_id'], case['artifact_digest'])
                self.assertEqual(accepted, case['kind'] == 'valid')
                prompt = case_prompt(case)
                self.assertIn(case['artifact_digest'], prompt)
                self.assertIn(case['run_id'], prompt)


if __name__ == '__main__':
    unittest.main()
