"""Private SQLite accounting for the trusted host, not a hostile-process sandbox.

All money is integer nanodollars. Held units use decimal integer TEXT so a
known overrun beyond SQLite's signed 64-bit range remains representable; sums
use Python integers. Caps and ordinary settled charges fit SQLite INTEGER.
A reservation is a persistent liability, even
when the process dies before dispatch. Reconciliation is deliberately external;
this module never resets a hold, changes a cap, or migrates historical ledgers.
"""
from contextlib import contextmanager
from decimal import Decimal, InvalidOperation, ROUND_CEILING, localcontext
import hashlib
import json
import os
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

    def reserve(self, usd, *, request=None, authorization=None):
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
            self._audit(c, identity, 'reserved', {'reserved_units': amount})
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
