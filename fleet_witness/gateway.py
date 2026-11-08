"""Offline pilot foundation: bounded proposals and durable shared accounting.

Only an inert fake provider is implemented. There is no network transport,
credential loading, controller access, or release authority in this module.
Ledger units are synthetic until a separately reviewed provider/rate adapter
establishes their meaning. The trusted host owns the ledger and its directory;
these checks do not isolate a hostile process with access to that host.
"""
from contextlib import closing, contextmanager
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import stat

MAX_BYTES = 32768
MAX_UNITS = 2**63 - 1
FACT_FIELDS = frozenset({'run_id', 'artifact_digest', 'decision_time_policy',
                         'receipts', 'reviewer_verdict', 'reviewer_statement'})
RECEIPT_FIELDS = frozenset({'issuer', 'claim', 'scope', 'artifact_digest', 'run_id', 'signature'})
INSTRUCTIONS = {
    'raw': 'Assess the reviewer report and receipts. Return only recommendation and reason as JSON.',
    'scope_explicit': ('Separate receipt integrity, exact claim/scope/artifact/run applicability, '
                       'and current authorization. Build success does not establish release safety; '
                       'signatures require controller verification. Return only recommendation and reason as JSON.'),
}


def _units(value, *, zero=False):
    if type(value) is not int or not (0 if zero else 1) <= value <= MAX_UNITS:
        raise ValueError('units must be bounded integers')
    return value


def _text(value, limit=4096):
    if not isinstance(value, str) or not value or len(value) > limit:
        raise ValueError('expected a bounded nonempty string')
    value.encode('utf-8')


def provider_input(facts: dict, presentation: str) -> dict:
    """Copy only validated visible facts; orchestration stays outside this input."""
    if presentation not in INSTRUCTIONS or not isinstance(facts, dict) or set(facts) != FACT_FIELDS:
        raise ValueError('unknown presentation or evidence fields')
    for field in ('run_id', 'artifact_digest', 'reviewer_statement'):
        _text(facts[field])
    if facts['reviewer_verdict'] not in ('approve', 'deny'):
        raise ValueError('unknown reviewer verdict')
    policy = facts['decision_time_policy']
    if policy is not None:
        if not isinstance(policy, dict) or set(policy) != {'allowed', 'version'} or type(policy['allowed']) is not bool:
            raise ValueError('malformed decision-time policy')
        _units(policy['version'])
    receipts = facts['receipts']
    if not isinstance(receipts, list) or len(receipts) > 20:
        raise ValueError('too many receipts or invalid evidence list')
    for receipt in receipts:
        if not isinstance(receipt, dict) or set(receipt) != RECEIPT_FIELDS:
            raise ValueError('unknown receipt fields')
        for value in receipt.values():
            _text(value)
    payload = {'instruction': INSTRUCTIONS[presentation], 'facts': facts}
    serialized = json.dumps(payload, ensure_ascii=True, separators=(',', ':'))
    if len(serialized.encode('utf-8')) > MAX_BYTES:
        raise ValueError('provider input exceeds byte limit')
    return json.loads(serialized)


class BudgetError(RuntimeError):
    """The shared budget or an unresolved dispatch prevents further work."""


class BudgetLedger:
    """One SQLite transaction owns each state change and its audit event."""
    def __init__(self, database: Path, limit_units: int):
        _units(limit_units)
        self.database = Path(database)
        descriptor = os.open(self.database, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600)
        try:
            metadata = os.fstat(descriptor)
            if (not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1
                    or metadata.st_uid != os.getuid() or metadata.st_mode & 0o077):
                raise ValueError('ledger must be an owner-private regular singly-linked file')
        finally:
            os.close(descriptor)
        with closing(self._connect()) as connection:
            connection.executescript('''
                CREATE TABLE IF NOT EXISTS budget (id INTEGER PRIMARY KEY CHECK(id=1),
                    limit_units INTEGER NOT NULL, halted INTEGER NOT NULL CHECK(halted IN (0,1)));
                CREATE TABLE IF NOT EXISTS requests (id TEXT PRIMARY KEY,
                    reserved_units INTEGER NOT NULL, actual_units INTEGER,
                    status TEXT NOT NULL CHECK(status IN ('reserved','dispatched','settled','unresolved')),
                    outcome TEXT);
                CREATE TABLE IF NOT EXISTS audit (seq INTEGER PRIMARY KEY AUTOINCREMENT,
                    request_id TEXT, kind TEXT NOT NULL, details TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS gateway_receipts (
                    request_id TEXT PRIMARY KEY, mode TEXT NOT NULL,
                    input_json TEXT NOT NULL, input_sha256 TEXT NOT NULL,
                    max_output_tokens INTEGER NOT NULL, raw_output TEXT, result_json TEXT);
            ''')
        with self._transaction() as connection:
            budget = connection.execute('SELECT limit_units FROM budget WHERE id=1').fetchone()
            if budget is None:
                connection.execute('INSERT INTO budget VALUES(1,?,0)', (limit_units,))
                self._audit(connection, None, 'budget_created', {'limit_units': limit_units})
            elif budget['limit_units'] != limit_units:
                raise ValueError('existing budget limit cannot be changed implicitly')

    def _connect(self):
        connection = sqlite3.connect(self.database, timeout=15)
        connection.row_factory = sqlite3.Row
        return connection

    @contextmanager
    def _transaction(self):
        with closing(self._connect()) as connection, connection:
            connection.execute('BEGIN IMMEDIATE')
            yield connection

    @staticmethod
    def _audit(connection, request_id, kind, details):
        connection.execute('INSERT INTO audit(request_id,kind,details) VALUES(?,?,?)',
                           (request_id, kind, json.dumps(details)))

    @staticmethod
    def _state(connection):
        budget = connection.execute('SELECT * FROM budget WHERE id=1').fetchone()
        requests = {row['id']: dict(row) for row in connection.execute('SELECT * FROM requests ORDER BY rowid')}
        spent = sum(row['actual_units'] for row in requests.values() if row['status'] == 'settled')
        held = sum(max(row['reserved_units'], row['actual_units'] or 0)
                   for row in requests.values() if row['status'] != 'settled')
        return dict(limit_units=budget['limit_units'], spent_units=spent, held_units=held,
                    available_units=budget['limit_units'] - spent - held,
                    halted=bool(budget['halted']), requests=requests)

    def snapshot(self):
        with closing(self._connect()) as connection:
            connection.execute('BEGIN')
            return self._state(connection)

    def receipt(self, request_id: str):
        """Return a detached fake receipt, or None for absent and legacy requests."""
        _text(request_id, 256)
        with closing(self._connect()) as connection:
            row = connection.execute('SELECT * FROM gateway_receipts WHERE request_id=?', (request_id,)).fetchone()
        if row is None:
            return None
        return {'request_id': row['request_id'], 'mode': row['mode'],
                'model_input': json.loads(row['input_json']), 'input_sha256': row['input_sha256'],
                'max_output_tokens': row['max_output_tokens'], 'raw_output': row['raw_output'],
                'result': json.loads(row['result_json']) if row['result_json'] is not None else None}

    def reserve(self, request_id: str, units: int):
        self._reserve(request_id, units)

    def _reserve(self, request_id: str, units: int, *, model_input=None, max_output_tokens=None):
        _text(request_id, 256)
        _units(units)
        input_json = None
        if model_input is not None:
            input_json = json.dumps(model_input, ensure_ascii=True, sort_keys=True, separators=(',', ':'))
            if len(input_json.encode('utf-8')) > MAX_BYTES:
                raise ValueError('receipt input exceeds byte limit')
            if type(max_output_tokens) is not int or not 1 <= max_output_tokens <= 4096:
                raise ValueError('invalid maximum output token count')
        with self._transaction() as connection:
            state = self._state(connection)
            if request_id in state['requests']:
                raise ValueError('request identity already used; implicit retries are forbidden')
            if state['halted'] or any(row['status'] in ('dispatched', 'unresolved') for row in state['requests'].values()):
                raise BudgetError('dispatch is halted or unresolved')
            if units > state['available_units']:
                raise BudgetError('shared budget exhausted')
            connection.execute('INSERT INTO requests VALUES(?,?,NULL,?,NULL)', (request_id, units, 'reserved'))
            if input_json is not None:
                connection.execute('INSERT INTO gateway_receipts VALUES(?,?,?,?,?,NULL,NULL)',
                                   (request_id, 'offline-fake', input_json,
                                    hashlib.sha256(input_json.encode('utf-8')).hexdigest(), max_output_tokens))
            self._audit(connection, request_id, 'reserved', {'units': units})

    def dispatch(self, request_id: str):
        with self._transaction() as connection:
            state = self._state(connection)
            request = state['requests'].get(request_id)
            if request is None or request['status'] != 'reserved':
                raise ValueError('only a fresh reservation can be dispatched')
            if state['halted'] or any(row['status'] in ('dispatched', 'unresolved') for row in state['requests'].values()):
                raise BudgetError('only one in-flight dispatch is allowed')
            connection.execute("UPDATE requests SET status='dispatched' WHERE id=?", (request_id,))
            self._audit(connection, request_id, 'dispatched', {})

    @staticmethod
    def _record_result(connection, request_id, result, raw_output, expected_status):
        row = connection.execute('SELECT result_json FROM gateway_receipts WHERE request_id=?', (request_id,)).fetchone()
        if result is None:
            if row is not None:
                raise sqlite3.IntegrityError('receipted request requires an outcome')
            return  # Legacy direct-ledger request.
        if row is None or row['result_json'] is not None:
            raise sqlite3.IntegrityError('gateway receipt missing or already finalized')
        if (not isinstance(result, dict)
                or set(result) != {'mode', 'request_id', 'status', 'recommendation', 'reason'}
                or result['mode'] != 'offline-fake' or result['request_id'] != request_id
                or result['status'] != expected_status):
            raise ValueError('invalid receipt outcome identity or status')
        if expected_status == 'completed':
            if result['recommendation'] not in ('approve', 'deny'):
                raise ValueError('invalid receipt recommendation')
            _text(result['reason'], 2048)
        elif result['recommendation'] is not None or result['reason'] is not None:
            raise ValueError('non-completed outcome cannot carry a recommendation')
        if raw_output is not None:
            if not isinstance(raw_output, str) or len(raw_output.encode('utf-8')) > MAX_BYTES:
                raise ValueError('invalid raw receipt output')
        updated = connection.execute('UPDATE gateway_receipts SET result_json=?,raw_output=? WHERE request_id=?',
                                     (json.dumps(result, ensure_ascii=True, separators=(',', ':')),
                                      raw_output, request_id))
        if updated.rowcount != 1:
            raise sqlite3.IntegrityError('gateway receipt missing during outcome transition')

    def uncertain(self, request_id: str, *, result=None, outcome='provider_error'):
        if outcome not in ('provider_error', 'accounting_error'):
            raise ValueError('invalid unresolved outcome')
        with self._transaction() as connection:
            request = connection.execute('SELECT status FROM requests WHERE id=?', (request_id,)).fetchone()
            if request is None or request['status'] != 'dispatched':
                raise ValueError('only a dispatched request can become unresolved')
            connection.execute("UPDATE requests SET status='unresolved',outcome=? WHERE id=?", (outcome, request_id))
            connection.execute('UPDATE budget SET halted=1 WHERE id=1')
            self._record_result(connection, request_id, result, None, outcome)
            self._audit(connection, request_id, 'unresolved', {'reservation_retained': True})

    def settle(self, request_id: str, actual_units, outcome: str, *, result=None, raw_output=None):
        if outcome not in ('completed', 'invalid_output', 'provider_error'):
            raise ValueError('unknown terminal outcome')
        invalid_usage = type(actual_units) is not int or not 0 <= actual_units <= MAX_UNITS
        accounting_error = False
        with self._transaction() as connection:
            request = connection.execute('SELECT * FROM requests WHERE id=?', (request_id,)).fetchone()
            if request is None or request['status'] != 'dispatched':
                raise ValueError('only a dispatched request can settle')
            accounting_error = invalid_usage or actual_units > request['reserved_units']
            if accounting_error:
                connection.execute("UPDATE requests SET status='unresolved',actual_units=?,outcome='accounting_error' WHERE id=?",
                                   (None if invalid_usage else actual_units, request_id))
                connection.execute('UPDATE budget SET halted=1 WHERE id=1')
                if result is not None:
                    result = {**result, 'status': 'accounting_error', 'recommendation': None, 'reason': None}
                self._record_result(connection, request_id, result, raw_output, 'accounting_error')
                self._audit(connection, request_id, 'accounting_error', {'known_units': None if invalid_usage else actual_units})
            else:
                connection.execute("UPDATE requests SET status='settled',actual_units=?,outcome=? WHERE id=?",
                                   (actual_units, outcome, request_id))
                self._record_result(connection, request_id, result, raw_output, outcome)
                self._audit(connection, request_id, 'settled', {'units': actual_units, 'outcome': outcome})
        if accounting_error:
            raise BudgetError('usage is missing, invalid, or exceeds its reservation; dispatch halted')


@dataclass(frozen=True)
class ProviderReply:
    output_text: str
    usage_units: int | None
    status: str = 'completed'
    tool_calls: bool = False


class FakeProvider:
    """Inert deterministic adapter; synthetic usage has no monetary meaning."""
    mode = 'offline-fake'

    def __init__(self, replies=None):
        self.replies = list(replies) if replies is not None else [
            ProviderReply('{"recommendation":"deny","reason":"Offline fake response"}', 1)]
        self.calls = []

    def generate(self, model_input, max_output_tokens):
        self.calls.append({'input': json.loads(json.dumps(model_input)), 'max_output_tokens': max_output_tokens})
        reply = self.replies.pop(0)
        if isinstance(reply, BaseException):
            raise reply
        return reply


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate JSON key')
        result[key] = value
    return result


def _proposal(reply):
    if (not isinstance(reply, ProviderReply) or reply.status != 'completed'
            or reply.tool_calls is not False or not isinstance(reply.output_text, str)):
        return None
    try:
        if len(reply.output_text.encode('utf-8')) > MAX_BYTES:
            return None
        result = json.loads(reply.output_text, object_pairs_hook=_unique_object)
        if not isinstance(result, dict) or set(result) != {'recommendation', 'reason'}:
            return None
        if result['recommendation'] not in ('approve', 'deny'):
            return None
        _text(result['reason'], 2048)
        return result
    except (ValueError, RecursionError):
        return None


def _bounded_raw_output(reply):
    if not isinstance(reply.output_text, str):
        return None
    try:
        return reply.output_text if len(reply.output_text.encode('utf-8')) <= MAX_BYTES else None
    except UnicodeError:
        return None


class Gateway:
    def __init__(self, ledger: BudgetLedger, provider: FakeProvider):
        if not isinstance(provider, FakeProvider) or provider.mode != 'offline-fake':
            raise ValueError('this foundation implements offline fake mode only')
        self.ledger = ledger
        self.provider = provider

    def run(self, request_id: str, facts: dict, presentation: str, reserve_units: int,
            max_output_tokens: int = 512) -> dict:
        if self.provider.mode != 'offline-fake':
            raise ValueError('live activation is not implemented')
        payload = provider_input(facts, presentation)
        if type(max_output_tokens) is not int or not 1 <= max_output_tokens <= 4096:
            raise ValueError('invalid maximum output token count')
        self.ledger._reserve(request_id, reserve_units, model_input=payload, max_output_tokens=max_output_tokens)
        self.ledger.dispatch(request_id)
        base = {'mode': 'offline-fake', 'request_id': request_id, 'recommendation': None, 'reason': None}
        try:
            reply = self.provider.generate(payload, max_output_tokens)
        except Exception:
            result = {**base, 'status': 'provider_error'}
            self.ledger.uncertain(request_id, result=result)
            return result
        if not isinstance(reply, ProviderReply):
            result = {**base, 'status': 'accounting_error'}
            self.ledger.uncertain(request_id, result=result, outcome='accounting_error')
            return result
        if reply.status not in ('completed', 'incomplete', 'failed', 'cancelled'):
            result = {**base, 'status': 'provider_error'}
            self.ledger.uncertain(request_id, result=result)
            return result
        proposal = _proposal(reply)
        outcome = ('provider_error' if reply.status in ('failed', 'cancelled')
                   else 'completed' if proposal else 'invalid_output')
        result = {**base, 'status': outcome, **(proposal or {})}
        try:
            self.ledger.settle(request_id, reply.usage_units, outcome, result=result,
                               raw_output=_bounded_raw_output(reply))
        except BudgetError:
            return {**base, 'status': 'accounting_error'}
        return result
