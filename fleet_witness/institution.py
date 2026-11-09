"""Separation-of-powers kernel for agent swarms: verify the institution, not the agents.

Branches:
- Legislature: the operator sets versioned release policy (`set_policy`).
- Proposers: the swarm votes; only the tally is recorded (`record_proposal`).
- Auditors (judiciary): a committee of m agents, seated by the kernel, attests that a
  release is safe. Each attestation is signed with that auditor's own key.
- Executive: only `execute` creates an effect, and only if every check passes,
  committing the release and its audit event in one SQLite transaction.

What the kernel checks mechanically: proposal majority, current policy, evidence
integrity (HMAC), k distinct *seated* auditors with valid attestations for this exact
run/artifact, and at most one release per case. What it deliberately does NOT check:
whether the evidence semantically establishes safety. That judgement is delegated to
auditors, which is exactly where a colluding cell can attack the institution.

The kernel's invariants are checked exhaustively over bounded worlds by
`fleet_witness.verify_institution`.
"""
from contextlib import closing
import hashlib
import hmac
import json
import sqlite3

from .evidence import FIELDS, _payload

ATTESTATION_FIELDS = ('auditor', 'claim', 'run_id', 'artifact_digest')

SCHEMA = '''
CREATE TABLE IF NOT EXISTS policy (case_id TEXT PRIMARY KEY, allowed INTEGER NOT NULL, version INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS cases (case_id TEXT PRIMARY KEY, run_id TEXT NOT NULL, artifact_digest TEXT NOT NULL,
  evidence TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS seats (case_id TEXT NOT NULL, auditor TEXT NOT NULL, PRIMARY KEY(case_id, auditor));
CREATE TABLE IF NOT EXISTS proposals (case_id TEXT PRIMARY KEY, approvals INTEGER NOT NULL, denials INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS attestations (case_id TEXT NOT NULL, auditor TEXT NOT NULL, body TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS attempts (id TEXT PRIMARY KEY, case_id TEXT NOT NULL, effect INTEGER NOT NULL,
  reason TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS releases (case_id TEXT PRIMARY KEY, attempt_id TEXT NOT NULL UNIQUE);
CREATE TABLE IF NOT EXISTS audit (seq INTEGER PRIMARY KEY AUTOINCREMENT, case_id TEXT, kind TEXT NOT NULL,
  detail TEXT NOT NULL);
'''


def sign_attestation(key: bytes, auditor: str, run_id: str, artifact_digest: str) -> dict:
    body = {'auditor': auditor, 'claim': 'release_safe', 'run_id': run_id, 'artifact_digest': artifact_digest}
    return dict(body, signature=hmac.new(key, _canonical(body), hashlib.sha256).hexdigest())


def _canonical(body: dict) -> bytes:
    return json.dumps({name: body[name] for name in ATTESTATION_FIELDS}, sort_keys=True,
                      separators=(',', ':')).encode()


class Institution:
    """`mutations` exists only so the bounded checker can show it catches broken kernels."""

    def __init__(self, conn: sqlite3.Connection, *, evidence_key: bytes, auditor_keys: dict[str, bytes],
                 quorum: int, committee_size: int, require_majority: bool = True,
                 mutations: frozenset = frozenset()):
        """require_majority=False: a single proposer suffices; the committee alone authorizes."""
        if not 1 <= quorum <= committee_size:
            raise ValueError('need 1 <= quorum <= committee_size')
        self.conn, self.evidence_key, self.auditor_keys = conn, evidence_key, dict(auditor_keys)
        self.quorum, self.committee_size, self.mutations = quorum, committee_size, frozenset(mutations)
        self.require_majority = require_majority
        conn.executescript(SCHEMA)

    @classmethod
    def open(cls, path, **kwargs):
        conn = sqlite3.connect(path, timeout=15, isolation_level=None)
        return cls(conn, **kwargs)

    def _audit(self, case_id, kind, detail):
        self.conn.execute('INSERT INTO audit(case_id,kind,detail) VALUES(?,?,?)',
                          (case_id, kind, json.dumps(detail, sort_keys=True)))

    def _tx(self):
        self.conn.execute('BEGIN IMMEDIATE')
        return _Tx(self.conn)

    # Legislature -----------------------------------------------------------------
    def set_policy(self, case_id: str, allowed: bool):
        with self._tx():
            self.conn.execute('''INSERT INTO policy VALUES(?,?,1) ON CONFLICT(case_id) DO UPDATE SET
                                 allowed=excluded.allowed, version=policy.version+1''', (case_id, int(allowed)))
            self._audit(case_id, 'policy', {'allowed': allowed})

    # Case registration and committee seating (kernel-controlled) ----------------
    def open_case(self, case_id: str, run_id: str, artifact_digest: str, evidence: list, seats: list[str]):
        if len(set(seats)) != self.committee_size or not set(seats) <= set(self.auditor_keys):
            raise ValueError('committee must be distinct registered auditors of the configured size')
        with self._tx():
            self.conn.execute('INSERT INTO cases VALUES(?,?,?,?)',
                              (case_id, run_id, artifact_digest, json.dumps(evidence)))
            self.conn.executemany('INSERT INTO seats VALUES(?,?)', [(case_id, seat) for seat in seats])
            self._audit(case_id, 'opened', {'seats': sorted(seats)})

    # Proposers --------------------------------------------------------------------
    def record_proposal(self, case_id: str, approvals: int, denials: int):
        with self._tx():
            self.conn.execute('INSERT INTO proposals VALUES(?,?,?)', (case_id, approvals, denials))
            self._audit(case_id, 'proposal', {'approvals': approvals, 'denials': denials})

    # Auditors ---------------------------------------------------------------------
    def submit_attestation(self, case_id: str, attestation: dict):
        """Anyone may submit anything; validity is decided only at execution time."""
        with self._tx():
            self.conn.execute('INSERT INTO attestations VALUES(?,?,?)',
                              (case_id, str(attestation.get('auditor')), json.dumps(attestation, sort_keys=True)))
            self._audit(case_id, 'attestation_submitted', {'auditor': attestation.get('auditor')})

    # Checks ---------------------------------------------------------------------------
    def _evidence_intact(self, evidence: list) -> bool:
        if 'skip_integrity' in self.mutations:
            return True
        for receipt in evidence:
            if not isinstance(receipt, dict) or set(receipt) != FIELDS | {'signature'}:
                return False
            expected = hmac.new(self.evidence_key, _payload({n: receipt[n] for n in FIELDS}),
                                hashlib.sha256).hexdigest()
            if not hmac.compare_digest(expected, str(receipt['signature'])):
                return False
        return bool(evidence)

    def _valid_attesters(self, case_id: str, run_id: str, digest: str):
        """Distinct seated auditors with a valid, bound attestation (a list under the duplicate mutation)."""
        seated = {row[0] for row in self.conn.execute('SELECT auditor FROM seats WHERE case_id=?', (case_id,))}
        seen = []
        for (body,) in self.conn.execute('SELECT body FROM attestations WHERE case_id=?', (case_id,)):
            attestation = json.loads(body)
            auditor = attestation.get('auditor')
            key = self.auditor_keys.get(auditor)
            if key is None or not all(isinstance(attestation.get(f), str) for f in ATTESTATION_FIELDS):
                continue
            if 'skip_seat_check' not in self.mutations and auditor not in seated:
                continue
            if 'skip_binding' not in self.mutations and (
                    attestation['run_id'] != run_id or attestation['artifact_digest'] != digest
                    or attestation['claim'] != 'release_safe'):
                continue
            expected = hmac.new(key, _canonical(attestation), hashlib.sha256).hexdigest()
            if not hmac.compare_digest(expected, str(attestation.get('signature'))):
                continue
            seen.append(auditor)
        return seen if 'count_duplicates' in self.mutations else set(seen)

    # Executive -------------------------------------------------------------------------
    def execute(self, case_id: str, attempt_id: str) -> dict:
        with self._tx():
            previous = self.conn.execute('SELECT effect, reason FROM attempts WHERE id=?', (attempt_id,)).fetchone()
            if previous:
                return {'effect': False, 'reason': 'attempt already processed', 'replay': True}
            case = self.conn.execute('SELECT run_id, artifact_digest, evidence FROM cases WHERE case_id=?',
                                     (case_id,)).fetchone()
            proposal = self.conn.execute('SELECT approvals, denials FROM proposals WHERE case_id=?',
                                         (case_id,)).fetchone()
            policy = self.conn.execute('SELECT allowed FROM policy WHERE case_id=?', (case_id,)).fetchone()
            reason = None
            if case is None:
                reason = 'unknown case'
            elif proposal is None or proposal[0] < 1 or (self.require_majority and proposal[0] <= proposal[1]):
                reason = 'no majority proposal' if self.require_majority else 'no proposal'
            elif 'skip_policy_recheck' not in self.mutations and (policy is None or not policy[0]):
                reason = 'policy missing or denies release'
            elif not self._evidence_intact(json.loads(case[2])):
                reason = 'evidence integrity failed'
            else:
                attesters = self._valid_attesters(case_id, case[0], case[1])
                if len(attesters) < self.quorum:
                    reason = f'only {len(attesters)} of {self.quorum} required auditor attestations'
                elif ('skip_uniqueness' not in self.mutations and
                      self.conn.execute('SELECT 1 FROM releases WHERE case_id=?', (case_id,)).fetchone()):
                    reason = 'already released; no duplicate effect'
            effect = reason is None
            reason = reason or 'all institutional checks passed'
            self.conn.execute('INSERT INTO attempts VALUES(?,?,?,?)', (attempt_id, case_id, int(effect), reason))
            if effect:
                if 'skip_uniqueness' in self.mutations:
                    self.conn.execute('INSERT OR IGNORE INTO releases VALUES(?,?)', (case_id + ':' + attempt_id,
                                                                                      attempt_id))
                else:
                    self.conn.execute('INSERT INTO releases VALUES(?,?)', (case_id, attempt_id))
            if 'skip_audit' not in self.mutations or not effect:
                self._audit(case_id, 'release' if effect else 'denied', {'attempt': attempt_id, 'reason': reason})
            return {'effect': effect, 'reason': reason}


class _Tx:
    def __init__(self, conn):
        self.conn = conn

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.conn.execute('ROLLBACK' if exc_type else 'COMMIT')
        return False
