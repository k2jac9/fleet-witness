"""Offline-only single-use authorization registry fixture.

This is not a production activation gate. A live entry point must pin one
canonical registry, verify actual account and source identities, bind its ledger,
and complete all ADR-0010 prerequisites before accessing a provider.
"""
from contextlib import closing, contextmanager
import json
import os
from pathlib import Path
import re
import sqlite3
import stat


MODE = 'offline-authorization-fixture'


def _id(value):
    if not isinstance(value, str) or not re.fullmatch(r'[0-9a-f]{32}', value):
        raise ValueError('invalid fixture authorization identity')


def _private_parent(path):
    parent = path.parent.lstat()
    if (not stat.S_ISDIR(parent.st_mode) or parent.st_uid != os.getuid()
            or stat.S_IMODE(parent.st_mode) & 0o077):
        raise ValueError('parent must be an owner-private directory')


def _ledger_path(value):
    if not isinstance(value, (str, Path)):
        raise ValueError('invalid ledger path')
    path = Path(value)
    if not path.is_absolute() or str(path) != str(path.resolve(strict=False)):
        raise ValueError('ledger path must be absolute and contain no symlinks')
    _private_parent(path)
    return str(path)


class FixtureRegistry:
    """Single-use records inside one private registry; fixture mode only."""
    def __init__(self, path):
        self.path = Path(path)
        if not self.path.is_absolute() or str(self.path) != str(self.path.resolve(strict=False)):
            raise ValueError('registry path must be absolute and contain no symlinks')
        _private_parent(self.path)
        fd = os.open(self.path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600)
        try:
            metadata = os.fstat(fd)
            if (not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1
                    or metadata.st_uid != os.getuid() or stat.S_IMODE(metadata.st_mode) & 0o077):
                raise ValueError('registry must be an owner-private singly-linked regular file')
        finally:
            os.close(fd)
        with closing(self._connect()) as c:
            c.executescript('''
                CREATE TABLE IF NOT EXISTS authorizations (
                    id TEXT PRIMARY KEY, account_id TEXT NOT NULL, source_commit TEXT NOT NULL,
                    ledger_path TEXT NOT NULL, status TEXT NOT NULL CHECK(status IN ('claimed','consumed')));
                CREATE TABLE IF NOT EXISTS audit (
                    seq INTEGER PRIMARY KEY AUTOINCREMENT, authorization_id TEXT NOT NULL,
                    kind TEXT NOT NULL CHECK(kind IN ('claimed','consumed')));
            ''')

    def _connect(self):
        c = sqlite3.connect(self.path, timeout=15)
        c.row_factory = sqlite3.Row
        return c

    @contextmanager
    def _transaction(self):
        with closing(self._connect()) as c, c:
            c.execute('BEGIN IMMEDIATE')
            yield c

    def claim(self, authorization_id, account_id, source_commit, ledger_path):
        _id(authorization_id)
        if not isinstance(account_id, str) or not re.fullmatch(r'[A-Za-z0-9._:-]{1,128}', account_id):
            raise ValueError('invalid fixture account identity')
        if not isinstance(source_commit, str) or not re.fullmatch(r'[0-9a-f]{40}', source_commit):
            raise ValueError('invalid source commit identity')
        ledger = _ledger_path(ledger_path)
        with self._transaction() as c:
            if c.execute('SELECT id FROM authorizations WHERE id=?', (authorization_id,)).fetchone():
                raise ValueError('fixture authorization identity already claimed')
            c.execute('INSERT INTO authorizations VALUES(?,?,?,?,?)',
                      (authorization_id, account_id, source_commit, ledger, 'claimed'))
            c.execute('INSERT INTO audit(authorization_id,kind) VALUES(?,?)', (authorization_id, 'claimed'))

    def consume(self, authorization_id):
        self._consume(authorization_id)

    def _consume(self, authorization_id, expected=None):
        _id(authorization_id)
        with self._transaction() as c:
            row = c.execute('SELECT * FROM authorizations WHERE id=?', (authorization_id,)).fetchone()
            if row is None or row['status'] != 'claimed':
                raise ValueError('fixture authorization is missing or already consumed')
            if expected is not None and (row['account_id'], row['source_commit'], row['ledger_path']) != expected:
                raise ValueError('fixture authorization binding mismatch')
            c.execute("UPDATE authorizations SET status='consumed' WHERE id=?", (authorization_id,))
            c.execute('INSERT INTO audit(authorization_id,kind) VALUES(?,?)', (authorization_id, 'consumed'))

    def snapshot(self, authorization_id):
        _id(authorization_id)
        with closing(self._connect()) as c:
            row = c.execute('SELECT * FROM authorizations WHERE id=?', (authorization_id,)).fetchone()
        if row is None:
            return None
        result = dict(row)
        result['authorization_id'] = result.pop('id')
        result['mode'] = MODE
        return result


class BoundFixtureRunner:
    """Bind a synthetic claim to a strictly inert runner; never a live gate."""
    def __init__(self, registry, runner, authorization_id, account_id, source_commit):
        from fleet_witness.live_gateway import FixtureRunner
        if type(registry) is not FixtureRegistry or type(runner) is not FixtureRunner:
            raise ValueError('only the offline fixture registry and runner are supported')
        _id(authorization_id)
        if not isinstance(account_id, str) or not re.fullmatch(r'[A-Za-z0-9._:-]{1,128}', account_id):
            raise ValueError('invalid fixture account identity')
        if not isinstance(source_commit, str) or not re.fullmatch(r'[0-9a-f]{40}', source_commit):
            raise ValueError('invalid source commit identity')
        self.registry, self.runner = registry, runner
        self.authorization_id, self.account_id, self.source_commit = authorization_id, account_id, source_commit

    def run(self, request_id, facts, presentation):
        from fleet_witness.live_gateway import _request_id, build_provider_request
        _request_id(request_id)
        request = build_provider_request(facts, presentation)
        visible = json.loads(request['input'])
        ledger = _ledger_path(self.runner.ledger.path)
        self.registry._consume(self.authorization_id, (self.account_id, self.source_commit, ledger))
        return self.runner.run(request_id, visible['facts'], presentation)
