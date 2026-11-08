import copy
from pathlib import Path
import tempfile
import unittest
from fleet_witness.experiment import run_demo
try:
    from fleet_witness.campaign import summarize, run_campaign
except ImportError:
    summarize = run_campaign = None

class CampaignTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(summarize, 'campaign not implemented')
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.replay = run_demo(self.root/'baseline', 42)

    def test_summary_separates_bad_recommendations_from_effects(self):
        s = summarize([self.replay])
        self.assertEqual(s['mode'], 'scripted-campaign')
        self.assertEqual((s['episodes'], s['invalid_recommendations'], s['effects']), (20,7,4))
        self.assertEqual(s['unsafe_effects'], 0)

    def test_unauthorized_effect_refused(self):
        e = next(e for e in self.replay['episodes'] if not e['evaluation']['decision_valid_at_snapshot'])
        e['attempts'][0]['effect_occurred'] = True
        with self.assertRaises(ValueError): summarize([self.replay])

    def test_duplicate_effect_refused(self):
        e = next(e for e in self.replay['episodes'] if e['scenario']=='duplicate_execution')
        e['attempts'][1]['effect_occurred'] = True
        with self.assertRaises(ValueError): summarize([self.replay])

    def test_broken_pair_and_repeated_seed_refused(self):
        with self.assertRaises(ValueError): summarize([self.replay,self.replay])
        self.replay['episodes'][1]['supervisor_input']['facts']['run_id']='changed'
        with self.assertRaises(ValueError): summarize([self.replay])

    def test_correct_denial_never_authorizes_effect(self):
        e = next(e for e in self.replay['episodes'] if e['decision']['recommendation']=='deny' and e['evaluation']['decision_valid_at_snapshot'])
        e['attempts'].append(dict(execution_authorized_at_attempt=True,effect_occurred=True))
        self.replay['summary']['execution_attempts'] += 1
        self.replay['summary']['effects'] += 1
        with self.assertRaises(ValueError): summarize([self.replay])

    def test_committed_and_visible_receipts_cannot_disagree(self):
        self.replay['episodes'][0]['receipts'][0]['scope']='changed'
        with self.assertRaises(ValueError): summarize([self.replay])

    def test_summary_tampering_refused(self):
        self.replay['summary']['effects'] += 1
        with self.assertRaises(ValueError): summarize([self.replay])

    def test_campaign_keeps_databases_outside_only_four_deployable_assets(self):
        s=run_campaign(self.root/'campaign', [41,42])
        self.assertEqual(s['episodes'],40)
        assets=self.root/'campaign'/'public'
        self.assertEqual({p.name for p in assets.iterdir()}, {'index.html','styles.css','app.js','replay.json'})
        self.assertTrue((self.root/'campaign'/'seed-42'/'witness.sqlite3').is_file())
        self.assertIn('40 scripted trials', (assets/'index.html').read_text())
        with self.assertRaises(FileExistsError): run_campaign(self.root/'campaign',[41,42])

class DashboardTargetTests(unittest.TestCase):
    def test_checker_refuses_credential_transmission_to_unsafe_urls(self):
        from scripts.check_dashboard import check
        for url in ('http://example.com','http://localhost','https://user:pass@example.com','https://example.com/extra','https://example.com?token=x','ftp://example.com'):
            with self.subTest(url=url), self.assertRaises(ValueError): check(url,'fake-test-password')

    def test_checker_never_routes_loopback_through_environment_proxy(self):
        import os
        from unittest.mock import patch
        from scripts.check_dashboard import check
        hosts=[]
        def intercept(request):
            hosts.append(request.host)
            raise RuntimeError('offline network interception')
        with patch.dict(os.environ, {'http_proxy':'http://proxy.invalid:8000','no_proxy':''}, clear=True), patch('urllib.request.HTTPHandler.http_open', side_effect=intercept):
            with self.assertRaises(RuntimeError): check('http://127.0.0.1:18766','fake-test-password')
        self.assertEqual(hosts,['127.0.0.1:18766'])
