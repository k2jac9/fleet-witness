"""Required review stages fail closed without discarding paid-attempt evidence."""
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from fleet_witness.swarm import providers as p
from scripts import peer_review_visual as peer
from test_research_requests import (OfflineTransport, assert_cancelled_attempt, fixture_authorizations,
                                    invoke, offline, response)
from test_swarm_provider import SyntheticSourceTestCase


PLAN = {'summary': 'A synthetic plan.', 'will_it_answer_the_questions': 'The fixture is bounded.',
        'predicted_scores_if_executed_well': {'impact_innovation': 3, 'execution': 3, 'presentation': 3},
        'top_changes': [], 'concerns': [], 'cut_if_short_on_time': [], 'verdict': 'proceed'}
REVIEW = {'summary': 'A synthetic paper.',
          'scores': {'impact_innovation': 3, 'execution': 3, 'presentation': 3,
                     'formality_aesthetics': 3, 'readability': 3},
          'score_rationale': {'impact_innovation': 'Scope is clear.', 'execution': 'Methods are stated.',
                              'presentation': 'Readable.', 'formality_aesthetics': 'Source structure is clear.',
                              'readability': 'Prose is direct.'},
          'strengths': [], 'concerns': [], 'readability_examples': [], 'verdict': 'weak accept', 'confidence': 3}
AUDIT = {'checked_claims': 1, 'issues': [], 'notes': 'One supplied claim checked.'}
DEBATE = {'judgements': [], 'revised_own_concerns': [], 'withdrawn': [], 'new_concerns': [],
          'rebuttals': [], 'updated_scores': REVIEW['scores'], 'updated_verdict': 'weak accept'}


def review_fixture(root):
    models = list(dict.fromkeys([*peer.REVIEWERS, peer.AUDITOR, peer.CHAIR]))
    ledger, path = fixture_authorizations(root, models)
    plan, tex, guidelines, data = (root / name for name in ('plan.md', 'paper.tex', 'guidelines.md', 'data.md'))
    for file, text in ((plan, 'Synthetic plan.'), (tex, 'One synthetic result: 1.'),
                       (guidelines, 'Judge the supplied evidence.'), (data, 'Synthetic result: 1.')):
        file.write_text(text)
    args = SimpleNamespace(plan=str(plan), tex=str(tex), pdf=None, guidelines=str(guidelines),
                           data=[str(data)], out=str(root / 'review'), max_usd=1, max_tokens=None,
                           reasoning='high', debate_rounds=0, authorization=str(path), live=True)
    return ledger, args


class PeerReviewTest(SyntheticSourceTestCase):
    def test_review_cancellation_retains_actual_attempt_and_propagates_original_exception(self):
        for interruption in (KeyboardInterrupt(), SystemExit(23)):
            with self.subTest(interruption=type(interruption).__name__), tempfile.TemporaryDirectory() as temp:
                ledger, args = review_fixture(Path(temp))
                out = Path(args.out)
                out.mkdir()
                transport = OfflineTransport(error=interruption)
                with offline(transport), redirect_stdout(io.StringIO()):
                    with self.assertRaises(type(interruption)) as caught:
                        peer.review_plan(args, out)
                self.assertIs(caught.exception, interruption)
                manifest = json.loads((out / 'manifest.json').read_text())
                self.assertEqual(manifest['status'], 'failed')
                self.assertEqual(manifest['completed_stages'], [])
                attempt = assert_cancelled_attempt(self, ledger, manifest, out / 'private/requests.jsonl', interruption)
                self.assertEqual(manifest['calls'][0]['attempts'], [attempt])
                self.assertEqual(len(transport.requests), 1)
                self.assertFalse((out / 'plan_meta_review.md').exists())

    def run_plan(self, args, transport):
        out = Path(args.out)
        out.mkdir()
        with offline(transport), patch.object(peer.time, 'sleep', return_value=None), redirect_stdout(io.StringIO()):
            try:
                peer.review_plan(args, out)
            except (p.ProviderError, ValueError, TimeoutError):
                pass
        manifest = out / 'manifest.json'
        self.assertTrue(manifest.exists(), 'every terminal plan-review path must retain a manifest')
        return json.loads(manifest.read_text())

    def test_ambiguous_failure_is_one_attempt_with_held_manifest_receipt(self):
        with tempfile.TemporaryDirectory() as temp:
            ledger, args = review_fixture(Path(temp))
            transport = OfflineTransport(error=TimeoutError('synthetic timeout'))
            manifest = self.run_plan(args, transport)
            self.assertEqual(manifest.get('status'), 'failed')
            self.assertEqual(len(transport.requests), 1)
            self.assertEqual(manifest['provider_attempts'], 1)
            self.assertEqual(ledger.calls, 1)
            self.assertGreater(manifest['held_usd'], 0)
            self.assertEqual(manifest['held_usd'], ledger.run_reserved)
            self.assertEqual(manifest['calls'][0]['attempts'][0]['status'], 'unresolved')
            receipts = Path(args.out) / 'private/requests.jsonl'
            self.assertEqual(len(receipts.read_text().splitlines()), 1)
            self.assertFalse((Path(args.out) / 'plan_meta_review.md').exists())

    def test_truncated_or_schema_invalid_plan_never_reaches_chair(self):
        variants = [response(json.dumps(PLAN), finish='length'), response(''), response('{}'),
                    response('{"summary":"broken"'),
                    response(json.dumps({**PLAN, 'verdict': 'accept'})),
                    response(json.dumps({**PLAN, 'predicted_scores_if_executed_well':
                                         {'impact_innovation': True, 'execution': 3, 'presentation': 3}}))]
        for payload in variants:
            with self.subTest(payload=payload), tempfile.TemporaryDirectory() as temp:
                ledger, args = review_fixture(Path(temp))
                transport = OfflineTransport([payload])
                manifest = self.run_plan(args, transport)
                self.assertEqual(manifest.get('status'), 'failed')
                self.assertEqual(manifest['provider_attempts'], 1)
                self.assertAlmostEqual(manifest['cost_usd'], .000005)
                self.assertAlmostEqual(ledger.run_spent, .000005)
                self.assertEqual(len(transport.requests), 1)
                self.assertFalse((Path(args.out) / 'plan_meta_review.md').exists())
                receipt = json.loads((Path(args.out) / 'private/requests.jsonl').read_text().splitlines()[0])
                self.assertEqual(len(receipt['attempts']), 1)
                self.assertEqual(receipt['response_text'], payload['choices'][0]['message']['content'])

    def test_valid_plan_requires_every_review_and_chair_before_completed(self):
        with tempfile.TemporaryDirectory() as temp:
            ledger, args = review_fixture(Path(temp))
            transport = OfflineTransport([*[response(json.dumps(PLAN)) for _ in peer.REVIEWERS],
                                          response('# Assessment\nProceed with the bounded plan.')])
            manifest = self.run_plan(args, transport)
            self.assertEqual(manifest.get('status'), 'completed')
            self.assertTrue(manifest['gated_workflow'])
            self.assertEqual(manifest['provider_attempts'], 5)
            self.assertEqual(len(manifest['completed_stages']), 5)
            self.assertEqual(ledger.calls, 5)
            self.assertEqual(transport.max_active, 1)

    def test_required_paper_audit_cannot_complete_on_bad_or_truncated_json(self):
        variants = [response(json.dumps(AUDIT), finish='max_tokens'), response(''), response('{}'),
                    response(json.dumps({**AUDIT, 'checked_claims': -1})),
                    response(json.dumps({**AUDIT, 'issues': 'none'}))]
        for payload in variants:
            with self.subTest(payload=payload), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                ledger, args = review_fixture(root)
                transport = OfflineTransport([*[response(json.dumps(REVIEW)) for _ in peer.REVIEWERS], payload])
                with offline(transport):
                    code = invoke(peer, ['--tex', args.tex, '--guidelines', args.guidelines, '--data', args.data[0],
                                         '--out', args.out, '--authorization', args.authorization, '--live'])
                self.assertNotEqual(code, 0)
                manifest_path = Path(args.out) / 'manifest.json'
                self.assertTrue(manifest_path.exists(), 'failed audit must retain the pipeline record')
                manifest = json.loads(manifest_path.read_text())
                self.assertEqual(manifest['status'], 'partial')
                self.assertEqual(manifest['review_mode'], 'text-only')
                self.assertEqual(manifest['page_images'], 0)
                self.assertEqual(len(manifest['completed_stages']), 4)
                self.assertEqual(manifest['provider_attempts'], 5)
                self.assertEqual(ledger.calls, 5)
                self.assertAlmostEqual(manifest['cost_usd'], .000025)
                self.assertFalse((Path(args.out) / 'meta_review.md').exists())
                receipts = (Path(args.out) / 'private/requests.jsonl').read_text().splitlines()
                self.assertEqual(len(receipts), 5)
                self.assertEqual(json.loads(receipts[-1])['response_text'],
                                 payload['choices'][0]['message']['content'])

    def test_image_content_is_explicitly_refused_without_silent_flattening(self):
        with self.assertRaisesRegex((ValueError, p.ProviderError), 'image|qualified|text'):
            peer.content('Review this paper.', ['synthetic-encoded-page'])
        self.assertEqual(peer.content('Text-only paper.', []), 'Text-only paper.')

    def test_programmatic_review_cannot_ignore_an_image_mode_request(self):
        with tempfile.TemporaryDirectory() as temp:
            ledger, args = review_fixture(Path(temp))
            args.pdf = 'unread-image-input.pdf'
            out = Path(args.out)
            out.mkdir()
            transport = OfflineTransport([response(json.dumps(PLAN))])
            with offline(transport), redirect_stdout(io.StringIO()):
                with self.assertRaisesRegex((ValueError, p.ProviderError), 'image|PDF'):
                    peer.review_plan(args, out)
            self.assertEqual(transport.requests, [])
            self.assertEqual(ledger.calls, 0)

    def test_empty_chair_keeps_four_reviews_but_does_not_complete_pipeline(self):
        with tempfile.TemporaryDirectory() as temp:
            ledger, args = review_fixture(Path(temp))
            transport = OfflineTransport([*[response(json.dumps(PLAN)) for _ in peer.REVIEWERS], response('')])
            manifest = self.run_plan(args, transport)
            self.assertEqual(manifest['status'], 'partial')
            self.assertEqual(len(manifest['completed_stages']), 4)
            self.assertEqual(manifest['failed_stage'], 'chair')
            self.assertEqual(manifest['calls'][-1]['status'], 'invalid_output')
            self.assertEqual(ledger.calls, 5)
            self.assertAlmostEqual(manifest['cost_usd'], .000025)
            self.assertFalse((Path(args.out) / 'plan_meta_review.md').exists())

    def test_invalid_nested_review_and_duplicate_json_are_incomplete(self):
        invalid = [json.dumps({**REVIEW, 'concerns': [{'id': 'C1', 'severity': 'critical'}]}),
                   json.dumps({**REVIEW, 'confidence': True}),
                   json.dumps({**REVIEW, 'unexpected': 'field'}),
                   json.dumps(REVIEW)[:-1] + ',"summary":"duplicate"}',
                   json.dumps({**REVIEW, 'scores': {**REVIEW['scores'], 'execution': float('nan')}})]
        for text in invalid:
            with self.subTest(text=text), tempfile.TemporaryDirectory() as temp:
                ledger, args = review_fixture(Path(temp))
                transport = OfflineTransport([response(text)])
                with offline(transport):
                    code = invoke(peer, ['--tex', args.tex, '--guidelines', args.guidelines, '--data', args.data[0],
                                         '--out', args.out, '--authorization', args.authorization, '--live'])
                self.assertNotEqual(code, 0)
                manifest = json.loads((Path(args.out) / 'manifest.json').read_text())
                self.assertEqual(manifest['status'], 'failed')
                self.assertEqual(manifest['calls'][0]['status'], 'invalid_output')
                self.assertEqual(ledger.calls, 1)
                self.assertAlmostEqual(manifest['cost_usd'], .000005)

    def test_oversized_audit_input_keeps_prior_receipts_and_refuses_dispatch(self):
        with tempfile.TemporaryDirectory() as temp:
            ledger, args = review_fixture(Path(temp))
            Path(args.data[0]).write_text('x' * 32768)
            transport = OfflineTransport([response(json.dumps(REVIEW))])
            with offline(transport):
                code = invoke(peer, ['--tex', args.tex, '--guidelines', args.guidelines, '--data', args.data[0],
                                     '--out', args.out, '--authorization', args.authorization, '--live'])
            self.assertNotEqual(code, 0)
            manifest = json.loads((Path(args.out) / 'manifest.json').read_text())
            self.assertEqual(manifest['status'], 'partial')
            self.assertEqual(manifest['failed_stage'], 'audit')
            self.assertEqual(manifest['provider_attempts'], 4)
            self.assertEqual(ledger.calls, 4)
            self.assertEqual(len(transport.requests), 4)
            self.assertEqual(manifest['calls'][-1]['provider_attempts'], 0)
            self.assertEqual(manifest['calls'][-1]['status'], 'refused')
            self.assertAlmostEqual(manifest['cost_usd'], .000020)
            receipts = (Path(args.out) / 'private/requests.jsonl').read_text().splitlines()
            self.assertEqual(len(receipts), 5)
            self.assertEqual(json.loads(receipts[-1])['attempts'], [])

    def test_missing_usage_audit_retains_shared_hold_and_stops_chair(self):
        with tempfile.TemporaryDirectory() as temp:
            ledger, args = review_fixture(Path(temp))
            transport = OfflineTransport([*[response(json.dumps(REVIEW)) for _ in peer.REVIEWERS],
                                          response(json.dumps(AUDIT), usage=False)])
            with offline(transport):
                code = invoke(peer, ['--tex', args.tex, '--guidelines', args.guidelines, '--data', args.data[0],
                                     '--out', args.out, '--authorization', args.authorization, '--live'])
            self.assertNotEqual(code, 0)
            manifest = json.loads((Path(args.out) / 'manifest.json').read_text())
            self.assertEqual(manifest['status'], 'partial')
            self.assertEqual(manifest['provider_attempts'], 5)
            self.assertAlmostEqual(manifest['cost_usd'], .000020)
            self.assertGreater(manifest['held_usd'], 0)
            self.assertEqual(manifest['held_usd'], ledger.run_reserved)
            self.assertEqual(manifest['calls'][-1]['attempts'][0]['status'], 'unresolved')
            self.assertEqual(len(transport.requests), 5)
            self.assertFalse((Path(args.out) / 'meta_review.md').exists())

    def test_complete_paper_review_with_debate_uses_text_only_and_one_shared_envelope(self):
        with tempfile.TemporaryDirectory() as temp:
            ledger, args = review_fixture(Path(temp))
            transport = OfflineTransport([*[response(json.dumps(REVIEW)) for _ in peer.REVIEWERS],
                                          response(json.dumps(AUDIT)),
                                          *[response(json.dumps(DEBATE)) for _ in peer.REVIEWERS],
                                          response('# Assessment\nBounded synthetic review complete.')])
            with offline(transport):
                code = invoke(peer, ['--tex', args.tex, '--guidelines', args.guidelines, '--data', args.data[0],
                                     '--out', args.out, '--authorization', args.authorization, '--live',
                                     '--debate-rounds', '1'])
            self.assertEqual(code, 0)
            manifest = json.loads((Path(args.out) / 'manifest.json').read_text())
            self.assertEqual(manifest['status'], 'completed')
            self.assertEqual(manifest['completed_stages'], manifest['required_stages'])
            self.assertEqual(manifest['provider_attempts'], 10)
            self.assertEqual(ledger.calls, 10)
            self.assertFalse(manifest['visual_assessment'])
            self.assertEqual(manifest['page_images'], 0)
            self.assertEqual(transport.max_active, 1)
            self.assertTrue(all(isinstance(message['content'], str) for request in transport.requests
                                for message in request['messages']))


if __name__ == '__main__':
    unittest.main()
