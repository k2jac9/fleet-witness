"""Trusted transactional authority for local database releases.

A trial is an independent simulated world. A run names the shared trajectory
within that world; immutable receipts can therefore be reused by paired trials.
This is a logical boundary in one process, not protection against hostile code.
"""
from contextlib import closing
import json
from pathlib import Path
import sqlite3

from .evidence import verify_receipt

SCHEMA = '''
CREATE TABLE IF NOT EXISTS policies (
 trial_id TEXT NOT NULL, run_id TEXT NOT NULL, artifact_digest TEXT NOT NULL,
 allowed INTEGER NOT NULL CHECK(allowed IN (0,1)), version INTEGER NOT NULL,
 PRIMARY KEY(trial_id,run_id,artifact_digest));
CREATE TABLE IF NOT EXISTS decisions (
 id TEXT PRIMARY KEY, trial_id TEXT NOT NULL, run_id TEXT NOT NULL,
 artifact_digest TEXT NOT NULL, recommendation TEXT NOT NULL CHECK(recommendation IN ('approve','deny')),
 reason TEXT NOT NULL, receipts TEXT NOT NULL, policy_snapshot TEXT NOT NULL,
 supervisor_input TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS attempts (
 id TEXT PRIMARY KEY, decision_id TEXT NOT NULL REFERENCES decisions(id), trial_id TEXT NOT NULL,
 execution_authorized_at_attempt INTEGER NOT NULL CHECK(execution_authorized_at_attempt IN (0,1)),
 effect_occurred INTEGER NOT NULL CHECK(effect_occurred IN (0,1)), reason TEXT NOT NULL,
 policy_version INTEGER);
CREATE TABLE IF NOT EXISTS releases (
 id TEXT PRIMARY KEY, attempt_id TEXT NOT NULL UNIQUE REFERENCES attempts(id),
 decision_id TEXT NOT NULL REFERENCES decisions(id), trial_id TEXT NOT NULL,
 run_id TEXT NOT NULL, artifact_digest TEXT NOT NULL,
 UNIQUE(trial_id,run_id,artifact_digest));
CREATE TABLE IF NOT EXISTS events (
 seq INTEGER PRIMARY KEY AUTOINCREMENT, trial_id TEXT NOT NULL, decision_id TEXT,
 kind TEXT NOT NULL, actor TEXT NOT NULL, message TEXT NOT NULL, details TEXT NOT NULL);
'''


class Controller:
    def __init__(self, database: Path, key: bytes, trial_id: str = 'default'):
        if not key or not trial_id:
            raise ValueError('a trusted key and trial identity are required')
        self.database = Path(database)
        self._key = key
        self.trial_id = trial_id
        with closing(self._connect()) as conn:
            conn.executescript(SCHEMA)

    def _connect(self):
        conn = sqlite3.connect(self.database, timeout=15)
        conn.row_factory = sqlite3.Row
        conn.execute('PRAGMA foreign_keys=ON')
        return conn

    def _policy(self, conn, run_id, artifact_digest):
        row = conn.execute('SELECT allowed,version FROM policies WHERE trial_id=? AND run_id=? AND artifact_digest=?',
                           (self.trial_id, run_id, artifact_digest)).fetchone()
        return {'allowed': bool(row['allowed']), 'version': row['version']} if row else None

    def _event(self, conn, kind, message, decision_id=None, details=None, actor='controller'):
        conn.execute('INSERT INTO events(trial_id,decision_id,kind,actor,message,details) VALUES(?,?,?,?,?,?)',
                     (self.trial_id, decision_id, kind, actor, message, json.dumps(details or {})))

    def set_policy(self, run_id: str, artifact_digest: str, allowed: bool):
        with closing(self._connect()) as conn, conn:
            conn.execute('BEGIN IMMEDIATE')
            conn.execute('''INSERT INTO policies VALUES(?,?,?,?,1)
                ON CONFLICT(trial_id,run_id,artifact_digest) DO UPDATE SET
                allowed=excluded.allowed, version=policies.version+1''',
                (self.trial_id, run_id, artifact_digest, int(allowed)))
            policy = self._policy(conn, run_id, artifact_digest)
            self._event(conn, 'policy_updated', 'Current release permission updated',
                        details={'run_id': run_id, 'artifact_digest': artifact_digest, **policy})
            return policy

    def record_decision(self, decision_id: str, run_id: str, artifact_digest: str,
                        recommendation: str, reason: str, receipts: list,
                        supervisor_input: dict | None = None) -> dict:
        if recommendation not in ('approve', 'deny'):
            raise ValueError('unknown recommendation')
        with closing(self._connect()) as conn, conn:
            conn.execute('BEGIN IMMEDIATE')
            snapshot = self._policy(conn, run_id, artifact_digest)
            conn.execute('INSERT INTO decisions VALUES(?,?,?,?,?,?,?,?,?)',
                (decision_id, self.trial_id, run_id, artifact_digest, recommendation, reason,
                 json.dumps(receipts), json.dumps(snapshot), json.dumps(supervisor_input or {})))
            self._event(conn, 'decision_recorded', reason, decision_id,
                        {'recommendation': recommendation}, actor='scripted-supervisor')
            return {'id': decision_id, 'recommendation': recommendation, 'reason': reason,
                    'policy_snapshot': snapshot}

    @staticmethod
    def _attempt(row):
        return {'id': row['id'], 'execution_authorized_at_attempt': bool(row['execution_authorized_at_attempt']),
                'effect_occurred': bool(row['effect_occurred']), 'reason': row['reason'],
                'policy_version': row['policy_version']}

    def execute(self, decision_id: str, attempt_id: str) -> dict:
        """Recheck current authority, evidence, and idempotency under one write lock."""
        with closing(self._connect()) as conn, conn:
            conn.execute('BEGIN IMMEDIATE')
            decision = conn.execute('SELECT * FROM decisions WHERE id=? AND trial_id=?',
                                    (decision_id, self.trial_id)).fetchone()
            if decision is None:
                raise ValueError('unknown decision in this trial')
            previous = conn.execute('SELECT * FROM attempts WHERE id=?', (attempt_id,)).fetchone()
            if previous:
                if previous['decision_id'] != decision_id or previous['trial_id'] != self.trial_id:
                    raise ValueError('attempt identity already belongs to another decision')
                return self._attempt(previous)
            policy = self._policy(conn, decision['run_id'], decision['artifact_digest'])
            authorized = False
            reason = 'Supervisor did not recommend approval'
            if decision['recommendation'] == 'approve':
                if not policy or not policy['allowed']:
                    reason = 'Current policy is missing or denies release'
                else:
                    checks = [verify_receipt(receipt, self._key, decision['run_id'], decision['artifact_digest'])
                              for receipt in json.loads(decision['receipts'])]
                    authorized = any(ok for ok, _ in checks)
                    reason = 'Current policy and applicable evidence authorize release' if authorized else (
                        checks[0][1] if checks else 'No release-safety receipt')
            effect = False
            if authorized:
                exists = conn.execute('SELECT 1 FROM releases WHERE trial_id=? AND run_id=? AND artifact_digest=?',
                    (self.trial_id, decision['run_id'], decision['artifact_digest'])).fetchone()
                effect = exists is None
                if not effect:
                    reason = 'Already released in this trial; no duplicate effect'
            version = policy['version'] if policy else None
            conn.execute('INSERT INTO attempts VALUES(?,?,?,?,?,?,?)',
                         (attempt_id, decision_id, self.trial_id, int(authorized), int(effect), reason, version))
            if effect:
                conn.execute('INSERT INTO releases VALUES(?,?,?,?,?,?)',
                    ('release:' + attempt_id, attempt_id, decision_id, self.trial_id,
                     decision['run_id'], decision['artifact_digest']))
            self._event(conn, 'release_committed' if effect else 'execution_without_effect', reason,
                        decision_id, {'attempt_id': attempt_id, 'execution_authorized_at_attempt': authorized,
                                      'effect_occurred': effect, 'policy_version': version})
            return {'id': attempt_id, 'execution_authorized_at_attempt': authorized,
                    'effect_occurred': effect, 'reason': reason, 'policy_version': version}
