"""Offline security and recovery cases; synthetic keys and HTTPS only."""
from contextlib import closing
import copy
import json
from pathlib import Path
import sqlite3
import ssl
import tempfile
import unittest
from unittest.mock import patch

from fleet_witness import pilot_design as design
from fleet_witness.gateway import provider_input
from fleet_witness.swarm import providers as p, secure_transport as secure
from fleet_witness.swarm.ledger import canonical_json
from test_swarm_provider import SyntheticSourceTestCase, authorization
from test_secure_transport import runtime_profile
from test_openrouter_controlled import response


class PilotCase(SyntheticSourceTestCase):
    def setUp(self):
        super().setUp()
        temp = tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve()
        key = self.root/'key'; key.write_text('synthetic-pilot-secret'); key.chmod(0o600)
        ca = self.root/'ca'; ca.write_text('synthetic')
        self.ledger = p.Ledger('openrouter', 15, 50, self.root/'ledger.sqlite3', run_id='pilot')
        self.record = authorization(self.ledger, purpose='confirmatory')
        self.record.update(schema_version='controlled-openrouter-pilot-v1', purpose='exploratory',
            model=design.MODEL, run_cap_usd='15', provider_cap_usd='50', request_limit=160,
            max_output_tokens=256, timeout_s=30,
            study={'design_sha256': design.design_sha256(), 'calibration_evidence_sha256': 'c'*64})
        self.record['openrouter'] = {'provider_slug':'azure/us','provider_name':'Azure','response_model':design.MODEL,
            'reasoning_effort':'low','output_token_parameter':'max_completion_tokens',
            'transport':runtime_profile(key,ca,['a'*64])}
        sub=patch.object(secure,'prepare',return_value=ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT));sub.start();self.addCleanup(sub.stop)
        self.plan=design.make_plan(b'k'*32)

    def client(self, record=None):
        return p.ModelClient('openrouter',design.MODEL,self.ledger,max_output_tokens=256,timeout=30,authorization=record or self.record)

    def requests(self,client):
        pairs={x['pair_id']:x for x in self.plan['pairs']}
        result=[]
        for call in self.plan['schedule']:
            visible=provider_input(pairs[call['pair_id']]['facts'],call['presentation'])
            body=client._body(visible['instruction'],canonical_json(visible['facts']),256)
            result.append({'call_id':call['trial_id'],'request_sha256':design.digest(body)})
        return result

    def claim(self,client):
        return self.ledger.claim_cohort(self.record, self.requests(client), plan_sha256=design.digest(self.plan),output_dir=str(self.root/'output'))

    def call(self,client,index,token):
        call=self.plan['schedule'][index];pairs={x['pair_id']:x for x in self.plan['pairs']}
        return client.recommend(pairs[call['pair_id']]['facts'],call['presentation'],call_id=call['trial_id'],cohort_token=token)

    def reply(self,text='{"recommendation":"approve","reason":"synthetic"}'):
        item=response(text);item.update(model=design.MODEL,provider='Azure');return json.dumps(item).encode()


class PilotBoundaryTests(PilotCase):
    def test_qualified_profile_and_attempt_binding_single_use_after_restart(self):
        client=self.client();token=self.claim(client)
        with patch.object(p,'_post',return_value=self.reply()) as post:
            outcome=self.call(client,0,token)
            self.assertEqual(outcome['status'],'succeeded');self.assertEqual(post.call_count,1)
        with closing(sqlite3.connect(self.ledger.path)) as db:
            row=db.execute('SELECT attempt_id FROM cohort_calls WHERE call_id=?',(self.plan['schedule'][0]['trial_id'],)).fetchone()
            self.assertEqual(row[0],outcome['attempts'][0]['attempt_id'])
        reopened=p.Ledger('openrouter',15,50,self.ledger.path,run_id='pilot')
        with self.assertRaises(p.ProviderError):
            reopened.claim_cohort(self.record,self.requests(client),plan_sha256=design.digest(self.plan),output_dir=str(self.root/'other'))
        with patch.object(secure,'read_key',side_effect=AssertionError('key touched')):
            with self.assertRaises(p.ProviderError): self.call(client,1,'lost-session-token')
            with self.assertRaises(p.ProviderError): self.call(client,1,token) # controller not checkpointed
        self.ledger.finish_cohort_call(self.plan['schedule'][0]['trial_id'],token)
        with patch.object(p,'_post',return_value=self.reply()):self.call(client,1,token)

    def test_pilot_cannot_bypass_closed_interface_claim_order_or_request_hash(self):
        client=self.client()
        with patch.object(secure,'read_key',side_effect=AssertionError('key touched')):
            with self.assertRaises(p.ProviderError):client.complete('system','user')
            with self.assertRaises(p.ProviderError):self.call(client,0,None)
            token=self.claim(client)
            with self.assertRaises(p.ProviderError):self.call(client,1,token)
            self.plan['pairs'][0]['facts']['reviewer_statement']='changed'
            index=next(i for i,c in enumerate(self.plan['schedule']) if c['pair_id']==self.plan['pairs'][0]['pair_id'])
            with self.assertRaises(p.ProviderError):self.call(client,index,token)

    def test_incomplete_qualification_or_modified_design_refused_before_key(self):
        variants=[]
        for field,value in [('request_limit',159),('max_output_tokens',255),('max_input_bytes',4097),('purpose','confirmatory')]:
            rec=copy.deepcopy(self.record);rec[field]=value;variants.append(rec)
        rec=copy.deepcopy(self.record);rec['qualification']['calibration_accepted']=False;variants.append(rec)
        rec=copy.deepcopy(self.record);rec['study']['design_sha256']='b'*64;variants.append(rec)
        rec=copy.deepcopy(self.record);rec['pricing']['input_per_million']='100';variants.append(rec)
        with patch.object(secure,'read_key',side_effect=AssertionError('key touched')):
            for rec in variants:
                with self.subTest(record=rec['purpose']):
                    with self.assertRaises(p.ProviderError):self.client(rec)

    def test_invalid_output_stops_remaining_cohort_even_without_hold(self):
        client=self.client();token=self.claim(client)
        with patch.object(p,'_post',return_value=self.reply('invalid')) as post:
            first=self.call(client,0,token)
            self.assertEqual(first['status'],'invalid_output')
            with self.assertRaises(p.ProviderError):self.ledger.finish_cohort_call(self.plan['schedule'][0]['trial_id'],token)
            with self.assertRaises(p.ProviderError):self.call(client,1,token)
            self.assertEqual(post.call_count,1)

    def test_reservation_and_schedule_link_roll_back_together_on_audit_failure(self):
        client=self.client();token=self.claim(client)
        original=self.ledger._audit
        def fail(db,identity,kind,data):
            if kind=='reserved':raise sqlite3.OperationalError('synthetic audit failure')
            original(db,identity,kind,data)
        with patch.object(self.ledger,'_audit',side_effect=fail),patch.object(p,'_post') as post:
            with self.assertRaises(sqlite3.OperationalError):self.call(client,0,token)
            post.assert_not_called()
        with closing(sqlite3.connect(self.ledger.path)) as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM requests').fetchone()[0],0)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM cohort_calls WHERE attempt_id IS NOT NULL').fetchone()[0],0)


class PilotRunnerTests(PilotCase):
    def run_fixture(self, side_effect=None):
        from fleet_witness import controlled_pilot
        client=self.client()
        with patch.object(p,'_post',side_effect=side_effect,return_value=self.reply()) as post:
            report=controlled_pilot.collect(client,self.root/'output')
        return report,post.call_count

    def test_full_cohort_has_atomic_effects_revocation_duplicate_and_live_labels(self):
        report,count=self.run_fixture()
        self.assertEqual(count,160);self.assertEqual(report['summary']['completed'],160)
        self.assertEqual(report['summary']['complete_pairs'],80)
        self.assertEqual(report['summary']['bad_approvals'],80)
        self.assertEqual(report['summary']['effects'],60)
        self.assertEqual(report['summary']['authorization_denials'],100)
        self.assertEqual(report['summary']['duplicate_noops'],20)
        self.assertEqual(report['summary']['contrast']['difference'],0)
        self.assertIsNotNone(report['summary']['contrast']['interval_95'])
        for call in report['calls']:
            event=next(e for e in call['events'] if e['kind']=='decision_recorded')
            self.assertEqual(event['actor'],'live-supervisor')
            self.assertEqual(call['outcome']['proposal']['recommendation'],call['decision']['recommendation'])
        self.assertNotIn('synthetic-pilot-secret',json.dumps(report))
        from fleet_witness import controlled_pilot
        with patch.object(p,'_post') as post:
            with self.assertRaises((ValueError,p.ProviderError,FileExistsError)):controlled_pilot.collect(self.client(),self.root/'other')
            post.assert_not_called()

    def test_invalid_call_and_unstarted_denominators_no_invented_denial_or_interval(self):
        report,count=self.run_fixture(lambda *a,**kw:self.reply('not json'))
        self.assertEqual(count,1)
        self.assertEqual(report['summary']['invalid_output'],1)
        self.assertEqual(report['summary']['unstarted'],159)
        self.assertEqual(report['summary']['valid_decisions'],0)
        self.assertIsNone(report['summary']['contrast']['interval_95'])
        self.assertIsNone(report['calls'][0]['decision'])
        self.assertIsNone(report['calls'][0]['evaluation'])

    def test_transport_failure_retains_hold_and_nullable_outcome(self):
        report,count=self.run_fixture(p.TransportFailure('synthetic-timeout'))
        self.assertEqual(count,1);self.assertEqual(report['summary']['provider_failed'],1)
        self.assertEqual(report['summary']['unstarted'],159)
        self.assertGreater(report['summary']['held_usd'],0)
        self.assertEqual(report['summary']['effects'],0)

    def test_crash_after_settlement_preserves_mapping_for_read_only_export(self):
        from fleet_witness import controlled_pilot,pilot_store
        original=pilot_store.Store.outcome
        def crash(*args,**kwargs):raise KeyboardInterrupt('simulated process loss')
        with patch.object(pilot_store.Store,'outcome',side_effect=crash),patch.object(p,'_post',return_value=self.reply()) as post:
            with self.assertRaises(KeyboardInterrupt):controlled_pilot.collect(self.client(),self.root/'output')
            self.assertEqual(post.call_count,1)
        with patch.object(p,'_post',side_effect=AssertionError('export dispatched')):
            report=pilot_store.export_report(self.root/'output/pilot.sqlite3',self.ledger.path)
        self.assertEqual(report['summary']['dispatched'],1)
        self.assertEqual(report['summary']['interrupted'],1)
        self.assertEqual(report['summary']['unstarted'],159)
        self.assertIsNotNone(report['calls'][0]['ledger_attempt']['id'])
        self.assertIsNone(report['calls'][0]['decision'])

    def test_local_failure_after_effect_preserves_committed_effect(self):
        from fleet_witness.controller import Controller
        original=Controller.execute
        def committed_then_crash(controller,*args,**kwargs):
            value=original(controller,*args,**kwargs)
            if value['effect_occurred']:raise RuntimeError('synthetic failure after commit')
            return value
        with patch.object(Controller,'execute',committed_then_crash):report,count=self.run_fixture()
        self.assertGreater(count,0);self.assertLess(count,160)
        self.assertEqual(report['summary']['effects'],1)
        self.assertEqual(report['summary']['interrupted'],1)
        self.assertIsNone(report['summary']['contrast']['interval_95'])

    def test_export_validator_rejects_count_and_pair_tampering_html_is_inert(self):
        from fleet_witness import pilot_store
        hostile='{"recommendation":"approve","reason":"</pre><script>alert(1)</script>"}'
        report,count=self.run_fixture(lambda *a,**kw:self.reply(hostile))
        page=pilot_store.html_report(report)
        self.assertNotIn('<script>',page);self.assertIn('&lt;script&gt;',page)
        altered=copy.deepcopy(report);altered['summary']['effects']+=1
        with self.assertRaises(ValueError):pilot_store.validate_report(altered)
        altered=copy.deepcopy(report);altered['calls'][0]['supervisor_input']['facts']['reviewer_statement']='changed'
        with self.assertRaises(ValueError):pilot_store.validate_report(altered)

    def test_live_switch_and_calibration_packet_required_before_dispatch(self):
        from fleet_witness import controlled_pilot
        with patch.object(p,'_post') as post,patch.object(secure,'read_key',side_effect=AssertionError('key touched')):
            with self.assertRaises(ValueError):controlled_pilot.run_pilot(None,None,self.root/'output')
            with self.assertRaises((ValueError,TypeError)):controlled_pilot.validate_calibration({},self.record)
        post.assert_not_called()

    def test_calibration_acceptance_is_source_bound_reconciled_and_behavior_independent(self):
        from fleet_witness import controlled_pilot
        import hashlib
        auth=copy.deepcopy(self.record)
        auth.update(schema_version='controlled-openrouter-v1',purpose='calibration',request_limit=1)
        del auth['study']
        result={'run_id':auth['run_id'],'outcome':{'status':'succeeded','provider_attempts':1,'response_contract':'supervisor-v1',
            'proposal':{'recommendation':'approve','reason':'Calibration eligibility must not select deny.'},
            'attempts':[{'provider_request_id':'gen-cal','provider_reported_cost_usd':'0.01','input_tokens':10,'output_tokens':20}]}}
        raw=canonical_json(result)
        packet={'schema_version':'calibration-acceptance-v1','applies_to_source_sha256':self.record['source_sha256'],
            'applicability':'Transport profile is unchanged and runner extension reviewed.','reviewed_by':'synthetic reviewer',
            'calibration_authorization':auth,'result_raw':raw,
            'reconciliation':{'result_sha256':hashlib.sha256(raw.encode()).hexdigest(),'accepted':True,'read_only':True,
                'checks':{'matched':True},'usage_delta':'0.01',
                'generation':{'id':'gen-cal','model':design.MODEL+'-20260929','provider_name':'Azure',
                    'total_cost':'0.01','native_tokens_prompt':10,'native_tokens_completion':20}}}
        rec=copy.deepcopy(self.record);rec['study']['calibration_evidence_sha256']=design.digest(packet)
        self.assertTrue(controlled_pilot.validate_calibration(packet,rec))
        for field,value in [('usage_delta','0.02'),('accepted',False)]:
            broken=copy.deepcopy(packet);broken['reconciliation'][field]=value
            rec['study']['calibration_evidence_sha256']=design.digest(broken)
            with self.assertRaises(ValueError):controlled_pilot.validate_calibration(broken,rec)
        broken=copy.deepcopy(packet);broken['applies_to_source_sha256']='b'*64
        rec['study']['calibration_evidence_sha256']=design.digest(broken)
        with self.assertRaises(ValueError):controlled_pilot.validate_calibration(broken,rec)

    def test_crash_after_reserve_before_dispatch_leaves_link_and_hold(self):
        from fleet_witness import controlled_pilot,pilot_store
        with patch.object(self.ledger,'dispatch',side_effect=KeyboardInterrupt('before network')),patch.object(p,'_post') as post:
            with self.assertRaises(KeyboardInterrupt):controlled_pilot.collect(self.client(),self.root/'output')
            post.assert_not_called()
        report=pilot_store.export_report(self.root/'output/pilot.sqlite3',self.ledger.path)
        self.assertEqual(report['summary']['dispatched'],0)
        self.assertEqual(report['summary']['interrupted'],1)
        self.assertGreater(report['summary']['held_usd'],0)
        self.assertEqual(report['calls'][0]['ledger_attempt']['status'],'reserved')

    def test_whole_cohort_must_fit_remaining_provider_allowance_before_key_access(self):
        previous=p.Ledger('openrouter',38,50,self.ledger.path,run_id='prior')
        identity=previous.reserve(38);previous.dispatch(identity);previous.settle(identity,38)
        self.record['pricing'].update(input_per_million='2.75',output_per_million='11')
        with patch.object(secure,'read_key',side_effect=AssertionError('key touched')),patch.object(p,'_post') as post:
            client=self.client()
            with self.assertRaises(p.ProviderError):self.claim(client)
            post.assert_not_called()

    def acceptance_packet(self,record):
        import hashlib
        auth=copy.deepcopy(record);auth.update(schema_version='controlled-openrouter-v1',purpose='calibration',request_limit=1);del auth['study']
        raw=canonical_json({'run_id':auth['run_id'],'outcome':{'status':'succeeded','provider_attempts':1,'response_contract':'supervisor-v1',
            'attempts':[{'provider_request_id':'gen-cal','provider_reported_cost_usd':'0.01','input_tokens':10,'output_tokens':20}]}})
        return {'schema_version':'calibration-acceptance-v1','applies_to_source_sha256':record['source_sha256'],
            'applicability':'Same reviewed transport and model with new runner checks.','reviewed_by':'offline reviewer',
            'calibration_authorization':auth,'result_raw':raw,'reconciliation':{'result_sha256':hashlib.sha256(raw.encode()).hexdigest(),
                'accepted':True,'read_only':True,'checks':{'matched':True},'usage_delta':'0.01',
                'generation':{'id':'gen-cal','model':design.MODEL+'-20260929','provider_name':'Azure','total_cost':'0.01',
                              'native_tokens_prompt':10,'native_tokens_completion':20}}}

    def test_authorization_replacement_cannot_change_the_calibration_qualified_client(self):
        from fleet_witness import controlled_pilot
        from fleet_witness.swarm import operator
        packet=self.acceptance_packet(self.record)
        self.record['study']['calibration_evidence_sha256']=design.digest(packet)
        authpath=self.root/'authorization.json';authpath.write_text(canonical_json(self.record));authpath.chmod(0o600)
        calpath=self.root/'calibration.json';calpath.write_text(canonical_json(packet));calpath.chmod(0o600)
        second=copy.deepcopy(self.record);second['study']['calibration_evidence_sha256']='b'*64
        key2=self.root/'second-key';key2.write_text('second-synthetic-secret');key2.chmod(0o600)
        second['openrouter']['transport']['key_file']=str(key2)
        original=operator.load_authorizations;loads=[];used=[]
        def replace_after_read(path):
            value=original(path);loads.append(1);authpath.write_text(canonical_json(second));return value
        def capture(url,key,*args,**kwargs):used.append(key);return self.reply('invalid')
        with patch.object(operator,'require_committed_source'),patch.object(operator,'load_authorizations',side_effect=replace_after_read),patch.object(p,'_post',side_effect=capture):
            report=controlled_pilot.run_pilot(authpath,calpath,self.root/'output',live=True)
        self.assertEqual(len(loads),1)
        self.assertEqual(used,['synthetic-pilot-secret'])
        self.assertEqual(report['summary']['invalid_output'],1)

    def test_report_rejects_ledger_effect_and_pair_identity_corruption(self):
        from fleet_witness import pilot_store
        report,_=self.run_fixture()
        variants=[]
        item=copy.deepcopy(report);item['calls'][0]['ledger_attempt']=None;variants.append(('missing ledger',item))
        item=copy.deepcopy(report);item['calls'][0]['ledger_attempt']['status']='unresolved';variants.append(('bad status',item))
        item=copy.deepcopy(report);item['calls'][0]['ledger_attempt']['receipt']['proposal']['recommendation']='deny';variants.append(('different ledger proposal',item))
        item=copy.deepcopy(report);item['calls'][0]['outcome']['attempts'][0]['attempt_id']='wrong';variants.append(('wrong provider attempt',item))
        item=copy.deepcopy(report);item['calls'][0]['outcome']['cost_usd']=.5;variants.append(('different accounting',item))
        item=copy.deepcopy(report);c=next(c for c in item['calls'] if c['releases']);extra=copy.deepcopy(c['releases'][0]);extra['attempt_id']='orphan';extra['id']='extra';c['releases'].append(extra);variants.append(('extra release',item))
        item=copy.deepcopy(report);c=next(c for c in item['calls'] if c['releases']);c['releases'][0]['artifact_digest']='wrong';variants.append(('wrong effect artifact',item))
        item=copy.deepcopy(report);c=next(c for c in item['calls'] if c['attempts']);c['attempts'][0]['decision_id']='wrong';variants.append(('wrong decision identity',item))
        item=copy.deepcopy(report);c=next(c for c in item['calls'] if c['releases']);e=next(e for e in c['events'] if e['kind']=='release_committed');e['actor']='live-supervisor';variants.append(('wrong effect actor',item))
        item=copy.deepcopy(report);first,second=item['calls'][:2];second['presentation']=first['presentation'];second['supervisor_input']['instruction']=first['supervisor_input']['instruction'];second['decision']['supervisor_input']=copy.deepcopy(second['supervisor_input']);item['plan']['schedule'][1]['presentation']=first['presentation'];item['plan_sha256']=design.digest(item['plan']);variants.append(('duplicate pair presentation',item))
        item=copy.deepcopy(report);item['source_sha256']='0'*64;variants.append(('wrong source provenance',item))
        for label,item in variants:
            item['summary']=pilot_store.summarize(item['calls'],item['stop_reason'])
            with self.subTest(label=label):
                with self.assertRaises(ValueError):pilot_store.validate_report(item)

    def test_export_rejects_persisted_outcome_attempt_mismatch(self):
        from fleet_witness import pilot_store
        report,_=self.run_fixture(lambda *a,**kw:self.reply('invalid'))
        with closing(sqlite3.connect(self.root/'output/pilot.sqlite3')) as db,db:
            row=db.execute('SELECT trial_id,outcome FROM pilot_calls WHERE outcome IS NOT NULL').fetchone()
            outcome=json.loads(row[1]);outcome['attempts'][0]['attempt_id']='wrong'
            db.execute('UPDATE pilot_calls SET outcome=? WHERE trial_id=?',(canonical_json(outcome),row[0]))
        with self.assertRaises(ValueError):pilot_store.export_report(self.root/'output/pilot.sqlite3',self.ledger.path)

    def test_canonical_provider_attempts_cannot_be_reused_between_scheduled_calls(self):
        from fleet_witness import pilot_store
        report,_=self.run_fixture()
        first,second=report['calls'][:2]
        identity=first['ledger_attempt']['id']
        second['ledger_attempt']['id']=identity
        second['ledger_attempt']['receipt']['attempt_id']=identity
        second['outcome']['attempts'][0]['attempt_id']=identity
        with self.assertRaises(ValueError):pilot_store.validate_report(report)

    def test_reconciled_failed_call_preserves_receipt_and_requires_matching_audit(self):
        from fleet_witness import pilot_store
        from fleet_witness.swarm.ledger import dollars
        import hashlib
        def invalid(*args,**kwargs):
            value=json.loads(self.reply());value['choices'][0]['message']['reasoning']='unexpected text';return json.dumps(value).encode()
        report,_=self.run_fixture(invalid)
        attempt=report['calls'][0]['ledger_attempt'];original=copy.deepcopy(attempt['receipt'])
        record={'schema_version':'operator-charge-reconciliation-v1','request_id':attempt['id'],'run_id':self.record['run_id'],
            'prior_status':'unresolved','prior_held_units':int(attempt['held']),'settled_units':30000,
            'provider_reported_cost_usd':'0.00003','response_sha256':attempt['response_sha256'],
            'receipt_sha256':design.digest(original),'account_evidence_sha256':'a'*64,'generation_evidence_sha256':'b'*64}
        with closing(sqlite3.connect(self.ledger.path)) as db,db:
            db.execute("UPDATE requests SET status='reconciled_invalid_output',held='0',settled=30000 WHERE id=?",(attempt['id'],))
        with self.assertRaises(ValueError):pilot_store.export_report(self.root/'output/pilot.sqlite3',self.ledger.path)
        with closing(sqlite3.connect(self.ledger.path)) as db,db:
            db.execute('INSERT INTO audit(request_id,kind,data) VALUES(?,?,?)',(attempt['id'],'operator_charge_reconciled',canonical_json(record)))
        recovered=pilot_store.export_report(self.root/'output/pilot.sqlite3',self.ledger.path)
        self.assertEqual(recovered['summary']['provider_failed'],1)
        self.assertEqual(recovered['summary']['settled_usd'],.00003)
        self.assertEqual(recovered['summary']['held_usd'],0)
        self.assertEqual(recovered['calls'][0]['ledger_attempt']['receipt'],original)
        self.assertIsNone(recovered['calls'][0]['decision'])
        corrupted=copy.deepcopy(recovered);corrupted['calls'][0]['ledger_attempt']['reconciliation']['receipt_sha256']='c'*64
        with self.assertRaises(ValueError):pilot_store.validate_report(corrupted)
