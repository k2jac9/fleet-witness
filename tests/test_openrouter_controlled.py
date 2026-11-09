"""Controlled OpenRouter behavior with a real ledger and synthetic transport."""
from contextlib import closing
import copy
import json
from pathlib import Path
import sqlite3
import ssl
import tempfile
from unittest.mock import patch

from fleet_witness import controlled_calibration as calibration
from fleet_witness.swarm import providers as p, secure_transport as secure
from test_controlled_calibration import facts
from test_secure_transport import runtime_profile
from test_swarm_provider import SyntheticSourceTestCase, authorization


def response(text='{"recommendation":"deny","reason":"Build evidence does not authorize release."}'):
    return {'id': 'gen-synthetic-one', 'model': 'fixture-model', 'provider': 'Fixture Provider',
            'object': 'chat.completion', 'created': 1700000000, 'service_tier': 'default',
            'choices': [{'index': 0, 'finish_reason': 'stop', 'native_finish_reason': 'stop',
                         'message': {'role': 'assistant', 'content': text, 'refusal': None,
                                     'reasoning': None, 'reasoning_details': []}, 'logprobs': None}],
            'usage': {'prompt_tokens': 10, 'completion_tokens': 20, 'total_tokens': 30,
                      'cost': 0.00003, 'is_byok': False,
                      'completion_tokens_details': {'reasoning_tokens': 10}}}


class OpenRouterControlledTests(SyntheticSourceTestCase):
    def setUp(self):
        super().setUp()
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve()
        key = self.root / 'key'
        key.write_text('synthetic-private-openrouter-key\n'); key.chmod(0o600)
        ca = self.root / 'ca.pem'; ca.write_text('synthetic fixture only')
        self.ledger = p.Ledger('openrouter', 15, 50, self.root / 'spend-ledger.sqlite3', run_id='one-call')
        self.record = authorization(self.ledger)
        self.record.update(schema_version='controlled-openrouter-v1', run_cap_usd='15',
                           provider_cap_usd='50', request_limit=1)
        self.record['openrouter'] = {'provider_slug': 'fixture/standard', 'provider_name': 'Fixture Provider',
                                    'response_model': 'fixture-model', 'reasoning_effort': 'low',
                                    'output_token_parameter': 'max_completion_tokens',
                                    'transport': runtime_profile(key, ca, ['a' * 64])}
        substitute = patch.object(secure, 'prepare', return_value=ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT))
        substitute.start(); self.addCleanup(substitute.stop)

    def client(self, record=None):
        try:
            return p.ModelClient('openrouter', 'fixture-model', self.ledger, max_output_tokens=100,
                                 timeout=1, authorization=record or self.record)
        except p.ProviderError as error:
            self.fail('qualified controlled OpenRouter profile was refused: ' + str(error))

    def attempt(self, value=None, presentation='raw'):
        with patch.object(p, '_post', return_value=json.dumps(value or response()).encode()), \
                patch.object(p, '_env_key', side_effect=AssertionError('environment key used')):
            return self.client().recommend(facts(), presentation)

    def test_qualified_request_uses_private_key_fixed_route_schema_and_atomic_proposal(self):
        outcome = self.attempt()
        self.assertEqual(outcome['status'], 'succeeded')
        self.assertEqual(outcome['proposal']['recommendation'], 'deny')
        with closing(sqlite3.connect(self.ledger.path)) as db:
            row = db.execute('SELECT request_json,receipt_json,reserved,settled FROM requests').fetchone()
            tables = {item[0] for item in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        request, receipt = json.loads(row[0]), json.loads(row[1])
        self.assertEqual(json.loads(request['messages'][1]['content']), facts())
        self.assertEqual(request['provider'], {'only': ['fixture/standard'], 'order': ['fixture/standard'], 'allow_fallbacks': False,
                         'require_parameters': True, 'data_collection': 'deny', 'zdr': True,
                         'max_price': {'prompt': 1, 'completion': 1, 'request': 0}})
        self.assertEqual(request['service_tier'], 'default')
        self.assertEqual(request['reasoning'], {'effort': 'low', 'exclude': True})
        self.assertEqual(request['max_completion_tokens'], 100)
        self.assertNotIn('max_tokens', request)
        self.assertNotIn('temperature', request)
        self.assertIs(request['store'], False)
        self.assertEqual(request['tools'], [])
        self.assertEqual(request['tool_choice'], 'none')
        self.assertEqual(request['response_format']['type'], 'json_schema')
        self.assertIs(request['response_format']['json_schema']['strict'], True)
        self.assertEqual(receipt['proposal'], outcome['proposal'])
        self.assertEqual(row[2], 15_000_000_000)
        self.assertEqual(row[3], 30_000)
        self.assertNotIn('releases', tables)
        self.assertNotIn('synthetic-private-openrouter-key', json.dumps(request))

    def test_presentation_changes_only_instruction_with_identical_facts(self):
        client = self.client()
        requests = []
        def capture(url, key, body, *args, **kwargs):
            requests.append(body)
            raise TimeoutError()
        for presentation in ('raw', 'scope_explicit'):
            # Compare construction without evading the one-call ledger limit.
            from fleet_witness.gateway import provider_input
            visible = provider_input(facts(), presentation)
            requests.append(client._body(visible['instruction'], json.dumps(visible['facts'],sort_keys=True),100))
        self.assertEqual(requests[0]['messages'][1], requests[1]['messages'][1])
        self.assertNotEqual(requests[0]['messages'][0], requests[1]['messages'][0])
        self.assertEqual({k:v for k,v in requests[0].items() if k != 'messages'},
                         {k:v for k,v in requests[1].items() if k != 'messages'})

    def test_envelope_identity_tools_cost_and_ambiguous_output_fail_closed(self):
        variants = []
        for field, value in (('model','other-model'),('provider','Other Provider'),('id','bad/id'),
                             ('service_tier','priority'),('object','chat.completion.chunk')):
            item=response(); item[field]=value; variants.append(item)
        item=response(); del item['usage']['cost']; variants.append(item)
        item=response(); item['usage']['cost']=True; variants.append(item)
        item=response(); item['usage']['cost']=-1; variants.append(item)
        item=response(); item['usage']['is_byok']=True; variants.append(item)
        item=response(); item['choices'][0]['message']['tool_calls']=[{'function':{'name':'release'}}]; variants.append(item)
        item=response(); item['choices'][0]['message']['role']='system'; variants.append(item)
        item=response(); item['choices'][0]['index']=1; variants.append(item)
        item=response(); item['choices'][0]['message']['unexpected']='x'; variants.append(item)
        item=response(); item['choices'][0]['message']['refusal']='cannot answer'; variants.append(item)
        item=response(); item['choices'][0]['message']['reasoning']='hidden text'; variants.append(item)
        item=response(); item['usage']['completion_tokens_details']['reasoning_tokens']=21; variants.append(item)
        item=response(); item['usage']['prompt_tokens_details']={'cached_tokens':11}; variants.append(item)
        item=response(); item['usage']['prompt_tokens_details']={'audio_tokens':1}; variants.append(item)
        item=response(); item['unexpected_output']={'tool':'release'}; variants.append(item)
        item=response(); item['choices'][0]['native_finish_reason']='length'; variants.append(item)
        for index, item in enumerate(variants):
            with self.subTest(index=index):
                self.ledger=p.Ledger('openrouter',15,50,self.root/f'case-{index}.sqlite3',run_id=f'case-{index}')
                self.record.update(ledger_path=str(self.ledger.path),run_id=self.ledger.run_id)
                with self.assertRaises(p.ProviderError): self.attempt(item)
                self.assertGreaterEqual(self.ledger.run_reserved,15)
                self.assertTrue(self.ledger.snapshot()['halted'])

    def test_generation_and_reported_charge_survive_invalid_identity(self):
        item=response(); item['model']='wrong-model'
        with self.assertRaises(p.ProviderError) as raised: self.attempt(item)
        attempt=raised.exception.attempts[0]
        self.assertEqual(attempt['provider_request_id'],'gen-synthetic-one')
        self.assertEqual(attempt['provider_reported_cost_usd'],'0.00003')

    def test_parseable_http_error_retains_known_larger_liability(self):
        item=response(); item['usage']['cost']=20
        client=self.client()
        with patch.object(p,'_post',side_effect=p.TransportFailure('http_error',raw=json.dumps(item).encode(),http_status=500)):
            with self.assertRaises(p.ProviderError) as raised: client.recommend(facts(),'raw')
        self.assertEqual(self.ledger.run_reserved,20)
        self.assertEqual(raised.exception.attempts[0]['provider_request_id'],'gen-synthetic-one')
        self.assertEqual(raised.exception.attempts[0]['provider_reported_cost_usd'],'20')

    def test_changed_cached_prices_do_not_reduce_authorized_accounting_bound(self):
        client=self.client(); client.prices=(0,0)
        item=response(); item['usage']['cost']=0
        with patch.object(p,'_post',return_value=json.dumps(item).encode()):
            outcome=client.recommend(facts(),'raw')
        self.assertEqual(outcome['cost_usd'],0.00003)
        self.assertEqual(outcome['attempts'][0]['provider_reported_cost_usd'],'0')

    def test_valid_looking_authorization_changes_refused_before_credentials_or_reservation(self):
        variants = [('openrouter', 'provider_slug', 'unreviewed/route'),
                    ('openrouter', 'reasoning_effort', 'none'),
                    ('pricing', 'input_per_million', '0'),
                    ('pricing', 'output_per_million', '0')]
        for section, field, value in variants:
            with self.subTest(field=field):
                client = self.client()
                client.authorization[section][field] = value
                with patch.object(secure, 'read_key') as key, patch.object(p, '_post') as post:
                    with self.assertRaises(p.ProviderError): client.recommend(facts(), 'raw')
                    key.assert_not_called(); post.assert_not_called()
                self.assertEqual(self.ledger.calls, 0)

    def test_encoded_credential_echo_is_removed_from_http_and_partial_receipts(self):
        key = 'synthetic-private-openrouter-key'
        encoded = ''.join('\\u%04x' % ord(char) for char in key)
        mixed = ''.join('\\u%04X' % ord(char) if i % 2 else char for i, char in enumerate(key))
        for index, value in enumerate((encoded, mixed, encoded + '"BROKEN')):
            with self.subTest(index=index):
                self.ledger = p.Ledger('openrouter', 15, 50, self.root/f'echo-{index}.sqlite3', run_id=f'echo-{index}')
                self.record.update(ledger_path=str(self.ledger.path), run_id=self.ledger.run_id)
                raw = ('{"error":{"message":"' + value + '"}}').encode()
                with patch.object(p, '_post', side_effect=p.TransportFailure('http_error', raw=raw, http_status=500)):
                    with self.assertRaises(p.ProviderError) as caught: self.client().recommend(facts(), 'raw')
                with closing(sqlite3.connect(self.ledger.path)) as db:
                    stored = db.execute('SELECT response_raw FROM requests').fetchone()[0]
                self.assertTrue(caught.exception.attempts[0].get('response_redacted'))
                self.assertNotEqual(stored, raw)
                self.assertNotIn(key.encode(), stored)
                if index < 2: self.assertNotIn(key, json.dumps(json.loads(stored)))
                self.assertEqual(self.ledger.run_reserved, 15)

    def test_unqualified_usage_and_cost_details_hold_best_known_liability(self):
        variants = [('audio_tokens', 1, 15), ('server_tool_use', {'web_search_requests': 1}, 15),
                    ('reasoning_tokens', 100000, 15),
                    ('completion_tokens_details', {'cache_write_tokens': 20}, 15),
                    ('prompt_tokens_details', {'reasoning_tokens': 1}, 15),
                    ('cost_details', {'upstream_inference_cost': 20}, 20),
                    ('cost_details', {'upstream_inference_prompt_cost': 12, 'upstream_inference_completions_cost': 9}, 21),
                    ('cost_details', {'upstream_inference_cost': -1}, 15),
                    ('cost_details', {'unknown_fee': 1}, 15),
                    ('cost_details', {'upstream_inference_cost': True}, 15)]
        for index, (field, value, hold) in enumerate(variants):
            with self.subTest(index=index):
                self.ledger = p.Ledger('openrouter', 15, 50, self.root/f'usage-{index}.sqlite3', run_id=f'usage-{index}')
                self.record.update(ledger_path=str(self.ledger.path), run_id=self.ledger.run_id)
                item = response(); item['usage'][field] = value
                with self.assertRaises(p.ProviderError): self.attempt(item)
                self.assertEqual(self.ledger.run_spent, 0)
                self.assertEqual(self.ledger.run_reserved, hold)
                self.assertTrue(self.ledger.snapshot()['halted'])

    def test_http_error_cost_breakdown_preserves_larger_liability(self):
        item = response(); item['usage']['cost_details'] = {'upstream_inference_cost': 20}
        with patch.object(p, '_post', side_effect=p.TransportFailure('http_error', raw=json.dumps(item).encode(), http_status=500)):
            with self.assertRaises(p.ProviderError): self.client().recommend(facts(), 'raw')
        self.assertEqual(self.ledger.run_reserved, 20)

    def test_consistent_known_cost_breakdown_and_zero_nontext_details_accepted(self):
        item = response()
        item['usage']['cost_details'] = {'upstream_inference_cost': 0.00003,
            'upstream_inference_prompt_cost': 0.00001, 'upstream_inference_completions_cost': 0.00002}
        item['usage']['prompt_tokens_details'] = {'cached_tokens': 2, 'cache_write_tokens': 0, 'audio_tokens': 0}
        self.assertEqual(self.attempt(item)['status'], 'succeeded')

    def test_documented_native_completed_and_zero_image_detail_are_accepted(self):
        for index in range(3):
            with self.subTest(index=index):
                self.ledger = p.Ledger('openrouter', 15, 50, self.root/f'accepted-{index}.sqlite3', run_id=f'accepted-{index}')
                self.record.update(ledger_path=str(self.ledger.path), run_id=self.ledger.run_id)
                item = response()
                if index != 1: item['choices'][0]['native_finish_reason'] = 'completed'
                if index != 0: item['usage']['completion_tokens_details']['image_tokens'] = 0
                outcome = self.attempt(item)
                self.assertEqual(outcome['status'], 'succeeded')
                self.assertEqual(outcome['proposal']['recommendation'], 'deny')
                self.assertEqual(self.ledger.run_reserved, 0)

    def test_positive_image_usage_and_completed_truncation_remain_unresolved(self):
        for index in range(2):
            with self.subTest(index=index):
                self.ledger = p.Ledger('openrouter', 15, 50, self.root/f'native-{index}.sqlite3', run_id=f'native-{index}')
                self.record.update(ledger_path=str(self.ledger.path), run_id=self.ledger.run_id)
                item = response()
                if index == 0: item['usage']['completion_tokens_details']['image_tokens'] = 1
                else:
                    item['choices'][0]['finish_reason'] = 'length'
                    item['choices'][0]['native_finish_reason'] = 'completed'
                with self.assertRaises(p.ProviderError): self.attempt(item)
                self.assertEqual(self.ledger.run_reserved, 15)
                self.assertEqual(self.ledger.run_spent, 0)

    def test_invalid_proposal_and_truncation_are_accounted_without_invented_denial(self):
        item=response('{"recommendation":"deny","reason":"x","extra":true}')
        item['choices'][0]['finish_reason']='length'
        item['choices'][0]['native_finish_reason']='length'
        outcome=self.attempt(item)
        self.assertEqual(outcome['status'],'invalid_output')
        self.assertIsNone(outcome['proposal'])
        self.assertTrue(outcome['truncated'])
        self.assertEqual(self.ledger.run_reserved,0)
        self.assertEqual(self.ledger.run_spent,0.00003)

    def test_reasoning_only_truncation_with_null_content_is_accounted_invalid(self):
        item=response(None)
        item['choices'][0]['finish_reason']='length'
        item['choices'][0]['native_finish_reason']='length'
        outcome=self.attempt(item)
        self.assertEqual(outcome['status'],'invalid_output')
        self.assertIsNone(outcome['proposal'])
        self.assertEqual(self.ledger.run_spent,0.00003)
        self.assertEqual(self.ledger.run_reserved,0)

    def test_timeout_and_restart_cannot_send_second_request(self):
        client=self.client()
        with patch.object(p,'_post',side_effect=TimeoutError()):
            with self.assertRaises(p.ProviderError): client.recommend(facts(),'raw')
        self.assertEqual(self.ledger.run_reserved,15)
        with patch.object(p,'_post',side_effect=AssertionError('second dispatch')):
            with self.assertRaises(p.ProviderError): self.client().recommend(facts(),'raw')

    def test_profile_tampering_and_generic_complete_are_rejected_before_key(self):
        client=self.client()
        with patch.object(secure,'read_key',side_effect=AssertionError('key read')):
            client.extra_body={'reasoning':{'effort':'none'}}
            with self.assertRaises(p.ProviderError): client.recommend(facts(),'raw')
            client.extra_body={}
            with self.assertRaises(p.ProviderError): client.complete('unqualified arbitrary instruction','data')
            client.authorization['openrouter']['provider_slug']='bad host'
            with self.assertRaises(p.ProviderError): client.recommend(facts(),'raw')
        self.assertEqual(self.ledger.calls,0)

    def test_wrong_schema_caps_or_incomplete_profile_refused(self):
        variants=[]
        for field,value in (('run_cap_usd','15.000000001'),('provider_cap_usd','51'),
                            ('request_limit',2),('max_output_tokens',257),('purpose','confirmatory')):
            item=copy.deepcopy(self.record); item[field]=value; variants.append(item)
        item=copy.deepcopy(self.record); del item['openrouter']['transport']; variants.append(item)
        item=copy.deepcopy(self.record); item['openrouter']['response_model']='~latest'; variants.append(item)
        for item in variants:
            with self.assertRaises(p.ProviderError):
                p.ModelClient('openrouter','fixture-model',self.ledger,max_output_tokens=100,timeout=1,authorization=item)

    def test_runner_selects_openrouter_and_refuses_replay(self):
        auth=self.root/'authorization.json'; auth.write_text(json.dumps(self.record)); auth.chmod(0o600)
        with patch.object(p,'LEDGER_DIR',self.root), patch('fleet_witness.swarm.operator.require_committed_source'), \
                patch.object(p,'_post',return_value=json.dumps(response()).encode()):
            result=calibration.run_calibration(auth,self.root/'result',live=True)
            self.assertEqual(result['outcome']['status'],'succeeded')
            self.assertIsNone(result['controller_effect'])
            self.assertEqual((self.root/'result'/'manifest.json').stat().st_mode & 0o777,0o600)
            with patch.object(p,'_post',side_effect=AssertionError('second network request')):
                again=calibration.run_calibration(auth,self.root/'second',live=True)
                self.assertNotEqual(again['outcome']['status'],'succeeded')

    def test_reviewed_azure_opaque_reasoning_is_inert_and_combined_tokens_are_accounted(self):
        self.record['model']='openai/gpt-6.1-sol'
        self.record['openrouter'].update(provider_slug='azure/us',provider_name='Azure',response_model=self.record['model'])
        item=response();item.update(model=self.record['model'],provider='Azure')
        opaque={'type':'reasoning.encrypted','format':'azure-openai-responses-v1','id':'rs_synthetic123','index':0,'data':'opaque_A0-='*20}
        item['choices'][0]['message']['reasoning_details']=[opaque]
        client=p.ModelClient('openrouter',self.record['model'],self.ledger,max_output_tokens=100,timeout=1,authorization=self.record)
        with patch.object(p,'_post',return_value=json.dumps(item).encode()):outcome=client.recommend(facts(),'raw')
        self.assertEqual(outcome['status'],'succeeded')
        self.assertEqual(outcome['output_tokens'],20)
        self.assertNotIn(opaque['data'],json.dumps(outcome))
        with closing(sqlite3.connect(self.ledger.path)) as db:
            request,raw,settled=db.execute('SELECT request_json,response_raw,settled FROM requests').fetchone()
        self.assertNotIn(opaque['data'],request)
        self.assertIn(opaque['data'],raw.decode())
        self.assertEqual(settled,30000)

    def test_opaque_reasoning_does_not_allow_text_other_formats_or_malformed_shapes(self):
        from fleet_witness.swarm.openrouter_controlled import validate_envelope
        record=copy.deepcopy(self.record);record['model']='openai/gpt-6.1-sol'
        record['openrouter'].update(provider_slug='azure/us',provider_name='Azure',response_model=record['model'])
        opaque={'type':'reasoning.encrypted','format':'azure-openai-responses-v1','id':'rs_synthetic123','index':0,'data':'opaque_A0-='*20}
        variants=[]
        for field,value in [('type','reasoning.text'),('format','openai-responses-v1'),('index',True),('index',1),('id',None),('data',''),('data',{'command':'release'}),('data','A'*32769),('data','<script>'),('summary','unapproved text')]:
            value_item=copy.deepcopy(opaque);value_item[field]=value;variants.append([value_item])
        variants.extend([[opaque,opaque],opaque])
        for detail in variants:
            with self.subTest(detail_type=type(detail).__name__):
                item=response();item.update(model=record['model'],provider='Azure');item['choices'][0]['message']['reasoning_details']=detail
                with self.assertRaises(ValueError):validate_envelope(item,record)
