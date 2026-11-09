"""Provider security boundaries use synthetic credentials and transport only."""
from contextlib import closing
import inspect
import json
from pathlib import Path
import sqlite3
import tempfile
import time
import unittest
from unittest.mock import patch

from fleet_witness.swarm import providers as p


class SyntheticSourceTestCase(unittest.TestCase):
    """Git-free offline workers use a synthetic test identity, never paid authority."""
    def setUp(self):
        super().setUp()
        from fleet_witness.swarm import authorization as gate
        identity = p.source_identity()
        if identity['source_commit'] is None:
            identity = {**identity, 'source_commit': 'f' * 40}
            for module in (p, gate):
                substitute = patch.object(module, 'source_identity', return_value=identity)
                substitute.start()
                self.addCleanup(substitute.stop)


def authorization(ledger, *, provider='openrouter', purpose='calibration'):
    identity = p.source_identity()
    now = int(time.time())
    return {'schema_version': 'swarm-paid-v1', 'authorization_id': 'synthetic-test-only',
            'approved_by': 'offline-test-fixture', 'purpose': purpose,
            'issued_at': now - 1, 'expires_at': now + 300,
            'source_commit': identity['source_commit'], 'source_sha256': identity['source_sha256'],
            'provider': provider, 'model': 'fixture-model',
            'endpoint': p.OPENROUTER_URL if provider == 'openrouter' else p.ADAPTION_URL,
            'ledger_path': str(ledger.path), 'run_id': ledger.run_id,
            'run_cap_usd': '1', 'provider_cap_usd': '1', 'request_limit': 2,
            'max_input_bytes': 4096, 'max_output_tokens': 100, 'max_response_bytes': 8192,
            'timeout_s': 1,
            'pricing': {'unit': 'USD', 'input_per_million': '1', 'output_per_million': '1',
                        'verified_at': now - 10, 'evidence_sha256': '1' * 64,
                        'all_billable_tokens_included': True},
            'qualification': {'access_verified': True, 'retention_reviewed': True,
                              'transport_reviewed': True, 'calibration_accepted': purpose == 'confirmatory',
                              'evidence_sha256': '2' * 64}}


def reply(*, tokens=98, finish='stop', usage=True, cost=None):
    data = {'id': 'synthetic-id', 'choices': [{'message': {'role': 'assistant', 'content': '{"vote":"approve"}'},
                                            'finish_reason': finish}]}
    if usage:
        data['usage'] = {'prompt_tokens': 1, 'completion_tokens': tokens}
        if cost is not None:
            data['usage']['cost'] = cost
    return data


class ProviderBoundaryTest(SyntheticSourceTestCase):
    def ledger(self, root):
        return p.Ledger('openrouter', 1, 1, Path(root) / 'ledger.sqlite3')

    def client(self, ledger, record=None):
        self.assertIn('authorization', inspect.signature(p.ModelClient).parameters,
                      'paid client must require explicit verified operator authorization')
        return p.ModelClient('openrouter', 'fixture-model', ledger, max_output_tokens=100,
                             timeout=1, authorization=record or authorization(ledger))

    def test_absent_authorization_fails_before_credential_or_network_access(self):
        touched = []
        def forbidden(*args, **kwargs):
            touched.append('I/O')
            raise p.ProviderError('unexpected I/O')
        with tempfile.TemporaryDirectory() as tmp, patch.object(p, '_env_key', forbidden), patch('urllib.request.urlopen', forbidden):
            with self.assertRaises(p.ProviderError):
                p.ModelClient('openrouter', 'fixture-model', self.ledger(tmp))
            self.assertEqual(touched, [])

    def test_models_share_request_limit_across_restart(self):
        with tempfile.TemporaryDirectory() as tmp:
            ledger = self.ledger(tmp)
            first = authorization(ledger)
            first['request_limit'] = 1
            client = self.client(ledger, first)
            with patch.object(p, '_post', return_value=json.dumps(reply()).encode()) as transport, \
                    patch.object(p, '_env_key', return_value='synthetic-key'):
                client.complete('s', 'u')
                resumed = p.Ledger('openrouter', 1, 1, ledger.path, run_id=ledger.run_id)
                second = {**first, 'authorization_id': 'second-model-record', 'model': 'second-model'}
                other = p.ModelClient('openrouter', 'second-model', resumed, authorization=second,
                                      max_output_tokens=100, timeout=1)
                with self.assertRaises(p.BudgetExceeded):
                    other.complete('s', 'u')
                self.assertEqual(transport.call_count, 1)
                self.assertEqual(resumed.calls, 1)

    def test_replacement_record_cannot_raise_shared_request_cap(self):
        with tempfile.TemporaryDirectory() as tmp:
            ledger = self.ledger(tmp)
            first = authorization(ledger)
            first['request_limit'] = 2
            client = self.client(ledger, first)
            with patch.object(p, '_post', return_value=json.dumps(reply()).encode()) as transport, \
                    patch.object(p, '_env_key', return_value='synthetic-key'):
                client.complete('s', 'u')
                replacement = {**first, 'authorization_id': 'replacement', 'request_limit': 3}
                changed = self.client(ledger, replacement)
                with self.assertRaises(p.BudgetExceeded):
                    changed.complete('s', 'u')
                self.assertEqual(transport.call_count, 1)

    def test_production_missing_commit_is_rejected_before_io(self):
        from fleet_witness.swarm import authorization as gate
        with tempfile.TemporaryDirectory() as tmp:
            ledger = self.ledger(tmp)
            record = authorization(ledger)
            missing = {**p.source_identity(), 'source_commit': None}
            with patch.object(gate, 'source_identity', return_value=missing), \
                    patch.object(p, '_env_key', side_effect=AssertionError('credential touched')):
                with self.assertRaises(p.ProviderError):
                    self.client(ledger, record)

    def test_truncation_never_retries_logical_request(self):
        client = object.__new__(p.ModelClient)
        client.max_output_tokens = 100
        caps = []
        def attempt(system, user, cap):
            caps.append(cap)
            return {'text': '', 'input_tokens': 1, 'output_tokens': cap,
                    'cost_usd': .001, 'truncated': True, 'latency_s': 0,
                    'attempts': [], 'provider_attempts': 1, 'held_usd': 0, 'status': 'truncated'}
        client._attempt = attempt
        client.complete('s', 'u')
        self.assertEqual(caps, [100])

    def test_explicit_stop_near_cap_is_one_success_with_private_receipt(self):
        with tempfile.TemporaryDirectory() as tmp:
            ledger = self.ledger(tmp)
            client = self.client(ledger)
            sent = []
            def transport(url, key, body, timeout, **kwargs):
                sent.append(body)
                return json.dumps(reply()).encode()
            with patch.object(p, '_post', transport), patch.object(p, '_env_key', return_value='synthetic-key'):
                result = client.complete('PRIVATE INSTRUCTION', 'private user text')
            self.assertEqual(len(sent), 1)
            self.assertFalse(result['truncated'])
            self.assertEqual(result['provider_attempts'], 1)
            self.assertEqual(result['status'], 'succeeded')
            self.assertEqual(result['cost_usd'], .000099)
            self.assertNotIn('PRIVATE INSTRUCTION', json.dumps(result['attempts']))
            self.assertNotIn('private user text', json.dumps(result['attempts']))
            with closing(sqlite3.connect(ledger.path)) as con:
                row = con.execute('SELECT request_json,response_raw,status FROM requests').fetchone()
            self.assertIn('PRIVATE INSTRUCTION', row[0])
            self.assertIn(b'"vote"', row[1].replace(b'\\', b''))
            self.assertEqual(row[2], 'succeeded')

    def test_protected_body_overrides_fail_before_credential_or_dispatch(self):
        for field in ('model', 'messages', 'max_tokens', 'stream', 'tools', 'provider'):
            with self.subTest(field=field), tempfile.TemporaryDirectory() as tmp:
                ledger = self.ledger(tmp)
                client = self.client(ledger)
                client.extra_body = {field: 10000}
                with patch.object(p, '_env_key', side_effect=AssertionError('credential accessed')), patch.object(p, '_post', side_effect=AssertionError('network accessed')):
                    with self.assertRaises(p.ProviderError):
                        client.complete('s', 'u')
                self.assertEqual(ledger.calls, 0)
                self.assertEqual(ledger.run_reserved, 0)

    def test_bad_usage_holds_reservation_and_stops_following_dispatch(self):
        for data in (reply(usage=False), reply(tokens=-1), reply(tokens=True), reply(tokens=1.5),
                     reply(tokens=101), reply(cost=-1), reply(cost=float('nan'))):
            with self.subTest(data=data), tempfile.TemporaryDirectory() as tmp:
                ledger = self.ledger(tmp)
                client = self.client(ledger)
                with patch.object(p, '_post', return_value=json.dumps(data).encode()), patch.object(p, '_env_key', return_value='synthetic-key'):
                    with self.assertRaises(p.ProviderError) as caught:
                        client.complete('s', 'u')
                    self.assertEqual(caught.exception.provider_attempts, 1)
                    self.assertGreater(caught.exception.held_usd, 0)
                    with self.assertRaises(p.BudgetExceeded):
                        client.complete('s', 'u')
                self.assertEqual(ledger.calls, 1)
                self.assertEqual(ledger.run_spent, 0)
                self.assertTrue(ledger.snapshot()['halted'])

    def test_reported_overrun_retains_larger_liability(self):
        with tempfile.TemporaryDirectory() as tmp:
            ledger = self.ledger(tmp)
            client = self.client(ledger)
            with patch.object(p, '_post', return_value=json.dumps(reply(cost=1.5)).encode()), patch.object(p, '_env_key', return_value='synthetic-key'):
                with self.assertRaises(p.ProviderError) as caught:
                    client.complete('s', 'u')
            self.assertEqual(caught.exception.held_usd, 1.5)
            self.assertEqual(ledger.run_reserved, 1.5)
            self.assertEqual(caught.exception.status, 'overrun')

    def test_wrong_source_expired_or_unqualified_record_refuses_before_io(self):
        for change in ('source', 'expired', 'qualification', 'ledger', 'pricing', 'confirmatory'):
            with self.subTest(change=change), tempfile.TemporaryDirectory() as tmp:
                ledger = self.ledger(tmp)
                self.assertTrue(hasattr(p, 'source_identity'), 'authorization must bind executable source')
                record = authorization(ledger)
                if change == 'source': record['source_sha256'] = '0' * 64
                if change == 'expired': record['expires_at'] = 1
                if change == 'qualification': record['qualification']['retention_reviewed'] = False
                if change == 'ledger': record['ledger_path'] += '.other'
                if change == 'pricing': record['pricing']['unit'] = 'unverified credits'
                if change == 'confirmatory': record['purpose'] = 'confirmatory'
                with patch.object(p, '_env_key', side_effect=AssertionError('credential accessed')), patch.object(p, '_post', side_effect=AssertionError('network accessed')):
                    with self.assertRaises(p.ProviderError):
                        self.client(ledger, record)

    def test_transport_failure_keeps_receipt_and_reservation(self):
        with tempfile.TemporaryDirectory() as tmp:
            ledger = self.ledger(tmp)
            client = self.client(ledger)
            with patch.object(p, '_post', side_effect=TimeoutError('private upstream error')), patch.object(p, '_env_key', return_value='synthetic-key'):
                with self.assertRaises(p.ProviderError) as caught:
                    client.complete('s', 'u')
            self.assertEqual(len(caught.exception.attempts), 1)
            self.assertNotIn('private upstream error', str(caught.exception))
            self.assertGreater(caught.exception.held_usd, 0)
            with closing(sqlite3.connect(ledger.path)) as con:
                row = con.execute('SELECT status,receipt_json FROM requests').fetchone()
            self.assertEqual(row[0], 'unresolved')
            self.assertIn('transport_failure', row[1])

class AdditionalBoundaryTest(SyntheticSourceTestCase):
    ledger = ProviderBoundaryTest.ledger
    client = ProviderBoundaryTest.client

    def test_maximum_request_bound_covers_unicode_and_largest_authorized_prompt(self):
        with tempfile.TemporaryDirectory() as tmp:
            ledger = self.ledger(tmp)
            client = self.client(ledger)
            self.assertTrue(callable(getattr(client, 'maximum_request_usd', None)),
                            'run estimates need an authorized maximum, not one sample prompt')
            for prompt in ('x' * 4096, '\x00' * 4096, '\u00e9' * 2048):
                self.assertGreaterEqual(client.maximum_request_usd(), client.worst_case_usd('', prompt))
            self.assertEqual(p.FakeClient().maximum_request_usd(), 0)

    def test_excess_valid_usage_retains_computed_liability(self):
        with tempfile.TemporaryDirectory() as tmp:
            ledger = self.ledger(tmp)
            client = self.client(ledger)
            with patch.object(p, '_post', return_value=json.dumps(reply(tokens=2000000)).encode()), patch.object(p, '_env_key', return_value='synthetic-key'):
                with self.assertRaises(p.ProviderError) as caught:
                    client.complete('s', 'u')
            self.assertEqual(caught.exception.held_usd, 2.000001)
            self.assertEqual(ledger.run_reserved, 2.000001)

    def test_credential_echo_is_redacted_from_private_receipt_and_final_text(self):
        with tempfile.TemporaryDirectory() as tmp:
            ledger = self.ledger(tmp)
            client = self.client(ledger)
            data = reply()
            data['choices'][0]['message']['content'] = 'echo synthetic-private-key'
            with patch.object(p, '_post', return_value=json.dumps(data).encode()), patch.object(p, '_env_key', return_value='synthetic-private-key'):
                with self.assertRaises(p.ProviderError):
                    client.complete('s', 'u')
            with closing(sqlite3.connect(ledger.path)) as con:
                raw = con.execute('SELECT response_raw FROM requests').fetchone()[0]
            self.assertNotIn(b'synthetic-private-key', raw)
            self.assertIn(b'[REDACTED]', raw)

    def test_run_cap_and_count_persist_when_resumed(self):
        with tempfile.TemporaryDirectory() as tmp:
            ledger = self.ledger(tmp)
            record = authorization(ledger)
            record['request_limit'] = 1
            client = self.client(ledger, record)
            with patch.object(p, '_post', return_value=json.dumps(reply()).encode()), patch.object(p, '_env_key', return_value='synthetic-key'):
                client.complete('s', 'u')
                restarted = p.Ledger('openrouter', 1, 1, ledger.path, run_id=ledger.run_id)
                resumed = self.client(restarted, record)
                with self.assertRaises(p.BudgetExceeded):
                    resumed.complete('s', 'u')
            self.assertEqual(restarted.calls, 1)
            with self.assertRaises(p.BudgetExceeded):
                p.Ledger('openrouter', 2, 1, ledger.path, run_id=ledger.run_id)

    def test_receipt_write_failure_keeps_dispatched_hold_and_exception_accounting(self):
        with tempfile.TemporaryDirectory() as tmp:
            ledger = self.ledger(tmp)
            client = self.client(ledger)
            def broken_receipt(*args, **kwargs):
                with closing(sqlite3.connect(ledger.path)) as con:
                    con.execute("CREATE TRIGGER fail_receipt BEFORE INSERT ON audit BEGIN SELECT RAISE(ABORT, 'disk unavailable'); END")
                return json.dumps(reply()).encode()
            with patch.object(p, '_post', broken_receipt), patch.object(p, '_env_key', return_value='synthetic-key'):
                with self.assertRaises(p.ProviderError) as caught:
                    client.complete('s', 'u')
            self.assertEqual(caught.exception.provider_attempts, 1)
            self.assertGreater(caught.exception.held_usd, 0)
            self.assertEqual(caught.exception.attempts[0]['error_code'], 'receipt_persistence_failure')
            self.assertEqual(ledger.calls, 1)
            self.assertGreater(ledger.run_reserved, 0)
            with closing(sqlite3.connect(ledger.path)) as con:
                self.assertEqual(con.execute('SELECT status FROM requests').fetchone()[0], 'dispatched')

    def test_constructor_and_estimator_do_not_read_credential_or_network(self):
        with tempfile.TemporaryDirectory() as tmp:
            ledger = self.ledger(tmp)
            with patch.object(p, '_env_key', side_effect=AssertionError('key read')), patch.object(p, '_post', side_effect=AssertionError('network')):
                client = self.client(ledger)
                self.assertGreater(client.worst_case_usd('s', 'u'), 0)

    def test_closed_outcomes_retain_raw_response_without_extra_requests(self):
        variants = [b'{"usage":{},"usage":{}}', b'[]', b'{', b'{"x":' + b'[' * 40 + b'0' + b']' * 40 + b'}']
        for finish in (None, 'tool_calls', 'error'):
            variants.append(json.dumps(reply(finish=finish)).encode())
        data = reply()
        data['choices'][0]['message']['tool_calls'] = [{'function': {'name': 'untrusted'}}]
        variants.append(json.dumps(data).encode())
        for raw in variants:
            with self.subTest(raw=raw), tempfile.TemporaryDirectory() as tmp:
                ledger = self.ledger(tmp)
                client = self.client(ledger)
                with patch.object(p, '_post', return_value=raw), patch.object(p, '_env_key', return_value='synthetic-key'):
                    with self.assertRaises(p.ProviderError): client.complete('s', 'u')
                self.assertEqual(ledger.calls, 1)
                self.assertGreater(ledger.run_reserved, 0)
                with closing(sqlite3.connect(ledger.path)) as con:
                    self.assertEqual(con.execute('SELECT response_raw FROM requests').fetchone()[0], raw)

class TransportBoundaryTest(SyntheticSourceTestCase):
    def connection(self, *, status=200, raw=b'{}', connection_close=False):
        observed = {'hosts': [], 'requests': [], 'timeouts': [], 'closed': 0}
        class Socket:
            def settimeout(self, timeout): observed['timeouts'].append(timeout)
        class Response:
            def __init__(self):
                self.status, self.remaining = status, raw
            def read1(self, count):
                chunk, self.remaining = self.remaining[:count], self.remaining[count:]
                return chunk
            def getheader(self, name, default=None): return default
        class Connection:
            def __init__(self, host, timeout):
                observed['hosts'].append(host)
                self.sock = Socket()
            def connect(self): pass
            def request(self, method, path, body, headers): observed['requests'].append((method, path, body, headers))
            def getresponse(self):
                if connection_close: self.sock = None
                return Response()
            def close(self): observed['closed'] += 1
        return Connection, observed

    def test_429_and_redirects_are_one_attempt_with_bounded_private_receipt(self):
        for status in (429, 301, 302, 307, 400, 500):
            with self.subTest(status=status), tempfile.TemporaryDirectory() as tmp:
                ledger = p.Ledger('openrouter', 1, 1, Path(tmp) / 'ledger.sqlite3')
                client = p.ModelClient('openrouter', 'fixture-model', ledger, max_output_tokens=100,
                                       timeout=1, authorization=authorization(ledger))
                connection, observed = self.connection(status=status, raw=b'provider private body')
                with patch.object(p.http.client, 'HTTPSConnection', connection), patch.object(p, '_env_key', return_value='synthetic-key'):
                    with self.assertRaises(p.ProviderError) as caught: client.complete('s', 'u')
                self.assertEqual(len(observed['requests']), 1)
                self.assertEqual(caught.exception.attempts[0]['http_status'], status)
                self.assertGreater(ledger.run_reserved, 0)
                self.assertNotIn('provider private body', str(caught.exception))
                with closing(sqlite3.connect(ledger.path)) as con:
                    self.assertEqual(con.execute('SELECT response_raw FROM requests').fetchone()[0], b'provider private body')

    def test_direct_https_ignores_proxy_environment_and_returns_connection_close_body(self):
        connection, observed = self.connection(raw=b'{"ok":true}', connection_close=True)
        with patch.dict('os.environ', {'HTTPS_PROXY': 'http://untrusted.invalid:3128'}), patch.object(p.http.client, 'HTTPSConnection', connection):
            result = p._post(p.OPENROUTER_URL, 'synthetic-key', {'model': 'fixture'}, 1, max_response_bytes=100)
        self.assertEqual(result, b'{"ok":true}')
        self.assertEqual(observed['hosts'], ['openrouter.ai'])
        self.assertEqual(observed['requests'][0][:2], ('POST', '/api/v1/chat/completions'))
        self.assertEqual(observed['requests'][0][3]['Authorization'], 'Bearer synthetic-key')

    def test_response_byte_limit_stops_read_and_retains_bounded_prefix(self):
        connection, observed = self.connection(raw=b'x' * 1000)
        with patch.object(p.http.client, 'HTTPSConnection', connection):
            with self.assertRaises(p.ProviderError) as caught:
                p._post(p.OPENROUTER_URL, 'synthetic-key', {}, 1, max_response_bytes=20)
        self.assertEqual(caught.exception.raw, b'x' * 21)
        self.assertEqual(len(observed['requests']), 1)

    def test_stalled_connect_returns_by_deadline_and_never_dispatches_afterward(self):
        import threading
        release, stopped = threading.Event(), threading.Event()
        sent = []
        class Connection:
            def __init__(self, *args, **kwargs): pass
            def connect(self): release.wait(2)
            def request(self, *args, **kwargs): sent.append('request')
            def close(self): stopped.set()
        start = time.monotonic()
        with patch.object(p.http.client, 'HTTPSConnection', Connection):
            with self.assertRaises(p.ProviderError):
                p._post(p.OPENROUTER_URL, 'synthetic-key', {}, .03, max_response_bytes=20)
            self.assertLess(time.monotonic() - start, .5)
            release.set()
            self.assertTrue(stopped.wait(1))
        self.assertEqual(sent, [])


class RecordPreflightTest(SyntheticSourceTestCase):
    def test_record_preflight_checks_source_and_authority_without_opening_ledger(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertTrue(callable(getattr(p, 'validate_record', None)), 'operator must validate before ledger initialization')
            ledger = p.Ledger('openrouter', 1, 1, Path(tmp) / 'existing.sqlite3')
            record = authorization(ledger)
            record['ledger_path'] = str(Path(tmp) / 'unopened.sqlite3')
            with patch.object(p, '_env_key', side_effect=AssertionError('key read')), patch('sqlite3.connect', side_effect=AssertionError('ledger opened')):
                self.assertEqual(p.validate_record(record), record)
                record['qualification']['access_verified'] = False
                with self.assertRaises(p.ProviderError): p.validate_record(record)
            self.assertFalse((Path(tmp) / 'unopened.sqlite3').exists())

class DecimalUsageTest(SyntheticSourceTestCase):
    def test_reported_decimal_charge_rounds_up_without_float_loss(self):
        with tempfile.TemporaryDirectory() as tmp:
            ledger = p.Ledger('openrouter', 1, 1, Path(tmp) / 'ledger.sqlite3')
            client = p.ModelClient('openrouter', 'fixture-model', ledger, max_output_tokens=100,
                                   timeout=1, authorization=authorization(ledger))
            raw = b'{"choices":[{"message":{"content":"ok"},"finish_reason":"stop"}],"usage":{"prompt_tokens":1,"completion_tokens":1,"cost":0.10000000000000000001}}'
            with patch.object(p, '_post', return_value=raw), patch.object(p, '_env_key', return_value='synthetic-key'):
                with self.assertRaises(p.ProviderError) as caught: client.complete('s', 'u')
            self.assertEqual(caught.exception.held_usd, .100000001)
            self.assertEqual(ledger.run_reserved, .100000001)

class AdaptionBoundaryTest(SyntheticSourceTestCase):
    def test_completed_adaption_reply_uses_direct_tool_free_bounded_request(self):
        with tempfile.TemporaryDirectory() as tmp:
            ledger = p.Ledger('adaption', 1, 1, Path(tmp) / 'ledger.sqlite3')
            record = authorization(ledger, provider='adaption')
            client = p.ModelClient('adaption', 'fixture-model', ledger, max_output_tokens=100,
                                   timeout=1, authorization=record)
            sent = []
            def transport(url, key, body, timeout, **kwargs):
                sent.append(body)
                return b'{"id":"fixture","status":"completed","output":[{"type":"message","content":[{"type":"output_text","text":"ok"}]}],"usage":{"input_tokens":1,"output_tokens":99}}'
            with patch.object(p, '_post', transport), patch.object(p, '_env_key', return_value='synthetic-key'):
                result = client.complete('s', 'u')
            self.assertEqual(result['text'], 'ok')
            self.assertFalse(result['truncated'])
            self.assertEqual(len(sent), 1)
            for field, expected in {'tools': [], 'tool_choice': 'none', 'store': False,
                                    'agentic_memory': False, 'background': False, 'max_output_tokens': 100}.items():
                self.assertEqual(sent[0][field], expected)

    def test_adaption_route_alias_cannot_replace_direct_model_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            ledger = p.Ledger('adaption', 1, 1, Path(tmp) / 'ledger.sqlite3')
            record = authorization(ledger, provider='adaption')
            record['model'] = 'agent:unreviewed-route'
            with self.assertRaises(p.ProviderError):
                p.ModelClient('adaption', record['model'], ledger, max_output_tokens=100, timeout=1, authorization=record)
