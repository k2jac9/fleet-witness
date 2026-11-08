"""Trusted-host live calibration foundation; importing this module spends nothing.

No network transport or credential loading is implemented yet. Monetary units
are integer microcredits; one credit equals 1,000,000 microcredits. The parent
ledger directory is a trusted private operator location, not a hostile-process
sandbox. The offline fake gateway and controller are independent.
"""
from contextlib import closing, contextmanager
import json
import math
import os
from pathlib import Path
import re
import sqlite3
import stat
import time

from .gateway import MAX_BYTES, ProviderReply, _proposal, _unique_object, provider_input

MICROCREDITS_PER_CREDIT = 1_000_000
MODEL = 'gemma-4-31b-it'
FIXTURE_MODE = 'offline-calibration-fixture'


class LiveBudgetError(RuntimeError):
    """A budget, deadline, or unresolved request prevents dispatch."""


def new_authorization(expires_at: int, rate_snapshot_sha256: str) -> dict:
    """Build the fixed one-request calibration record, not a provider call."""
    if type(expires_at) is not int or expires_at < 0 or expires_at > int(time.time()) + 3600:
        raise ValueError('invalid calibration deadline')
    if not isinstance(rate_snapshot_sha256, str) or not re.fullmatch(r'[0-9a-f]{64}', rate_snapshot_sha256):
        raise ValueError('rate evidence must be an exact SHA-256 digest')
    return {'mode': FIXTURE_MODE, 'provider': 'adaption', 'model': MODEL,
            'budget_microcredits': MICROCREDITS_PER_CREDIT, 'request_limit': 1,
            'timeout_seconds': 30, 'max_output_tokens': 256, 'context_tokens': 256_000,
            'input_rate_microcredits_per_million': 90_000,
            'output_rate_microcredits_per_million': 340_000,
            'rate_snapshot_sha256': rate_snapshot_sha256, 'expires_at': expires_at}


def _authorization(value):
    if not isinstance(value, dict):
        raise ValueError('authorization must be an object')
    try:
        expected = new_authorization(value['expires_at'], value['rate_snapshot_sha256'])
    except (KeyError, TypeError):
        raise ValueError('invalid authorization') from None
    if value != expected or set(value) != set(expected):
        raise ValueError('authorization changes fixed calibration constraints')
    return expected


def _request_id(value):
    if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9._:-]{1,128}', value):
        raise ValueError('invalid request identity')


def build_provider_request(facts: dict, presentation: str) -> dict:
    """Build a bounded, tool-free request without touching a credential or network."""
    visible = provider_input(facts, presentation)
    return {'model': MODEL,
            'input': json.dumps(visible, ensure_ascii=True, sort_keys=True, separators=(',', ':')),
            'max_output_tokens': 256, 'tools': [], 'tool_choice': 'none',
            'store': False, 'agentic_memory': False, 'background': False}


def parse_provider_response(raw: bytes) -> dict:
    """Parse bounded inert JSON; duplicate keys and invalid Unicode fail closed."""
    if not isinstance(raw, bytes) or len(raw) > 65_536:
        raise ValueError('provider response exceeds byte limit')
    try:
        def reject_constant(_):
            raise ValueError('non-finite JSON number')
        value = json.loads(raw.decode('utf-8'), object_pairs_hook=_unique_object,
                           parse_constant=reject_constant)
        if not isinstance(value, dict):
            raise ValueError('provider response must be an object')
        pending = [(value, 1)]
        while pending:
            item, depth = pending.pop()
            if depth > 32:
                raise ValueError('provider response too deeply nested')
            if isinstance(item, dict):
                for key, child in item.items():
                    key.encode('utf-8')
                    pending.append((child, depth + 1))
            elif isinstance(item, list):
                pending.extend((child, depth + 1) for child in item)
            elif isinstance(item, str):
                item.encode('utf-8')
            elif isinstance(item, float) and not math.isfinite(item):
                raise ValueError('non-finite JSON number')
        return value
    except (ValueError, UnicodeError, RecursionError, OverflowError):
        raise ValueError('invalid bounded provider response') from None


class LiveLedger:
    """One shared SQLite ledger with atomic request state and audit events."""
    def __init__(self, path: Path, authorization: dict):
        checked = _authorization(authorization)
        self._authorization_json = json.dumps(checked, sort_keys=True, separators=(',', ':'))
        self.path = Path(path)
        parent = self.path.parent.lstat()
        if (not stat.S_ISDIR(parent.st_mode) or parent.st_uid != os.getuid()
                or stat.S_IMODE(parent.st_mode) & 0o077):
            raise ValueError('ledger parent must be an owner-private directory')
        fd = os.open(self.path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600)
        try:
            meta = os.fstat(fd)
            if (not stat.S_ISREG(meta.st_mode) or meta.st_nlink != 1
                    or meta.st_uid != os.getuid() or stat.S_IMODE(meta.st_mode) & 0o077):
                raise ValueError('ledger must be an owner-private singly-linked regular file')
        finally:
            os.close(fd)
        with closing(self._connect()) as c:
            c.executescript('''
                CREATE TABLE IF NOT EXISTS authorization (
                    id INTEGER PRIMARY KEY CHECK(id=1), data TEXT NOT NULL,
                    halted INTEGER NOT NULL CHECK(halted IN (0,1)));
                CREATE TABLE IF NOT EXISTS requests (
                    id TEXT PRIMARY KEY, status TEXT NOT NULL
                        CHECK(status IN ('reserved','dispatched','unresolved','settled')),
                    reserved_microcredits INTEGER NOT NULL, actual_microcredits INTEGER,
                    input_json TEXT NOT NULL, result_json TEXT);
                CREATE TABLE IF NOT EXISTS audit (
                    seq INTEGER PRIMARY KEY AUTOINCREMENT, request_id TEXT,
                    kind TEXT NOT NULL, details TEXT NOT NULL);
            ''')
        with self._transaction() as c:
            row = c.execute('SELECT data FROM authorization WHERE id=1').fetchone()
            if row is None:
                c.execute('INSERT INTO authorization VALUES(1,?,0)', (self._authorization_json,))
                self._audit(c, None, 'authorization_created', {})
            elif row['data'] != self._authorization_json:
                raise ValueError('existing authorization cannot be changed implicitly')

    @property
    def authorization(self):
        """Return a detached copy of the frozen authorization."""
        return json.loads(self._authorization_json)

    def _connect(self):
        c = sqlite3.connect(self.path, timeout=15)
        c.row_factory = sqlite3.Row
        return c

    @contextmanager
    def _transaction(self):
        with closing(self._connect()) as c, c:
            c.execute('BEGIN IMMEDIATE')
            yield c

    @staticmethod
    def _audit(c, request_id, kind, details):
        c.execute('INSERT INTO audit(request_id,kind,details) VALUES(?,?,?)',
                  (request_id, kind, json.dumps(details, sort_keys=True, separators=(',', ':'))))

    def _snapshot(self, c):
        config = c.execute('SELECT data,halted FROM authorization WHERE id=1').fetchone()
        if config is None or config['data'] != self._authorization_json:
            raise ValueError('persisted authorization changed unexpectedly')
        auth = json.loads(config['data'])
        requests = {}
        spent = held = 0
        for row in c.execute('SELECT * FROM requests ORDER BY rowid'):
            item = dict(row)
            item['model_input'] = json.loads(item.pop('input_json'))
            result_json = item.pop('result_json')
            item['result'] = json.loads(result_json) if result_json is not None else None
            if item['status'] == 'settled':
                spent += item['actual_microcredits']
            else:
                held += max(item['reserved_microcredits'], item['actual_microcredits'] or 0)
            requests[item.pop('id')] = item
        return {'budget_microcredits': auth['budget_microcredits'], 'spent_microcredits': spent,
                'held_microcredits': held, 'available_microcredits': auth['budget_microcredits'] - spent - held,
                'halted': bool(config['halted']), 'requests': requests}

    def snapshot(self):
        with closing(self._connect()) as c:
            c.execute('BEGIN')
            return self._snapshot(c)

    def reserve(self, request_id: str, facts: dict, presentation: str):
        _request_id(request_id)
        payload = provider_input(facts, presentation)
        encoded = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(',', ':'))
        with self._transaction() as c:
            state = self._snapshot(c)
            if request_id in state['requests']:
                raise ValueError('request identity cannot be reused')
            if (state['halted'] or int(time.time()) >= self.authorization['expires_at']
                    or len(state['requests']) >= self.authorization['request_limit']
                    or state['available_microcredits'] < MICROCREDITS_PER_CREDIT):
                raise LiveBudgetError('authorization expired or calibration budget unavailable')
            c.execute('INSERT INTO requests VALUES(?,?,?,NULL,?,NULL)',
                      (request_id, 'reserved', MICROCREDITS_PER_CREDIT, encoded))
            self._audit(c, request_id, 'reserved', {'microcredits': MICROCREDITS_PER_CREDIT})

    def dispatch(self, request_id: str):
        _request_id(request_id)
        with self._transaction() as c:
            state = self._snapshot(c)
            request = state['requests'].get(request_id)
            if request is None or request['status'] != 'reserved':
                raise ValueError('only a fresh reservation can be dispatched')
            if state['halted'] or int(time.time()) >= self.authorization['expires_at']:
                raise LiveBudgetError('authorization expired or dispatch halted')
            c.execute("UPDATE requests SET status='dispatched' WHERE id=?", (request_id,))
            self._audit(c, request_id, 'dispatched', {})

    def uncertain(self, request_id: str, reason: str):
        _request_id(request_id)
        if reason not in ('timeout', 'network_error', 'response_error', 'provider_error', 'operator_cancelled'):
            raise ValueError('unknown unresolved classification')
        with self._transaction() as c:
            self._snapshot(c)
            row = c.execute('SELECT status FROM requests WHERE id=?', (request_id,)).fetchone()
            if row is None or row['status'] != 'dispatched':
                raise ValueError('only dispatched requests can become unresolved')
            c.execute("UPDATE requests SET status='unresolved' WHERE id=?", (request_id,))
            c.execute('UPDATE authorization SET halted=1 WHERE id=1')
            self._audit(c, request_id, 'unresolved', {'reason': reason, 'reservation_retained': True})

    def settle(self, request_id: str, response: dict):
        """Settle a completed response or retain all liability on ambiguity."""
        _request_id(request_id)
        usage = _usage(response)
        status_valid = (isinstance(response, dict) and response.get('object') == 'response'
                        and response.get('status') == 'completed' and response.get('model') == MODEL
                        and response.get('error') is None and response.get('incomplete_details') is None
                        and _items_final(response.get('output'))
                        and isinstance(response.get('id'), str)
                        and re.fullmatch(r'[A-Za-z0-9._:-]{1,128}', response['id']) is not None)
        known_cost = None if usage is None else (
            usage['input_tokens'] * self.authorization['input_rate_microcredits_per_million']
            + usage['output_tokens'] * self.authorization['output_rate_microcredits_per_million']
            + 999_999) // 1_000_000
        invalid_accounting = (usage is None or not status_valid
                              or usage['input_tokens'] == 0
                              or (usage['output_tokens'] == 0 and isinstance(response.get('output'), list)
                                  and bool(response['output']))
                              or usage['total_tokens'] > self.authorization['context_tokens']
                              or usage['output_tokens'] > self.authorization['max_output_tokens']
                              or known_cost > MICROCREDITS_PER_CREDIT)
        result = None
        if not invalid_accounting:
            text = _output_text(response)
            proposal = _proposal(ProviderReply(text, 0)) if text is not None else None
            result = {'mode': FIXTURE_MODE, 'request_id': request_id,
                      'status': 'completed' if proposal else 'invalid_output',
                      'model': MODEL, 'provider_response_id': response['id'],
                      'recommendation': proposal['recommendation'] if proposal else None,
                      'reason': proposal['reason'] if proposal else None,
                      'raw_output': text, 'usage': usage, 'estimated_microcredits': known_cost}
        with self._transaction() as c:
            self._snapshot(c)
            row = c.execute('SELECT status FROM requests WHERE id=?', (request_id,)).fetchone()
            if row is None or row['status'] != 'dispatched':
                raise ValueError('only dispatched requests can settle')
            if invalid_accounting:
                rejection = {'mode': FIXTURE_MODE, 'request_id': request_id,
                             'status': 'unresolved', 'classification': 'accounting_error',
                             'provider_response_id': _safe_identifier(response, 'id'),
                             'reported_model': _safe_identifier(response, 'model'),
                             'usage': usage, 'estimated_microcredits': known_cost,
                             'recommendation': None}
                c.execute("UPDATE requests SET status='unresolved',actual_microcredits=?,result_json=? WHERE id=?",
                          (known_cost, json.dumps(rejection, separators=(',', ':')), request_id))
                c.execute('UPDATE authorization SET halted=1 WHERE id=1')
                self._audit(c, request_id, 'unresolved', {'reason': 'accounting_error',
                                                        'known_microcredits': known_cost})
            else:
                c.execute("UPDATE requests SET status='settled',actual_microcredits=?,result_json=? WHERE id=?",
                          (known_cost, json.dumps(result, ensure_ascii=True, separators=(',', ':')), request_id))
                self._audit(c, request_id, 'settled', {'microcredits': known_cost, 'status': result['status']})
        if invalid_accounting:
            raise LiveBudgetError('response or usage is ambiguous; reservation retained')
        return result


def _usage(response):
    if not isinstance(response, dict) or not isinstance(response.get('usage'), dict):
        return None
    data = response['usage']
    if not set(data).issubset({'input_tokens', 'output_tokens', 'total_tokens',
                               'input_tokens_details', 'output_tokens_details'}):
        return None
    fields = ('input_tokens', 'output_tokens', 'total_tokens')
    if any(type(data.get(field)) is not int or not 0 <= data[field] <= 2**53 - 1 for field in fields):
        return None
    if data['input_tokens'] + data['output_tokens'] != data['total_tokens']:
        return None
    for details, allowed, bound in [('input_tokens_details', 'cached_tokens', data['input_tokens']),
                                    ('output_tokens_details', 'reasoning_tokens', data['output_tokens'])]:
        value = data.get(details)
        if value is not None:
            if not isinstance(value, dict) or not set(value).issubset({allowed}):
                return None
            if allowed in value and (type(value[allowed]) is not int or not 0 <= value[allowed] <= bound):
                return None
    result = {field: data[field] for field in fields}
    for details in ('input_tokens_details', 'output_tokens_details'):
        if data.get(details) is not None:
            result[details] = dict(data[details])
    return result


def _safe_identifier(response, field):
    if not isinstance(response, dict):
        return None
    value = response.get(field)
    return value if isinstance(value, str) and re.fullmatch(r'[A-Za-z0-9._:-]{1,128}', value) else None


def _items_final(output):
    if not isinstance(output, list):
        return True  # Invalid schema is classified separately as invalid output.
    return all(not isinstance(item, dict) or 'status' not in item or item['status'] == 'completed'
               for item in output)


def _output_text(response):
    try:
        output = response['output']
        if not isinstance(output, list) or len(output) != 1 or not isinstance(output[0], dict):
            return None
        item = output[0]
        content = item.get('content')
        if (item.get('type') != 'message' or item.get('role') != 'assistant'
                or not isinstance(content, list) or len(content) != 1 or not isinstance(content[0], dict)
                or content[0].get('type') != 'output_text' or content[0].get('refusal')):
            return None
        text = content[0].get('text')
        if (not isinstance(text, str) or len(text.encode('utf-8')) > MAX_BYTES
                or ('output_text' in response and response['output_text'] != text)):
            return None
        return text
    except (KeyError, UnicodeError, RecursionError):
        return None


class FixtureTransport:
    """Inert test source; it has no URL, credential access or network code."""
    def __init__(self, responses):
        if not isinstance(responses, list) or any(not isinstance(item, bytes) for item in responses):
            raise ValueError('fixture responses must be a list of bytes')
        self._responses = list(responses)
        self.requests = []

    def send(self, request):
        self.requests.append(json.loads(json.dumps(request)))
        if not self._responses:
            raise ValueError('fixture exhausted')
        return self._responses.pop(0)


class FixtureRunner:
    """Exercise the accounting and wire contracts only with an inert fixture."""
    def __init__(self, ledger: LiveLedger, transport: FixtureTransport):
        if type(ledger) is not LiveLedger or type(transport) is not FixtureTransport:
            raise ValueError('only an inert fixture transport is implemented')
        self.ledger = ledger
        self.transport = transport

    def run(self, request_id: str, facts: dict, presentation: str):
        request = build_provider_request(facts, presentation)
        visible = json.loads(request['input'])
        self.ledger.reserve(request_id, visible['facts'], presentation)
        self.ledger.dispatch(request_id)
        try:
            raw = self.transport.send(request)
            response = parse_provider_response(raw)
        except Exception:
            self.ledger.uncertain(request_id, 'response_error')
            return {'mode': FIXTURE_MODE, 'request_id': request_id, 'status': 'unresolved'}
        try:
            return self.ledger.settle(request_id, response)
        except LiveBudgetError:
            return {'mode': FIXTURE_MODE, 'request_id': request_id, 'status': 'unresolved'}
