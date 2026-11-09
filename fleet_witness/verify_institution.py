"""Bounded exhaustive verification of the institution kernel, plus capture mathematics.

The checker explores every reachable state of the *real* kernel (real SQLite,
real HMAC) in a small world, breadth first, deduplicating states, up to a depth
bound. After every action it compares the kernel with an independently written
specification and checks global invariants:

  S1 safety:   an effect happens only if a majority proposal exists, current policy
               allows it, the evidence is intact, and >= quorum DISTINCT SEATED auditors
               gave valid attestations bound to this exact run/artifact.
  S2 liveness: if all of that holds and nothing was released yet, execution succeeds.
  S3 at most one release per case, whatever the attempt sequence.
  S4 every release has a matching audit event (same transaction).

This is bounded model checking, not a proof for all world sizes. To show that the
checker has teeth, `--mutants` re-runs it against deliberately broken kernels and
reports the shortest counterexample found for each.

Capture math: if each seat is filled uniformly without replacement from N agents of
which C collude, and honest auditors wrongly attest with independent probability eps,
then given S1 the probability an invalid release happens is exactly
P(colluding seats + honest errors >= quorum). Herding makes honest errors correlated,
which breaks the independence assumption; the swarm experiments measure that gap.
"""
import argparse
from collections import deque
from math import comb
import sqlite3
import time

from .evidence import issue_receipt
from .institution import Institution, sign_attestation

EVIDENCE_KEY = b'evidence-key-for-bounded-check'
AUDITORS = {name: f'key-{name}'.encode() for name in ('s1', 's2', 's3', 'x1')}
SEATS = ['s1', 's2', 's3']
RUN, DIGEST = 'run-R', 'sha256:artifact-A'
QUORUM = 2

ACTIONS = ['propose+', 'propose-', 'policy+', 'policy-', 'att:s1', 'att:s2', 'att:s3', 'att:x1',
           'forge:s1', 'wrong:s2', 'exec:a1', 'exec:a2']
MUTANTS = ['skip_policy_recheck', 'skip_integrity', 'skip_seat_check', 'skip_binding', 'count_duplicates',
           'skip_uniqueness', 'skip_audit']


def _new_kernel(intact: bool, mutations=frozenset(), require_majority=True):
    conn = sqlite3.connect(':memory:', isolation_level=None)
    kernel = Institution(conn, evidence_key=EVIDENCE_KEY, auditor_keys=AUDITORS, quorum=QUORUM,
                         committee_size=len(SEATS), require_majority=require_majority, mutations=mutations)
    receipt = issue_receipt(EVIDENCE_KEY, issuer='build-issuer', claim='build_succeeded', scope='build',
                            artifact_digest=DIGEST, run_id=RUN)
    if not intact:
        receipt['signature'] = '0' * 64
    kernel.open_case('C', RUN, DIGEST, [receipt], SEATS)
    return kernel


def _clone(kernel, mutations):
    conn = sqlite3.connect(':memory:', isolation_level=None)
    conn.deserialize(kernel.conn.serialize())
    return Institution(conn, evidence_key=EVIDENCE_KEY, auditor_keys=AUDITORS, quorum=QUORUM,
                       committee_size=len(SEATS), require_majority=kernel.require_majority, mutations=mutations)


def _apply(kernel, spec: dict, action: str):
    """Apply to kernel and to the independent spec. Returns (kernel_effect, spec_effect) for executes."""
    spec = dict(spec)
    kind, _, arg = action.partition(':')
    try:
        if kind in ('propose+', 'propose-'):
            kernel.record_proposal('C', *((3, 1) if kind == 'propose+' else (1, 3)))
        elif kind in ('policy+', 'policy-'):
            kernel.set_policy('C', kind == 'policy+')
        elif kind == 'att':
            kernel.submit_attestation('C', sign_attestation(AUDITORS[arg], arg, RUN, DIGEST))
        elif kind == 'forge':
            kernel.submit_attestation('C', dict(sign_attestation(AUDITORS[arg], arg, RUN, DIGEST), signature='f' * 64))
        elif kind == 'wrong':
            kernel.submit_attestation('C', sign_attestation(AUDITORS[arg], arg, RUN, 'sha256:other-artifact'))
    except sqlite3.IntegrityError:
        pass  # e.g. a second proposal: rejected, state unchanged
    # Spec update (written independently of the kernel code)
    if kind in ('propose+', 'propose-') and spec['proposal'] is None:
        spec['proposal'] = kind[-1]
    elif kind in ('policy+', 'policy-'):
        spec['policy'] = kind == 'policy+'
    elif kind == 'att' and arg in SEATS:
        spec['attesters'] = spec['attesters'] | {arg}
    if kind != 'exec':
        return spec, None
    result = kernel.execute('C', arg)
    if arg in spec['attempts']:
        expected = False
    else:
        spec['attempts'] = spec['attempts'] | {arg}
        proposed = spec['proposal'] == '+' if kernel.require_majority else spec['proposal'] is not None
        expected = (proposed and spec['policy'] is True and spec['intact']
                    and len(spec['attesters']) >= QUORUM and not spec['released'])
        if expected:
            spec['released'] = True
    return spec, (result['effect'], expected)


def _global_violations(kernel) -> list[str]:
    problems = []
    releases = kernel.conn.execute('SELECT COUNT(*) FROM releases').fetchone()[0]
    audited = kernel.conn.execute("SELECT COUNT(*) FROM audit WHERE kind='release'").fetchone()[0]
    if releases > 1:
        problems.append(f'S3 violated: {releases} releases for one case')
    if releases != audited:
        problems.append(f'S4 violated: {releases} releases but {audited} release audit events')
    return problems


def _fingerprint(kernel, spec) -> tuple:
    tables = []
    for table in ('policy', 'proposals', 'attestations', 'attempts', 'releases'):
        tables.append(tuple(sorted(map(tuple, kernel.conn.execute(f'SELECT * FROM {table}')))))
    tables.append(tuple(sorted(row[0] for row in kernel.conn.execute('SELECT kind FROM audit'))))
    return (tuple(tables), tuple(sorted((k, tuple(sorted(v)) if isinstance(v, frozenset) else v)
                                        for k, v in spec.items())))


def check(depth: int = 6, mutations=frozenset(), stop_at_first: bool = True, require_majority: bool = True) -> dict:
    started = time.monotonic()
    queue, seen, violations, transitions = deque(), set(), [], 0
    for intact in (True, False):
        kernel = _new_kernel(intact, mutations, require_majority)
        spec = {'intact': intact, 'proposal': None, 'policy': None, 'attesters': frozenset(),
                'attempts': frozenset(), 'released': False}
        queue.append((kernel, spec, ('evidence-intact' if intact else 'evidence-tampered',)))
        seen.add(_fingerprint(kernel, spec))
    while queue:
        kernel, spec, trace = queue.popleft()
        if len(trace) - 1 >= depth:
            continue
        for action in ACTIONS:
            child = _clone(kernel, mutations)
            new_spec, outcome = _apply(child, spec, action)
            transitions += 1
            new_trace = trace + (action,)
            problems = _global_violations(child)
            if outcome and outcome[0] and not outcome[1]:
                problems.append('S1 violated: kernel released when the specification forbids it')
            if outcome and not outcome[0] and outcome[1]:
                problems.append('S2 violated: kernel refused a release the specification allows')
            if problems:
                violations.append({'trace': list(new_trace), 'problems': problems})
                if stop_at_first:
                    return _summary(depth, mutations, seen, transitions, violations, started)
                continue
            key = _fingerprint(child, new_spec)
            if key not in seen:
                seen.add(key)
                queue.append((child, new_spec, new_trace))
    return _summary(depth, mutations, seen, transitions, violations, started)


def _summary(depth, mutations, seen, transitions, violations, started):
    return {'depth': depth, 'mutations': sorted(mutations), 'distinct_states': len(seen),
            'transitions_checked': transitions, 'violations': violations[:3],
            'verified': not violations, 'seconds': round(time.monotonic() - started, 2)}


# ---------------------------------------------------------------------------------
def capture_probability(agents: int, colluders: int, committee: int, quorum: int, honest_error: float = 0.0) -> float:
    """P(colluding seats + independent honest wrong attestations >= quorum), seats drawn without replacement."""
    total = 0.0
    for bad_seats in range(0, min(colluders, committee) + 1):
        p_seats = comb(colluders, bad_seats) * comb(agents - colluders, committee - bad_seats) / comb(agents, committee)
        honest = committee - bad_seats
        need = max(0, quorum - bad_seats)
        p_errors = sum(comb(honest, j) * honest_error ** j * (1 - honest_error) ** (honest - j)
                       for j in range(need, honest + 1))
        total += p_seats * p_errors
    return total


def main(argv=None):
    parser = argparse.ArgumentParser(description='Bounded exhaustive check of the institution kernel')
    parser.add_argument('--depth', type=int, default=6)
    parser.add_argument('--mutants', action='store_true', help='also check deliberately broken kernels')
    args = parser.parse_args(argv)
    for majority in (True, False):
        result = check(args.depth, require_majority=majority)
        label = 'hybrid (majority + quorum)' if majority else 'committee-only (quorum)'
        print(f"Kernel {label}: depth {result['depth']}, {result['distinct_states']} distinct states, "
              f"{result['transitions_checked']} transitions, {result['seconds']}s -> "
              + ('ALL INVARIANTS HOLD' if result['verified'] else f"VIOLATION {result['violations'][0]}"))
    if args.mutants:
        for mutant in MUTANTS:
            found = check(args.depth, frozenset({mutant}))
            if found['verified']:
                print(f'  mutant {mutant:<20} NOT caught within depth {args.depth}')
            else:
                v = found['violations'][0]
                print(f"  mutant {mutant:<20} caught: {v['problems'][0]}  trace={' > '.join(v['trace'])}")
    print('\nCapture probability, N=100 agents, by colluder share (honest error 0):')
    print('  share   1-of-1   2-of-3   3-of-5   4-of-7   7-of-7')
    for share in (0.05, 0.1, 0.2, 0.3, 0.4, 0.5):
        c = round(100 * share)
        row = [capture_probability(100, c, m, k) for m, k in ((1, 1), (3, 2), (5, 3), (7, 4), (7, 7))]
        print(f'  {share:>5.0%}  ' + '  '.join(f'{p:7.4f}' for p in row))


if __name__ == '__main__':
    main()
