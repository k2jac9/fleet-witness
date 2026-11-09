import sqlite3
import unittest

from fleet_witness.evidence import issue_receipt
from fleet_witness.institution import Institution, sign_attestation
from fleet_witness.verify_institution import MUTANTS, capture_probability, check

EKEY = b'evidence'
KEYS = {name: name.encode() * 4 for name in ('a', 'b', 'c', 'outsider')}


def kernel(quorum=2, require_majority=True, intact=True):
    k = Institution(sqlite3.connect(':memory:', isolation_level=None), evidence_key=EKEY, auditor_keys=KEYS,
                    quorum=quorum, committee_size=3, require_majority=require_majority)
    receipt = issue_receipt(EKEY, issuer='i', claim='c', scope='s', artifact_digest='d', run_id='r')
    if not intact:
        receipt['signature'] = 'f' * 64
    k.open_case('C', 'r', 'd', [receipt], ['a', 'b', 'c'])
    k.set_policy('C', True)
    return k


class InstitutionTest(unittest.TestCase):
    def test_quorum_of_seated_auditors_authorizes_exactly_once(self):
        k = kernel()
        k.record_proposal('C', 5, 1)
        k.submit_attestation('C', sign_attestation(KEYS['a'], 'a', 'r', 'd'))
        self.assertFalse(k.execute('C', 'x1')['effect'])
        k.submit_attestation('C', sign_attestation(KEYS['b'], 'b', 'r', 'd'))
        self.assertTrue(k.execute('C', 'x2')['effect'])
        self.assertFalse(k.execute('C', 'x3')['effect'])
        self.assertEqual(k.conn.execute('SELECT COUNT(*) FROM releases').fetchone()[0], 1)

    def test_outsiders_duplicates_and_misbound_attestations_do_not_count(self):
        k = kernel()
        k.record_proposal('C', 5, 1)
        k.submit_attestation('C', sign_attestation(KEYS['a'], 'a', 'r', 'd'))
        k.submit_attestation('C', sign_attestation(KEYS['a'], 'a', 'r', 'd'))
        k.submit_attestation('C', sign_attestation(KEYS['outsider'], 'outsider', 'r', 'd'))
        k.submit_attestation('C', sign_attestation(KEYS['b'], 'b', 'r', 'other'))
        k.submit_attestation('C', dict(sign_attestation(KEYS['c'], 'c', 'r', 'd'), signature='0' * 64))
        result = k.execute('C', 'x')
        self.assertFalse(result['effect'])
        self.assertIn('only 1 of 2', result['reason'])

    def test_tampered_evidence_and_revoked_policy_block(self):
        k = kernel(intact=False)
        k.record_proposal('C', 5, 1)
        for name in ('a', 'b', 'c'):
            k.submit_attestation('C', sign_attestation(KEYS[name], name, 'r', 'd'))
        self.assertEqual(k.execute('C', 'x')['reason'], 'evidence integrity failed')
        k2 = kernel()
        k2.record_proposal('C', 5, 1)
        for name in ('a', 'b'):
            k2.submit_attestation('C', sign_attestation(KEYS[name], name, 'r', 'd'))
        k2.set_policy('C', False)
        self.assertFalse(k2.execute('C', 'x')['effect'])

    def test_committee_only_mode_does_not_need_majority(self):
        k = kernel(require_majority=False)
        k.record_proposal('C', 1, 0)
        for name in ('a', 'b'):
            k.submit_attestation('C', sign_attestation(KEYS[name], name, 'r', 'd'))
        self.assertTrue(k.execute('C', 'x')['effect'])


class BoundedCheckTest(unittest.TestCase):
    def test_kernel_verified_and_every_mutant_caught(self):
        for majority in (True, False):
            self.assertTrue(check(depth=4, require_majority=majority)['verified'])
        caught = {m for m in MUTANTS if not check(6 if m == 'skip_uniqueness' else 5, frozenset({m}))['verified']}
        self.assertEqual(caught, set(MUTANTS))

    def test_capture_probability(self):
        self.assertAlmostEqual(capture_probability(100, 10, 1, 1), 0.10)
        self.assertAlmostEqual(capture_probability(100, 0, 7, 4, honest_error=0.0), 0.0)
        self.assertAlmostEqual(capture_probability(10, 10, 3, 2), 1.0)
        # more seats with a majority quorum help when the cell is a minority
        self.assertLess(capture_probability(100, 20, 7, 4), capture_probability(100, 20, 3, 2))


if __name__ == '__main__':
    unittest.main()
