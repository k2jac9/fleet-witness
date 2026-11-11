"""Research entrypoints exercise real authorization/accounting with offline transport."""
from contextlib import closing, contextmanager, redirect_stderr, redirect_stdout
from concurrent.futures import ThreadPoolExecutor
import hashlib
import io
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

from fleet_witness.swarm import operator, providers as p
from scripts import judgement_experiment as experiment, label_check
from test_swarm_provider import SyntheticSourceTestCase, authorization


def fixture_authorizations(root, models, *, cap='1', request_limit=200):
    ledger = p.Ledger('openrouter', cap, cap, root / 'ledger.sqlite3', run_id='synthetic-research')
    base = authorization(ledger)
    base.update(run_cap_usd=cap, provider_cap_usd=cap, request_limit=request_limit,
                max_input_bytes=32768, max_output_tokens=1000)
    records = [{**base, 'authorization_id': f'synthetic-research-{index}', 'model': model}
               for index, model in enumerate(models)]
    path = root / 'authorization.json'
    path.write_text(json.dumps({'schema_version': 'swarm-authorizations-v1', 'authorizations': records}))
    path.chmod(0o600)
    return ledger, path


def response(text='{"vote":"approve","sign":true,"reason":"synthetic"}', *, finish='stop', usage=True):
    payload = {'id': 'synthetic-research-response',
               'choices': [{'message': {'role': 'assistant', 'content': text}, 'finish_reason': finish}]}
    if usage:
        payload['usage'] = {'prompt_tokens': 2, 'completion_tokens': 3, 'total_tokens': 5, 'cost': .000005}
    return payload


class OfflineTransport:
    """Only external I/O is replaced; ledger, clients, scripts and files remain real."""
    def __init__(self, replies=None, *, error=None):
        self.replies = list(replies or [response()])
        self.error = error
        self.requests = []
        self.timeouts = []
        self.active = self.max_active = 0
        self.lock = threading.Lock()

    def post(self, url, key, body, timeout, **kwargs):
        with self.lock:
            index = len(self.requests)
            self.requests.append(body)
            self.timeouts.append(timeout)
            self.active += 1
            self.max_active = max(self.max_active, self.active)
        try:
            if self.error is not None:
                raise self.error
            # Allow a concurrent dispatch to become observable without any network I/O.
            time.sleep(.002)
            return json.dumps(self.replies[min(index, len(self.replies) - 1)]).encode()
        finally:
            with self.lock:
                self.active -= 1

    def legacy(self, request, timeout):
        return io.BytesIO(self.post(request.full_url, 'synthetic-research-key',
                                  json.loads(request.data), timeout))


@contextmanager
def offline(transport):
    with patch.dict(os.environ, {'OPENROUTER_API_KEY': 'synthetic-research-key'}), \
            patch.object(p, '_post', transport.post), patch('urllib.request.urlopen', transport.legacy), \
            patch.object(operator, 'require_committed_source'):
        # Dirty source is accepted only in this synthetic, network-isolated test fixture.
        # The real source identity, record validation and durable ledger still run.
        yield


def invoke(module, arguments):
    with patch('sys.argv', [str(module.__file__), *map(str, arguments)]), \
            redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
        try:
            result = module.main()
        except SystemExit as error:
            return error.code
        except (p.ProviderError, ValueError, OSError):
            return 1
    return result if isinstance(result, int) else 0


def experiment_args(root, path, *, label='fixture', model='fixture-model'):
    return ['--model', model, '--label', label, '--shares', '0', '--agents', '7', '--cases', '1',
            '--conditions', 'hidden-cell', '--out', root / 'runs', '--authorization', path, '--live']


def assert_cancelled_attempt(test, ledger, summary, receipt_path, cancellation):
    """Check an actual dispatched request across its authoritative and derived records."""
    test.assertEqual(ledger.calls, 1)
    test.assertEqual(summary['provider_attempts'], 1)
    test.assertEqual(summary['cost_usd'], 0)
    test.assertGreater(summary['held_usd'], 0)
    test.assertEqual(summary['held_usd'], ledger.run_reserved)
    private = [json.loads(line) for line in receipt_path.read_text().splitlines()]
    test.assertEqual(len(private), 1)
    test.assertEqual(private[0]['status'], 'unresolved')
    test.assertEqual(len(private[0]['attempts']), 1)
    attempt = private[0]['attempts'][0]
    with closing(sqlite3.connect(ledger.path)) as connection:
        rows = connection.execute('SELECT id,request_json,receipt_json,status,held,dispatched FROM requests').fetchall()
        test.assertEqual(len(rows), 1)
        identity, request, raw_receipt, status, held, dispatched = rows[0]
        test.assertIsNotNone(dispatched)
        test.assertIsNotNone(raw_receipt, 'cancellation must persist the active attempt receipt')
        durable = json.loads(raw_receipt)
        test.assertEqual(connection.execute("SELECT COUNT(*) FROM audit WHERE kind='dispatched'").fetchone()[0], 1)
        test.assertEqual(connection.execute("SELECT COUNT(*) FROM audit WHERE kind='unresolved'").fetchone()[0], 1)
    test.assertEqual(status, 'unresolved')
    test.assertEqual(attempt['attempt_id'], identity)
    test.assertEqual(attempt['request_sha256'], hashlib.sha256(request.encode()).hexdigest())
    test.assertEqual(attempt['held_usd'], int(held) / 1_000_000_000)
    test.assertEqual(attempt['provider_attempts'], 1)
    test.assertEqual(attempt['status'], 'unresolved')
    test.assertEqual(attempt, durable)
    test.assertEqual(cancellation.attempts, [durable])
    test.assertEqual(cancellation.provider_attempts, 1)
    test.assertEqual(cancellation.held_usd, summary['held_usd'])
    return attempt


class ResearchRequestsTest(SyntheticSourceTestCase):
    def test_label_cancellation_preserves_actual_attempt_and_original_exception(self):
        for interruption in (KeyboardInterrupt(), SystemExit(23)):
            with self.subTest(interruption=type(interruption).__name__), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                ledger, path = fixture_authorizations(root, ['fixture-model'])
                output = root / 'labels.json'
                transport = OfflineTransport(error=interruption)
                arguments = ['label_check.py', '--model', 'fixture-model', '--out', str(output),
                             '--authorization', str(path), '--live']
                with offline(transport), patch('sys.argv', arguments), redirect_stdout(io.StringIO()):
                    with self.assertRaises(type(interruption)) as caught:
                        label_check.main()
                self.assertIs(caught.exception, interruption)
                result = json.loads(output.read_text())
                self.assertEqual(result['status'], 'failed')
                self.assertEqual(result['completed_cases'], 0)
                attempt = assert_cancelled_attempt(self, ledger, result, root / result['private_receipts'], interruption)
                self.assertEqual(result['calls'][0]['attempts'], [attempt])
                self.assertEqual(result['rows'][0]['status'], 'unresolved')
                self.assertTrue(all(row['status'] == 'not_started' for row in result['rows'][1:]))
                self.assertEqual(len(transport.requests), 1)

    def test_cancellation_at_ledger_transition_keeps_committed_attempt_accounting(self):
        for transition in ('dispatch', 'settle'):
            with self.subTest(transition=transition), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                ledger, path = fixture_authorizations(root, ['fixture-model'])
                output = root / 'labels.json'
                interruption = KeyboardInterrupt()
                original = getattr(p.Ledger, transition)

                def interrupt_after_commit(instance, *args, **kwargs):
                    original(instance, *args, **kwargs)
                    raise interruption

                transport = OfflineTransport([response('{"label":"safe","problem":"none"}')])
                arguments = ['label_check.py', '--model', 'fixture-model', '--out', str(output),
                             '--authorization', str(path), '--live']
                with offline(transport), patch('sys.argv', arguments), redirect_stdout(io.StringIO()), \
                        patch.object(p.Ledger, transition, interrupt_after_commit):
                    with self.assertRaises(KeyboardInterrupt) as caught:
                        label_check.main()
                self.assertIs(caught.exception, interruption)
                result = json.loads(output.read_text())
                self.assertEqual(result['provider_attempts'], 1)
                self.assertEqual(result['provider_attempts'], ledger.calls)
                self.assertEqual(result['cost_usd'], ledger.run_spent)
                self.assertEqual(result['held_usd'], ledger.run_reserved)
                self.assertEqual(result['status'], 'failed')
                self.assertEqual(result['completed_cases'], 0)
                with closing(sqlite3.connect(ledger.path)) as connection:
                    durable = json.loads(connection.execute('SELECT receipt_json FROM requests').fetchone()[0])
                receipt = json.loads((root / result['private_receipts']).read_text().splitlines()[0])
                self.assertEqual(len(receipt['attempts']), 1)
                retained = receipt['attempts'][0]
                for field in ('attempt_id', 'request_sha256', 'response_sha256', 'status', 'provider_attempts',
                              'reserved_usd', 'cost_usd', 'held_usd'):
                    self.assertEqual(retained[field], durable[field])
                self.assertEqual(result['calls'][0]['attempts'], [retained])
                self.assertEqual(interruption.attempts, [durable])
                if transition == 'settle':
                    self.assertEqual(durable['status'], 'succeeded')
                    self.assertEqual(result['cost_usd'], .000005)
                    self.assertEqual(result['held_usd'], 0)
                    self.assertEqual(len(transport.requests), 1)
                else:
                    self.assertEqual(durable['status'], 'unresolved')
                    self.assertGreater(result['held_usd'], 0)
                    self.assertEqual(transport.requests, [])

    def test_judgement_cancellation_retains_manifest_and_stops_the_next_request(self):
        for interruption in (KeyboardInterrupt(), SystemExit(23)):
            with self.subTest(interruption=type(interruption).__name__), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                ledger, path = fixture_authorizations(root, ['fixture-model'])
                transport = OfflineTransport(error=interruption)
                arguments = ['judgement_experiment.py', *map(str, experiment_args(root, path))]
                with offline(transport), patch('sys.argv', arguments), redirect_stdout(io.StringIO()):
                    with self.assertRaises(type(interruption)) as caught:
                        experiment.main()
                self.assertIs(caught.exception, interruption)
                out = root / 'runs/fixture/f00'
                self.assertTrue((out / 'manifest.json').is_file(), 'interruption must retain an incomplete manifest')
                result = json.loads((out / 'manifest.json').read_text())
                self.assertTrue(result['incomplete'])
                attempt = assert_cancelled_attempt(self, ledger, result, out / 'private/requests.jsonl', interruption)
                self.assertEqual(result['interruption']['attempts'], [attempt])
                self.assertEqual(result['interruption']['type'], type(interruption).__name__)
                events = [json.loads(line) for line in (out / 'events.jsonl').read_text().splitlines()]
                self.assertEqual(len(events), 1)
                self.assertEqual(events[0]['attempts'], [attempt])
                self.assertFalse(events[0]['ok'])
                self.assertEqual(len(transport.requests), 1)
                self.assertFalse((out / 'decisions.json').exists())

    def test_transport_cancellation_prevents_late_dispatch_after_connect(self):
        for interruption in (KeyboardInterrupt(), SystemExit(23)):
            with self.subTest(interruption=type(interruption).__name__):
                release, stopped = threading.Event(), threading.Event()
                sent = []

                class Connection:
                    def __init__(self, *args, **kwargs): self.sock = self
                    def connect(self): release.wait(2)
                    def settimeout(self, value): pass
                    def request(self, *args, **kwargs): sent.append('request')
                    def getresponse(self): raise TimeoutError('synthetic response is unavailable')
                    def close(self): stopped.set()

                with patch.object(p.http.client, 'HTTPSConnection', Connection), \
                        patch.object(p.queue.Queue, 'get', side_effect=interruption):
                    with self.assertRaises(type(interruption)) as caught:
                        p._post(p.OPENROUTER_URL, 'synthetic-research-key', {}, 5)
                    self.assertIs(caught.exception, interruption)
                    release.set()
                    self.assertTrue(stopped.wait(2))
                self.assertEqual(sent, [], 'a cancelled caller must not leave a connecting worker able to dispatch')

    def test_mismatched_purposes_refuse_the_whole_job_before_any_spend(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            ledger, path = fixture_authorizations(root, ['fixture-model', 'second-model'])
            bundle = json.loads(path.read_text())
            bundle['authorizations'][1]['purpose'] = 'confirmatory'
            bundle['authorizations'][1]['qualification']['calibration_accepted'] = True
            path.write_text(json.dumps(bundle))
            transport = OfflineTransport()
            with offline(transport):
                code = invoke(experiment, experiment_args(root, path) +
                               ['--shared-models', 'fixture-model', 'second-model'])
            self.assertNotEqual(code, 0)
            self.assertEqual(transport.requests, [])
            self.assertEqual(ledger.calls, 0)
            self.assertEqual(ledger.run_spent, 0)
            self.assertFalse((root / 'runs').exists())

    def test_experiment_client_refuses_absent_authorization_before_io(self):
        transport = OfflineTransport()
        with offline(transport):
            with self.assertRaises((p.ProviderError, ValueError)):
                experiment.OpenRouterClient('fixture-model', 1)
        self.assertEqual(transport.requests, [])

    def test_authorized_judgement_run_serializes_and_retains_real_receipts(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            ledger, path = fixture_authorizations(root, ['fixture-model'])
            transport = OfflineTransport()
            with offline(transport):
                code = invoke(experiment, experiment_args(root, path))
            self.assertEqual(code, 0, 'a qualified synthetic run should use the existing paid boundary')
            manifest = json.loads((root / 'runs/fixture/f00/manifest.json').read_text())
            self.assertEqual(manifest['provider_attempts'], 14)
            self.assertEqual(ledger.calls, 14)
            self.assertEqual(transport.max_active, 1)
            self.assertTrue(all(0 < timeout <= 30 for timeout in transport.timeouts))
            self.assertAlmostEqual(manifest['cost_usd'], .000070)
            self.assertAlmostEqual(ledger.run_spent, .000070)
            self.assertEqual(ledger.run_reserved, 0)
            receipts = [json.loads(line) for line in
                        (root / 'runs/fixture/f00/private/requests.jsonl').read_text().splitlines()]
            self.assertEqual(sum(len(row['attempts']) for row in receipts), 14)
            self.assertTrue(manifest['gated_workflow'])

    def test_missing_usage_halts_later_shares_and_preserves_final_attempt(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            ledger, path = fixture_authorizations(root, ['fixture-model'])
            transport = OfflineTransport([response(usage=False)])
            arguments = experiment_args(root, path)
            arguments[arguments.index('--shares') + 1:arguments.index('--agents')] = ['0', '0.2']
            with offline(transport):
                code = invoke(experiment, arguments)
            self.assertNotEqual(code, 0)
            manifest_path = root / 'runs/fixture/f00/manifest.json'
            self.assertTrue(manifest_path.exists(), 'the failed run must retain its manifest')
            manifest = json.loads(manifest_path.read_text())
            self.assertTrue(manifest['incomplete'])
            self.assertEqual(manifest['provider_attempts'], 1)
            self.assertEqual(len(transport.requests), 1)
            self.assertEqual(ledger.calls, 1)
            self.assertGreater(manifest['held_usd'], 0)
            self.assertEqual(manifest['held_usd'], ledger.run_reserved)
            self.assertFalse((root / 'runs/fixture/f20').exists())
            receipts = [json.loads(line) for line in
                        (root / 'runs/fixture/f00/private/requests.jsonl').read_text().splitlines()]
            attempted = [row for row in receipts if row['attempts']]
            self.assertEqual(len(attempted), 1)
            self.assertEqual(attempted[0]['attempts'][0]['provider_attempts'], 1)
            self.assertEqual(attempted[0]['status'], 'unresolved')

    def test_small_budget_denies_before_any_provider_dispatch(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            ledger, path = fixture_authorizations(root, ['fixture-model'], cap='0.000001')
            transport = OfflineTransport()
            with offline(transport):
                code = invoke(experiment, experiment_args(root, path))
            self.assertNotEqual(code, 0)
            manifest_path = root / 'runs/fixture/f00/manifest.json'
            self.assertTrue(manifest_path.exists(), 'admission failure must be reported')
            self.assertTrue(json.loads(manifest_path.read_text())['incomplete'])
            self.assertEqual(transport.requests, [])
            self.assertEqual(ledger.calls, 0)

    def test_restarted_model_run_consumes_same_request_allowance(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            ledger, path = fixture_authorizations(root, ['fixture-model', 'second-model'], request_limit=14)
            transport = OfflineTransport()
            shared = ['--shared-models', 'fixture-model', 'second-model']
            with offline(transport):
                first = invoke(experiment, experiment_args(root, path) + shared)
                second = invoke(experiment, experiment_args(root, path, label='second', model='second-model') + shared)
            self.assertEqual(first, 0)
            self.assertNotEqual(second, 0)
            self.assertEqual(ledger.calls, 14)
            self.assertEqual(len(transport.requests), 14)
            self.assertEqual({body['model'] for body in transport.requests}, {'fixture-model'})
            manifest = json.loads((root / 'runs/second/f00/manifest.json').read_text())
            self.assertTrue(manifest['incomplete'])
            self.assertEqual(manifest['provider_attempts'], 0)

    def test_competing_authorized_clients_cannot_dispatch_a_second_inflight_request(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            ledger, path = fixture_authorizations(root, ['fixture-model', 'second-model'])
            transport = OfflineTransport()
            entered, release = threading.Event(), threading.Event()

            def blocked(*args, **kwargs):
                entered.set()
                if not release.wait(5):
                    raise TimeoutError('test failed to release the offline transport')
                return transport.post(*args, **kwargs)

            with offline(transport):
                first = experiment.OpenRouterClient('fixture-model', authorization=path, live=True,
                                                    shared_models=['second-model'])
                second = experiment.OpenRouterClient('second-model', authorization=path, live=True,
                                                     shared_models=['fixture-model'])
                with patch.object(p, '_post', blocked), ThreadPoolExecutor(2) as pool:
                    future = pool.submit(first.complete, 'synthetic system', 'synthetic input')
                    try:
                        self.assertTrue(entered.wait(5))
                        with self.assertRaises(p.BudgetExceeded):
                            second.complete('synthetic system', 'competing input')
                        self.assertEqual(ledger.calls, 1)
                        self.assertGreater(ledger.run_reserved, 0)
                    finally:
                        release.set()
                    result = future.result(5)
            self.assertEqual(result['provider_attempts'], 1)
            self.assertEqual(len(transport.requests), 1)
            self.assertEqual(ledger.run_reserved, 0)
            self.assertAlmostEqual(ledger.run_spent, .000005)

    def test_restarted_model_cannot_spend_the_first_models_settled_budget_again(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            ledger, path = fixture_authorizations(root, ['fixture-model', 'second-model'], cap='0.002')
            charged = response()
            charged['usage']['cost'] = .0015
            transport = OfflineTransport([charged])
            with offline(transport):
                first = experiment.OpenRouterClient('fixture-model', authorization=path, live=True,
                                                    shared_models=['second-model'])
                first.complete('s', 'u')
                restarted = experiment.OpenRouterClient('second-model', authorization=path, live=True,
                                                        shared_models=['fixture-model'])
                with self.assertRaises(p.BudgetExceeded):
                    restarted.complete('s', 'u')
            self.assertEqual(ledger.calls, 1)
            self.assertEqual(len(transport.requests), 1)
            self.assertEqual(ledger.run_spent, .0015)
            self.assertEqual(ledger.run_reserved, 0)

    def test_mismatched_shared_envelope_and_over_15_dollar_run_refuse_before_dispatch(self):
        for change in ('run_id', 'source', 'cap'):
            with self.subTest(change=change), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                ledger, path = fixture_authorizations(root, ['fixture-model', 'second-model'],
                                                      cap='16' if change == 'cap' else '1')
                bundle = json.loads(path.read_text())
                if change == 'run_id':
                    bundle['authorizations'][1]['run_id'] = 'a-second-spending-allowance'
                elif change == 'source':
                    bundle['authorizations'][1]['source_commit'] = '0' * 40
                path.write_text(json.dumps(bundle))
                transport = OfflineTransport()
                with offline(transport):
                    code = invoke(experiment, experiment_args(root, path) +
                                   ['--shared-models', 'fixture-model', 'second-model'])
                self.assertNotEqual(code, 0)
                self.assertEqual(transport.requests, [])
                self.assertEqual(ledger.calls, 0)
                self.assertFalse((root / 'runs').exists())

    def test_ambiguous_http_failure_retains_known_overrun_and_provider_identity(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            ledger, path = fixture_authorizations(root, ['fixture-model'])
            raw = json.dumps({'id': 'failed-provider-generation', 'error': {'message': 'synthetic failure'},
                              'usage': {'prompt_tokens': 2, 'completion_tokens': 3, 'cost': 1.5}}).encode()
            transport = OfflineTransport(error=p.TransportFailure('http_error', raw=raw, http_status=500))
            with offline(transport):
                code = invoke(experiment, experiment_args(root, path))
            self.assertNotEqual(code, 0)
            manifest = json.loads((root / 'runs/fixture/f00/manifest.json').read_text())
            self.assertEqual(manifest['provider_attempts'], 1)
            self.assertEqual(manifest['held_usd'], 1.5)
            self.assertEqual(ledger.run_reserved, 1.5)
            receipts = [json.loads(line) for line in
                        (root / 'runs/fixture/f00/private/requests.jsonl').read_text().splitlines()]
            attempt = next(row['attempts'][0] for row in receipts if row['attempts'])
            self.assertEqual(attempt['status'], 'overrun')
            self.assertEqual(attempt['http_status'], 500)
            self.assertEqual(attempt['provider_request_id'], 'failed-provider-generation')
            self.assertEqual(len(transport.requests), 1)

    def test_label_check_requires_authorization_before_credentials_or_dispatch(self):
        with tempfile.TemporaryDirectory() as temp:
            transport = OfflineTransport([response('{"label":"safe","problem":"none"}')])
            with offline(transport):
                code = invoke(label_check, ['--model', 'fixture-model', '--out', Path(temp) / 'labels.json'])
            self.assertNotEqual(code, 0)
            self.assertEqual(transport.requests, [])

    def test_label_check_invalid_output_is_failed_with_usage_receipt(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            ledger, path = fixture_authorizations(root, ['fixture-model'])
            transport = OfflineTransport([response('{"label":"maybe","problem":"unclear"}')])
            with offline(transport):
                code = invoke(label_check, ['--model', 'fixture-model', '--out', root / 'labels.json',
                                            '--authorization', path, '--live'])
            self.assertNotEqual(code, 0)
            self.assertTrue((root / 'labels.json').exists(), 'failed label collection must retain evidence')
            result = json.loads((root / 'labels.json').read_text())
            self.assertEqual(result['status'], 'failed')
            self.assertEqual(result['completed_cases'], 0)
            self.assertEqual(result['provider_attempts'], 1)
            self.assertAlmostEqual(result['cost_usd'], .000005)
            self.assertAlmostEqual(ledger.run_spent, .000005)
            self.assertIsNone(result['rows'][0]['agree'])
            self.assertEqual(len(transport.requests), 1)
            private = root / result['private_receipts']
            receipt = json.loads(private.read_text().splitlines()[0])
            self.assertEqual(receipt['status'], 'invalid_output')
            self.assertEqual(receipt['attempts'][0]['status'], 'succeeded')

    def test_label_check_missing_usage_keeps_partial_results_and_an_unresolved_hold(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            ledger, path = fixture_authorizations(root, ['fixture-model'])
            transport = OfflineTransport([response('{"label":"safe","problem":"none"}'),
                                          response('{"label":"safe","problem":"none"}', usage=False)])
            with offline(transport):
                code = invoke(label_check, ['--model', 'fixture-model', '--out', root / 'labels.json',
                                            '--authorization', path, '--live'])
            self.assertNotEqual(code, 0)
            result = json.loads((root / 'labels.json').read_text())
            self.assertEqual(result['status'], 'partial')
            self.assertEqual(result['completed_cases'], 1)
            self.assertEqual(result['provider_attempts'], 2)
            self.assertAlmostEqual(result['cost_usd'], .000005)
            self.assertEqual(result['held_usd'], ledger.run_reserved)
            self.assertGreater(result['held_usd'], 0)
            self.assertEqual(result['rows'][1]['status'], 'unresolved')
            self.assertIsNone(result['rows'][1]['agree'])
            self.assertTrue(all(row['status'] == 'not_started' for row in result['rows'][2:]))
            self.assertEqual(len(transport.requests), 2)

    def test_label_check_completes_only_after_all_48_serialized_labels(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            ledger, path = fixture_authorizations(root, ['fixture-model'])
            transport = OfflineTransport([response('{"label":"safe","problem":"none"}')])
            with offline(transport):
                code = invoke(label_check, ['--model', 'fixture-model', '--out', root / 'labels.json',
                                            '--authorization', path, '--live'])
            self.assertEqual(code, 0)
            result = json.loads((root / 'labels.json').read_text())
            self.assertEqual(result['status'], 'completed')
            self.assertEqual(result['completed_cases'], 48)
            self.assertEqual(result['provider_attempts'], 48)
            self.assertEqual(ledger.calls, 48)
            self.assertEqual(transport.max_active, 1)
            self.assertAlmostEqual(result['cost_usd'], .000240)

    def test_label_output_name_cannot_collide_with_its_receipt_directory(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _, path = fixture_authorizations(root, ['fixture-model'])
            output = root / 'labels.receipts'
            transport = OfflineTransport([response('{}')])
            with offline(transport):
                code = invoke(label_check, ['--model', 'fixture-model', '--out', output,
                                            '--authorization', path, '--live'])
            self.assertNotEqual(code, 0)
            self.assertTrue(output.is_file(), 'a retained failure result must not collide with its receipt directory')
            result = json.loads(output.read_text())
            self.assertEqual(result['status'], 'failed')
            self.assertTrue((root / result['private_receipts']).is_file())


if __name__ == '__main__':
    unittest.main()
