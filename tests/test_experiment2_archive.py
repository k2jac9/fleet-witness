"""Small in-memory mutations of recovered evidence; no calls or extraction."""
import hashlib
import io
import json
import unittest
import zipfile

try:
    from scripts import verify_experiment2_archive as verifier
except ImportError:
    verifier = None


def packed(files, *, original=None, changes=None, mutate=None):
    original = original or files
    members = dict(files)
    for kind, values in [('original', original), ('published', files)]:
        members['SHA256SUMS-' + kind] = ''.join(
            f'{hashlib.sha256(data).hexdigest()}  {name}\n'
            for name, data in sorted(values.items())).encode()
    members['CHANGES.json'] = json.dumps({'files_changed': changes or {}}).encode()
    if mutate:
        mutate(members)
    output = io.BytesIO()
    with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as archive:
        for name, data in members.items():
            archive.writestr('experiment2-runs/' + name, data)
    output.seek(0)
    return output


class Experiment2ArchiveTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(verifier, 'offline recovered-record verifier is missing')

    def test_checks_unchanged_files_without_extraction(self):
        with zipfile.ZipFile(packed({'judge/a/events.jsonl': b'{}\n'})) as archive:
            result = verifier.verify_hashes(archive)
        self.assertEqual(result['published_files'], 1)
        self.assertEqual(result['restored_original_files'], 0)

    def test_detects_tampered_published_member(self):
        stream = packed({'judge/a/events.jsonl': b'{}\n'},
                        mutate=lambda m: m.update({'judge/a/events.jsonl': b'[]\n'}))
        with zipfile.ZipFile(stream) as archive, self.assertRaisesRegex(ValueError, 'published hash'):
            verifier.verify_hashes(archive)

    def test_requires_every_member_in_both_manifests(self):
        stream = packed({'judge/a/events.jsonl': b'{}\n'},
                        mutate=lambda m: m.update({'unlisted.json': b'{}'}))
        with zipfile.ZipFile(stream) as archive, self.assertRaisesRegex(ValueError, 'manifest membership'):
            verifier.verify_hashes(archive)

    def test_rejects_duplicate_manifest_rows(self):
        def duplicate(members):
            members['SHA256SUMS-published'] *= 2
        with zipfile.ZipFile(packed({'judge/a/file': b'x'}, mutate=duplicate)) as archive:
            with self.assertRaisesRegex(ValueError, 'duplicate manifest'):
                verifier.verify_hashes(archive)

    def test_rejects_traversal_even_without_extraction(self):
        with zipfile.ZipFile(packed({'../escape': b'x'})) as archive:
            with self.assertRaisesRegex(ValueError, 'unsafe archive'):
                verifier.verify_hashes(archive)

    def test_restores_only_documented_synthetic_substitution(self):
        name = 'judge/a/private/requests.jsonl'
        source = b'prefix ' + verifier.SYNTHETIC_KEY.encode() + b' suffix'
        public = source.replace(verifier.SYNTHETIC_KEY.encode(), verifier.PLACEHOLDER.encode())
        stream = packed({name: public}, original={name: source},
                        changes={name: {'fake_key_replacements': 1}})
        with zipfile.ZipFile(stream) as archive:
            result = verifier.verify_hashes(archive)
        self.assertEqual(result['restored_original_files'], 1)

    def test_rejects_false_transformation_count(self):
        name = 'judge/a/private/requests.jsonl'
        stream = packed({name: verifier.PLACEHOLDER.encode()},
                        original={name: verifier.SYNTHETIC_KEY.encode()},
                        changes={name: {'fake_key_replacements': 2}})
        with zipfile.ZipFile(stream) as archive, self.assertRaisesRegex(ValueError, 'replacement count'):
            verifier.verify_hashes(archive)

    def test_rejects_duplicate_json_keys(self):
        with self.assertRaisesRegex(ValueError, 'duplicate JSON'):
            verifier.decode_json('{"calls": 1, "calls": 0}')

    def test_receipt_prompt_binding_detects_changed_prompt(self):
        request = {'system': 'system', 'user': 'input'}
        digest = hashlib.sha256(json.dumps(request, sort_keys=True, separators=(',', ':'),
                                           ensure_ascii=False).encode()).hexdigest()
        event = {'logical_request_id': 'one', 'prompt_sha256': digest,
                 'attempts': [], 'provider_status': 'completed'}
        receipt = dict(event, status='completed', request=request,
                       retention_truncated={'system': False, 'user': False, 'response': False})
        verifier.verify_receipt(event, receipt)
        receipt['request'] = dict(request, user='changed')
        with self.assertRaisesRegex(ValueError, 'prompt hash'):
            verifier.verify_receipt(event, receipt)

    def test_receipt_binding_rejects_missing_retention_evidence(self):
        with self.assertRaisesRegex(ValueError, 'retention'):
            verifier.verify_receipt({}, {'retention_truncated': {'system': True}})

    def run_fixture(self, *, mutate=None):
        root = 'judge/demo/f00'
        request = {'system': 'system', 'user': 'input'}
        hashed = hashlib.sha256(json.dumps(request, sort_keys=True, separators=(',', ':'),
                                           ensure_ascii=False).encode()).hexdigest()
        base = {'case_id': 'case-01', 'condition': 'hidden-cell', 'agent_id': 'A000',
                'prompt_sha256': hashed, 'ok': True, 'provider_status': 'completed',
                'provider_attempts': 1, 'cost_usd': 0.1, 'held_usd': 0,
                'attempts': [{'cost_usd': 0.1, 'finish_reason': 'stop', 'status': 'succeeded'}]}
        events = [dict(base, type='vote', logical_request_id='vote', vote='deny', wave=0),
                  dict(base, type='attestation', logical_request_id='audit', outcome='abstain',
                       sign=False, seat=0)]
        receipts = [dict(logical_request_id=e['logical_request_id'], prompt_sha256=hashed,
                         request=request, attempts=e['attempts'], status='completed',
                         retention_truncated={'system': False, 'user': False, 'response': False})
                    for e in events]
        records = {'events.jsonl': events, 'private/requests.jsonl': receipts,
                   'truth.json': {'cases': {'case-01': {'valid': False, 'kind': 'harm_easy'}},
                                  'targets': ['case-01'], 'committees': {'case-01': ['A000']},
                                  'colluders': []},
                   'manifest.json': {'calls': 2, 'errors': 0, 'abstentions': 1, 'provider_attempts': 2,
                                     'cost_usd': 0.2, 'held_usd': 0, 'logical_responses_completed': 2,
                                     'scheduled_logical_requests': 2, 'incomplete': False,
                                     'agents': 1, 'conditions': ['hidden-cell']},
                   'decisions.json': [{'case_id': 'case-01', 'condition': 'hidden-cell',
                                       'approvals': 0, 'denials': 1, 'majority_approve': False,
                                       'signatures': [False],
                                       'regimes': {r: {'effect': False} for r in verifier.REGIMES}}]}
        if mutate:
            mutate(records)
        files = {root + '/' + name: (''.join(json.dumps(row) + '\n' for row in value).encode()
                                   if name.endswith('.jsonl') else json.dumps(value).encode())
                 for name, value in records.items()}
        with zipfile.ZipFile(packed(files)) as archive:
            return verifier.summarize_run(archive, root, set(files))

    def test_auditor_abstention_counts_in_accounting_but_is_no_signature(self):
        result = self.run_fixture()
        self.assertEqual(result['accounting']['abstentions'], 1)
        self.assertEqual(result['abstentions']['attestation'], 1)
        self.assertEqual(result['honest_by_kind']['attestation']['harm_easy']['n'], 1)

    def test_missing_receipt_is_not_a_successful_complete_run(self):
        with self.assertRaisesRegex(ValueError, 'missing retained'):
            self.run_fixture(mutate=lambda r: r['private/requests.jsonl'].pop())

    def test_tampered_decision_tally_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'decision tally'):
            self.run_fixture(mutate=lambda r: r['decisions.json'][0].update(approvals=1))

    def test_absent_stopped_manifest_remains_unknown(self):
        result = self.run_fixture(mutate=lambda r: r.pop('manifest.json'))
        self.assertIsNone(result['declared_incomplete'])
        self.assertIn('manifest.json', result['missing_files'])

    def test_costs_cannot_be_shifted_between_request_identities(self):
        def shift(records):
            records['events.jsonl'][0]['cost_usd'] = 0.2
            records['events.jsonl'][1]['cost_usd'] = 0.0
        with self.assertRaisesRegex(ValueError, 'request cost'):
            self.run_fixture(mutate=shift)

    def test_explicit_attempt_accounting_must_match_event(self):
        for field, value in [('held_usd', 10), ('provider_attempts', 7)]:
            def mismatch(records):
                for event, receipt in zip(records['events.jsonl'], records['private/requests.jsonl']):
                    event['attempts'][0][field] = value
                    receipt['attempts'][0][field] = value
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, 'attempt accounting'):
                self.run_fixture(mutate=mismatch)

    def test_missing_attempt_fields_are_reported_as_unverified(self):
        result = self.run_fixture()
        self.assertEqual(result['accounting']['unverified_attempt_fields'],
                         {'held_usd': 2, 'provider_attempts': 2})

    def test_non_boolean_completion_cannot_disable_coverage_checks(self):
        def malformed(records):
            records['manifest.json']['incomplete'] = 'false'
            records['manifest.json']['scheduled_logical_requests'] = 999
            records.pop('decisions.json')
        with self.assertRaisesRegex(ValueError, 'manifest incomplete must be boolean'):
            self.run_fixture(mutate=malformed)

    def test_empty_conditions_cannot_make_missing_decisions_complete(self):
        def malformed(records):
            records['manifest.json']['conditions'] = []
            records.pop('decisions.json')
        with self.assertRaisesRegex(ValueError, 'manifest conditions'):
            self.run_fixture(mutate=malformed)

    def test_present_invalid_manifest_is_not_treated_as_absent(self):
        for value in ({}, [], False, None):
            def malformed(records):
                records['manifest.json'] = value
                records.pop('decisions.json')
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, 'manifest'):
                self.run_fixture(mutate=malformed)


if __name__ == '__main__':
    unittest.main()
