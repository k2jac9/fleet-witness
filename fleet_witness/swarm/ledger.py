"""Private SQLite accounting for the trusted host, not a hostile-process sandbox.

All money is integer nanodollars. Held units use decimal integer TEXT so a
known overrun beyond SQLite's signed 64-bit range remains representable; sums
use Python integers. Caps and ordinary settled charges fit SQLite INTEGER.
A reservation is a persistent liability, even
when the process dies before dispatch. Reconciliation is deliberately external;
this module never resets a hold, changes a cap, or rewrites historical rows.
Additive cohort tables retain the existing accounting schema and records.
"""
from contextlib import contextmanager
from decimal import Decimal, InvalidOperation, ROUND_CEILING, localcontext
import hashlib
import json
import os
import hmac
import re
import secrets
from pathlib import Path
import sqlite3
import stat
import time
import uuid

UNITS_PER_USD = 1_000_000_000
MAX_USD = Decimal('1000000')
MAX_LIABILITY_USD = Decimal('1e24')
DEFAULT_LIFETIME_CAP = {'adaption': 100, 'openrouter': 15, 'fake': 1000000}


class ProviderError(RuntimeError):
    def __init__(self, message, *, attempts=None, status='refused'):
        super().__init__(message)
        self.attempts = list(attempts or [])
        self.provider_attempts = sum(a.get('provider_attempts', 1) for a in self.attempts)
        self.held_usd = sum(a.get('held_usd', 0) for a in self.attempts)
        self.cost_usd = sum(a.get('cost_usd', 0) for a in self.attempts)
        self.status = status


class BudgetExceeded(ProviderError):
    pass


def decimal_usd(value, *, liability=False):
    if isinstance(value, bool) or not isinstance(value, (str, int, float, Decimal)):
        raise ValueError('money must be a nonnegative finite decimal')
    try:
        amount = Decimal(str(value))
    except InvalidOperation:
        raise ValueError('invalid money') from None
    if not amount.is_finite() or not 0 <= amount <= (MAX_LIABILITY_USD if liability else MAX_USD):
        raise ValueError('money outside supported bounds')
    return amount


def units(value, *, exact=False, liability=False):
    with localcontext() as context:
        context.prec = 100
        scaled = decimal_usd(value, liability=liability) * UNITS_PER_USD
        rounded = scaled.to_integral_value(rounding=ROUND_CEILING)
    if exact and scaled != rounded:
        raise ValueError('cap must use whole nanodollars')
    return int(rounded)


def dollars(value):
    return value / UNITS_PER_USD


def canonical_json(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False)


class Ledger:
    def __init__(self, provider, run_cap_usd, lifetime_cap_usd=None, path=None, *, run_id=None, tag=None):
        if provider not in DEFAULT_LIFETIME_CAP:
            raise ValueError('unknown provider')
        self.provider = provider
        self.run_id = run_id or uuid.uuid4().hex
        if not isinstance(self.run_id, str) or not 1 <= len(self.run_id) <= 128:
            raise ValueError('invalid run identity')
        self.tag = os.environ.get('FLEET_WITNESS_LEDGER_TAG', '') if tag is None else tag
        if not isinstance(self.tag, str) or len(self.tag.encode()) > 256:
            raise ValueError('invalid run tag')
        self._run_cap = units(run_cap_usd, exact=True)
        self._provider_cap = units(DEFAULT_LIFETIME_CAP[provider] if lifetime_cap_usd is None else lifetime_cap_usd, exact=True)
        requested = Path(path).absolute()
        if requested.is_symlink() or requested.parent.resolve() != requested.parent:
            raise BudgetExceeded('ledger symlinks are forbidden')
        self.path = requested.resolve()
        self._check_legacy()
        self.path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        parent = self.path.parent.stat()
        if stat.S_IMODE(parent.st_mode) & 0o077 or parent.st_uid != os.getuid():
            raise BudgetExceeded('ledger directory must be owner-private')
        fd = os.open(self.path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600)
        try:
            info = os.fstat(fd)
            if (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or
                    info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) & 0o077):
                raise BudgetExceeded('ledger must be an owner-private regular file')
        finally:
            os.close(fd)
        with self._transaction() as c:
            for statement in (
                'CREATE TABLE IF NOT EXISTS providers(provider TEXT PRIMARY KEY, cap INTEGER NOT NULL)',
                'CREATE TABLE IF NOT EXISTS runs(run_id TEXT PRIMARY KEY, provider TEXT NOT NULL, cap INTEGER NOT NULL, tag TEXT NOT NULL)',
                'CREATE TABLE IF NOT EXISTS run_authority(run_id TEXT PRIMARY KEY, envelope TEXT NOT NULL)',
                'CREATE TABLE IF NOT EXISTS authorizations(id TEXT PRIMARY KEY, data TEXT NOT NULL)',
                '''CREATE TABLE IF NOT EXISTS requests(
                    id TEXT PRIMARY KEY, run_id TEXT NOT NULL, provider TEXT NOT NULL,
                    authorization_id TEXT, status TEXT NOT NULL, reserved INTEGER NOT NULL,
                    held TEXT NOT NULL, settled INTEGER NOT NULL DEFAULT 0,
                    created REAL NOT NULL, dispatched REAL, request_json TEXT,
                    response_raw BLOB, receipt_json TEXT)''',
                'CREATE TABLE IF NOT EXISTS audit(seq INTEGER PRIMARY KEY, request_id TEXT, kind TEXT NOT NULL, data TEXT NOT NULL)',
                '''CREATE TABLE IF NOT EXISTS cohorts(run_id TEXT PRIMARY KEY, authorization_json TEXT NOT NULL,
                    plan_sha256 TEXT NOT NULL, output_dir TEXT NOT NULL UNIQUE, token_sha256 TEXT NOT NULL,
                    status TEXT NOT NULL)''',
                '''CREATE TABLE IF NOT EXISTS cohort_calls(call_id TEXT PRIMARY KEY, run_id TEXT NOT NULL,
                    position INTEGER NOT NULL, request_sha256 TEXT NOT NULL, attempt_id TEXT UNIQUE,
                    completed INTEGER NOT NULL DEFAULT 0, UNIQUE(run_id,position))''',
            ):
                c.execute(statement)
            row = c.execute('SELECT cap FROM providers WHERE provider=?', (provider,)).fetchone()
            if row is None:
                c.execute('INSERT INTO providers VALUES(?,?)', (provider, self._provider_cap))
                self._audit(c, None, 'provider_created', {'provider': provider, 'cap_units': self._provider_cap})
            elif row['cap'] != self._provider_cap:
                raise BudgetExceeded('provider cap is immutable; operator reconciliation required')
            row = c.execute('SELECT * FROM runs WHERE run_id=?', (self.run_id,)).fetchone()
            if row is None:
                c.execute('INSERT INTO runs VALUES(?,?,?,?)', (self.run_id, provider, self._run_cap, self.tag))
                self._audit(c, None, 'run_created', {'run_id': self.run_id})
            elif (row['provider'], row['cap'], row['tag']) != (provider, self._run_cap, self.tag):
                raise BudgetExceeded('run identity/cap/tag cannot change')

    def _check_legacy(self):
        if self.path.suffix.lower() == '.json' or any(self.path.parent.glob('spend-ledger*.json')):
            raise BudgetExceeded('historical JSON ledger requires explicit operator reconciliation; preserved unchanged')

    @contextmanager
    def _transaction(self):
        self._check_legacy()
        c = sqlite3.connect(self.path, timeout=5, isolation_level=None)
        c.row_factory = sqlite3.Row
        try:
            c.execute('PRAGMA synchronous=FULL')
            c.execute('BEGIN IMMEDIATE')
            yield c
            c.commit()
        except BaseException:
            c.rollback()
            raise
        finally:
            c.close()

    @staticmethod
    def _audit(c, request_id, kind, data):
        c.execute('INSERT INTO audit(request_id,kind,data) VALUES(?,?,?)', (request_id, kind, canonical_json(data)))

    def _totals(self, c, where, value):
        rows = c.execute(f'SELECT settled,held,dispatched FROM requests WHERE {where}=?', (value,))
        totals = {'settled': 0, 'held': 0, 'attempts': 0}
        for row in rows:
            totals['settled'] += row['settled']
            totals['held'] += int(row['held'])
            totals['attempts'] += row['dispatched'] is not None
        return totals

    def _check_caps(self, c):
        provider = c.execute('SELECT cap FROM providers WHERE provider=?', (self.provider,)).fetchone()
        run = c.execute('SELECT cap FROM runs WHERE run_id=?', (self.run_id,)).fetchone()
        if provider is None or run is None or provider[0] != self._provider_cap or run[0] != self._run_cap:
            raise BudgetExceeded('persisted caps changed unexpectedly')

    def claim_cohort(self, authorization, calls, *, plan_sha256, output_dir):
        """Consume a cohort once; the session capability is never persisted in clear."""
        if (authorization.get('schema_version') != 'controlled-openrouter-pilot-v1' or
                authorization.get('run_id') != self.run_id or len(calls) != 160 or
                not isinstance(plan_sha256, str) or not re.fullmatch(r'[0-9a-f]{64}', plan_sha256) or
                not Path(output_dir).is_absolute() or str(Path(output_dir).resolve()) != output_dir):
            raise BudgetExceeded('invalid cohort claim')
        for call in calls:
            if (set(call) != {'call_id', 'request_sha256'} or
                    not re.fullmatch(r'[0-9a-f]{32}', call['call_id']) or
                    not re.fullmatch(r'[0-9a-f]{64}', call['request_sha256'])):
                raise BudgetExceeded('invalid scheduled call')
        if len({c['call_id'] for c in calls}) != 160:
            raise BudgetExceeded('duplicate scheduled call')
        token = secrets.token_hex(32)
        with self._transaction() as c:
            self._check_caps(c)
            if (c.execute('SELECT 1 FROM cohorts WHERE run_id=? OR output_dir=?', (self.run_id, output_dir)).fetchone() or
                    c.execute('SELECT 1 FROM requests WHERE run_id=?', (self.run_id,)).fetchone()):
                raise BudgetExceeded('cohort already consumed; recovery is export-only')
            if c.execute("SELECT 1 FROM requests WHERE status IN ('reserved','dispatched','unresolved','overrun') LIMIT 1").fetchone():
                raise BudgetExceeded('unresolved liability blocks cohort')
            pricing = authorization['pricing']
            bound = ((6 * authorization['max_input_bytes'] + 4096) * decimal_usd(pricing['input_per_million']) +
                     authorization['max_output_tokens'] * decimal_usd(pricing['output_per_million'])) / Decimal(1000000)
            for field, value, cap in (('run_id', self.run_id, self._run_cap), ('provider', self.provider, self._provider_cap)):
                totals = self._totals(c, field, value)
                if totals['settled'] + totals['held'] + units(bound) * 160 > cap:
                    raise BudgetExceeded('whole cohort exceeds remaining budget')
            c.execute('INSERT INTO cohorts VALUES(?,?,?,?,?,?)', (self.run_id, canonical_json(authorization),
                      plan_sha256, output_dir, hashlib.sha256(token.encode()).hexdigest(), 'active'))
            c.executemany('INSERT INTO cohort_calls(call_id,run_id,position,request_sha256) VALUES(?,?,?,?)',
                          [(call['call_id'], self.run_id, i, call['request_sha256']) for i, call in enumerate(calls)])
            self._audit(c, None, 'cohort_claimed', {'run_id': self.run_id, 'plan_sha256': plan_sha256,
                                                  'output_dir': output_dir, 'scheduled_calls': 160})
        return token

    def _cohort(self, c, token):
        row = c.execute('SELECT * FROM cohorts WHERE run_id=?', (self.run_id,)).fetchone()
        if (row is None or row['status'] != 'active' or not isinstance(token, str) or
                not hmac.compare_digest(row['token_sha256'], hashlib.sha256(token.encode()).hexdigest())):
            raise BudgetExceeded('active cohort capability required; no resume')
        return row

    def _cohort_call(self, c, authorization, call_id, token, request):
        row = self._cohort(c, token)
        if row['authorization_json'] != canonical_json(authorization):
            raise BudgetExceeded('cohort authorization changed')
        call = c.execute('SELECT * FROM cohort_calls WHERE run_id=? AND call_id=?', (self.run_id, call_id)).fetchone()
        if (call is None or call['attempt_id'] is not None or
                call['request_sha256'] != hashlib.sha256(canonical_json(request).encode()).hexdigest()):
            raise BudgetExceeded('scheduled request mismatch or already attempted')
        if c.execute('''SELECT 1 FROM cohort_calls cc LEFT JOIN requests r ON r.id=cc.attempt_id
                WHERE cc.run_id=? AND cc.position<? AND
                (cc.completed=0 OR r.status IS NULL OR r.status!='succeeded') LIMIT 1''',
                     (self.run_id, call['position'])).fetchone():
            raise BudgetExceeded('earlier scheduled call incomplete or failed')

    def validate_cohort_call(self, authorization, call_id, token, request):
        with self._transaction() as c:
            self._cohort_call(c, authorization, call_id, token, request)

    def finish_cohort_call(self, call_id, token):
        with self._transaction() as c:
            self._cohort(c, token)
            row = c.execute('''SELECT cc.completed,r.status FROM cohort_calls cc
                JOIN requests r ON r.id=cc.attempt_id WHERE cc.run_id=? AND cc.call_id=?''',
                (self.run_id, call_id)).fetchone()
            if row is None or row['completed'] or row['status'] != 'succeeded':
                raise BudgetExceeded('only successful uncheckpointed calls can complete')
            c.execute('UPDATE cohort_calls SET completed=1 WHERE call_id=?', (call_id,))
            self._audit(c, None, 'cohort_call_completed', {'run_id': self.run_id, 'call_id': call_id})

    def stop_cohort(self, token, reason):
        with self._transaction() as c:
            self._cohort(c, token)
            c.execute("UPDATE cohorts SET status='closed' WHERE run_id=?", (self.run_id,))
            self._audit(c, None, 'cohort_closed', {'run_id': self.run_id, 'reason': reason})

    def reserve(self, usd, *, request=None, authorization=None, call_id=None, cohort_token=None):
        amount = units(usd)
        request_json = canonical_json(request or {})
        if len(request_json.encode()) > 2_000_000:
            raise ValueError('request receipt exceeds limit')
        with self._transaction() as c:
            self._check_caps(c)
            if c.execute("SELECT 1 FROM requests WHERE status IN ('reserved','dispatched','unresolved','overrun') LIMIT 1").fetchone():
                raise BudgetExceeded('unresolved or in-flight request blocks dispatch')
            for field, value, cap in (('run_id', self.run_id, self._run_cap), ('provider', self.provider, self._provider_cap)):
                totals = self._totals(c, field, value)
                if totals['settled'] + totals['held'] + amount > cap:
                    raise BudgetExceeded(f'{field} budget exhausted')
            claimed = c.execute('SELECT 1 FROM cohorts WHERE run_id=?', (self.run_id,)).fetchone()
            pilot = authorization is not None and authorization.get('schema_version') == 'controlled-openrouter-pilot-v1'
            if claimed or pilot:
                self._cohort_call(c, authorization, call_id, cohort_token, request)
            elif call_id is not None or cohort_token is not None:
                raise BudgetExceeded('scheduled context requires a pilot claim')
            auth_id = None
            if authorization is not None:
                envelope = {field: authorization[field] for field in
                            ('request_limit', 'expires_at', 'source_commit', 'source_sha256', 'purpose')}
                encoded_envelope = canonical_json(envelope)
                shared = c.execute('SELECT envelope FROM run_authority WHERE run_id=?', (self.run_id,)).fetchone()
                if shared is None:
                    c.execute('INSERT INTO run_authority VALUES(?,?)', (self.run_id, encoded_envelope))
                    self._audit(c, None, 'run_authority_bound', {'run_id': self.run_id, **envelope})
                elif shared['envelope'] != encoded_envelope:
                    raise BudgetExceeded('shared run request/source/deadline envelope is immutable')
                run_count = c.execute('SELECT COUNT(*) FROM requests WHERE run_id=?', (self.run_id,)).fetchone()[0]
                if time.time() >= envelope['expires_at'] or run_count >= envelope['request_limit']:
                    raise BudgetExceeded('shared run expired or request limit exhausted')
                auth_id = authorization['authorization_id']
                data = canonical_json(authorization)
                prior = c.execute('SELECT data FROM authorizations WHERE id=?', (auth_id,)).fetchone()
                if prior is None:
                    c.execute('INSERT INTO authorizations VALUES(?,?)', (auth_id, data))
                elif prior['data'] != data:
                    raise BudgetExceeded('authorization cannot change implicitly')
                count = c.execute('SELECT COUNT(*) FROM requests WHERE authorization_id=?', (auth_id,)).fetchone()[0]
                if time.time() >= authorization['expires_at'] or count >= authorization['request_limit']:
                    raise BudgetExceeded('authorization expired or request limit exhausted')
            identity = uuid.uuid4().hex
            c.execute('''INSERT INTO requests(id,run_id,provider,authorization_id,status,reserved,held,created,request_json)
                VALUES(?,?,?,?,?,?,?,?,?)''', (identity, self.run_id, self.provider, auth_id, 'reserved', amount, amount, time.time(), request_json))
            if pilot:
                c.execute('UPDATE cohort_calls SET attempt_id=? WHERE run_id=? AND call_id=?',
                          (identity, self.run_id, call_id))
            self._audit(c, identity, 'reserved', {'reserved_units': amount,
                                                **({'call_id': call_id} if pilot else {})})
            return identity

    def dispatch(self, identity):
        with self._transaction() as c:
            self._check_caps(c)
            row = self._request(c, identity)
            if row['status'] != 'reserved':
                raise BudgetExceeded('request already dispatched or terminal')
            if row['authorization_id']:
                auth = json.loads(c.execute('SELECT data FROM authorizations WHERE id=?', (row['authorization_id'],)).fetchone()[0])
                if time.time() >= auth['expires_at']:
                    raise BudgetExceeded('authorization expired before dispatch')
            c.execute("UPDATE requests SET status='dispatched',dispatched=? WHERE id=?", (time.time(), identity))
            self._audit(c, identity, 'dispatched', {})

    def _request(self, c, identity):
        row = c.execute('SELECT * FROM requests WHERE id=? AND run_id=?', (identity, self.run_id)).fetchone()
        if row is None:
            raise BudgetExceeded('unknown reservation')
        return row

    def request_state(self, identity):
        """Read detached canonical accounting for one request, without a transition."""
        with self._transaction() as c:
            row = self._request(c, identity)
            return {'status': row['status'], 'provider_attempts': int(row['dispatched'] is not None),
                    'receipt': json.loads(row['receipt_json']) if row['receipt_json'] is not None else None}

    def settle(self, identity, actual, *, status='succeeded', receipt=None, response_raw=None):
        """Known overspend remains an unresolved liability, never a clipped charge."""
        amount = units(actual, liability=True)
        with self._transaction() as c:
            row = self._request(c, identity)
            if row['status'] not in ('reserved', 'dispatched'):
                raise BudgetExceeded('reservation already terminal; reconciliation required')
            overrun = amount > row['reserved']
            final_status = 'overrun' if overrun else status
            held, settled = (amount, 0) if overrun else (0, amount)
            self._finish(c, row, final_status, held, settled, receipt, response_raw)

    def hold(self, identity, *, liability=None, receipt=None, response_raw=None, status='unresolved'):
        with self._transaction() as c:
            row = self._request(c, identity)
            if row['status'] not in ('reserved', 'dispatched'):
                raise BudgetExceeded('reservation already terminal; reconciliation required')
            amount = max(row['reserved'], units(liability, liability=True) if liability is not None else 0)
            self._finish(c, row, status, amount, 0, receipt, response_raw)

    def _finish(self, c, row, status, held, settled, receipt, raw):
        if raw is not None and (not isinstance(raw, bytes) or len(raw) > 1_048_577):
            raise ValueError('invalid bounded response receipt')
        encoded = canonical_json(receipt or {})
        if len(encoded.encode()) > 65536:
            raise ValueError('receipt metadata exceeds limit')
        c.execute('UPDATE requests SET status=?,held=?,settled=?,response_raw=?,receipt_json=? WHERE id=?',
                  (status, str(held), settled, raw, encoded, row['id']))
        self._audit(c, row['id'], status, {'held_units': held, 'settled_units': settled,
                    'response_sha256': hashlib.sha256(raw).hexdigest() if raw is not None else None})

    def snapshot(self):
        with self._transaction() as c:
            self._check_caps(c)
            def entry(field, identity, cap):
                row = self._totals(c, field, identity)
                return {'settled_usd': dollars(row['settled']), 'held_usd': dollars(row['held']),
                        'cap_usd': dollars(cap), 'provider_attempts': row['attempts']}
            return {'run_id': self.run_id, 'path': str(self.path),
                    'run': entry('run_id', self.run_id, self._run_cap),
                    'provider': entry('provider', self.provider, self._provider_cap),
                    'halted': bool(c.execute("SELECT 1 FROM requests WHERE status IN ('reserved','dispatched','unresolved','overrun') LIMIT 1").fetchone())}

    @property
    def run_cap(self):
        return dollars(self._run_cap)

    @property
    def lifetime_cap(self):
        return dollars(self._provider_cap)

    @property
    def run_spent(self):
        return self.snapshot()['run']['settled_usd']

    @property
    def run_reserved(self):
        return self.snapshot()['run']['held_usd']

    @property
    def calls(self):
        return self.snapshot()['run']['provider_attempts']

    def lifetime_spent(self):
        return self.snapshot()['provider']['settled_usd']
