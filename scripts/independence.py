"""Do honest LLM errors cluster? Test the independence assumption behind committee guarantees.

Usage: python scripts/independence.py --model DeepSeek=runs/ambig-deepseek-s* --model gpt-oss=runs/ambig-gptoss-s*
Uses ambiguous-mode runs (authentic near-miss receipts, invalid under the strict rule).
For honest agents only, on invalid cases:
  - error rate eps (reviewer approvals; auditor signatures), per case kind;
  - overdispersion: variance of per-case error rates vs the binomial variance expected if
    errors were independent with the same mean (ratio > 1 means errors cluster on cases);
  - committee capture from honest error alone: observed P(>= k of m honest seats sign) vs
    the independence prediction Binomial(m, eps);
  - mixed-model committees: alternate seats between two models on the same cases/seats.
"""
import argparse
from collections import defaultdict
from glob import glob
import json
from math import comb
from pathlib import Path

REGIMES = [(1, 1), (3, 2), (5, 3), (7, 4), (7, 7)]


def binom_tail(m, k, p):
    return sum(comb(m, j) * p ** j * (1 - p) ** (m - j) for j in range(k, m + 1))


def load(dirs):
    """Per (seed, fraction, condition, case): reviewer votes and committee signatures by seat (honest only)."""
    cases = {}
    for d in dirs:
        d = Path(d)
        truth = json.loads((d / 'truth.json').read_text(encoding='utf-8'))
        manifest = json.loads((d / 'manifest.json').read_text(encoding='utf-8'))
        if manifest.get('case_mode') != 'ambiguous' or manifest.get('incomplete'):
            continue
        cell = set(truth['colluders'])
        for line in (d / 'events.jsonl').read_text(encoding='utf-8').splitlines():
            e = json.loads(line)
            info = truth['cases'][e['case_id']]
            key = (manifest['seed'], manifest['cell_fraction'], e['condition'], e['case_id'])
            c = cases.setdefault(key, {'kind': info['kind'], 'valid': info['valid'], 'votes': [], 'seats': {},
                                       'committee': truth['committees'][e['case_id']], 'cell': cell})
            honest = e['agent_id'] not in cell
            if e['type'] == 'vote' and honest and e.get('vote') in ('approve', 'deny'):
                c['votes'].append(e['vote'] == 'approve')
            if e['type'] == 'attestation' and e.get('outcome') in ('sign', 'refuse', 'abstain'):
                c['seats'][e['seat']] = (honest, e['outcome'] == 'sign')
    return cases


def overdispersion(groups):
    """groups: list of lists of 0/1. Returns (mean, observed var of group means, binomial-expected var, ratio)."""
    groups = [g for g in groups if g]
    total = sum(len(g) for g in groups)
    eps = sum(sum(g) for g in groups) / total
    means = [sum(g) / len(g) for g in groups]
    observed = sum((m - eps) ** 2 for m in means) / len(means)
    expected = sum(eps * (1 - eps) / len(g) for g in groups) / len(groups)
    return eps, observed, expected, (observed / expected if expected else float('nan'))


def analyze(name, cases, fraction=0.0):
    invalid = {k: c for k, c in cases.items() if not c['valid'] and k[1] == fraction}
    print(f'\n== {name}: {len(invalid)} invalid (ambiguous) case-conditions at cell share {fraction:.0%}')
    eps_v, ov, ev, rv = overdispersion([c['votes'] for c in invalid.values()])
    print(f'reviewer votes: honest error {eps_v:.3f}; per-case variance {ov:.4f} vs {ev:.4f} if independent '
          f'(ratio {rv:.1f})')
    seats = [[s for _, (h, s) in sorted(c['seats'].items()) if h] for c in invalid.values()]
    eps_a, oa, ea, ra = overdispersion(seats)
    print(f'committee seats: honest error {eps_a:.3f}; per-case variance {oa:.4f} vs {ea:.4f} if independent '
          f'(ratio {ra:.1f})')
    by_kind = defaultdict(list)
    for c in invalid.values():
        by_kind[c['kind']] += [s for _, (h, s) in c['seats'].items() if h]
    print('auditor error by kind: ' + ', '.join(f'{k} {sum(v) / len(v):.2f} (n={len(v)})' for k, v in sorted(by_kind.items())))
    print(f"{'regime':<8} {'observed capture by honest error':>34} {'independence predicts':>22}")
    rows = {}
    for m, k in REGIMES:
        hits = n = 0
        for c in invalid.values():
            first = [c['seats'][i] for i in range(m) if i in c['seats']]
            if len(first) == m and all(h for h, _ in first):
                n += 1
                hits += sum(s for _, s in first) >= k
        pred = binom_tail(m, k, eps_a)
        rows[f'{k}of{m}'] = (hits, n, pred)
        print(f'{k}-of-{m:<4} {hits:>15}/{n:<4} = {hits / max(1, n):.3f} {pred:>22.3f}')
    return {'eps_votes': eps_v, 'overdispersion_votes': rv, 'eps_auditors': eps_a, 'overdispersion_auditors': ra,
            'regimes': rows, 'by_kind': {k: sum(v) / len(v) for k, v in by_kind.items()}}


def mixed(cases_a, cases_b, fraction=0.0):
    """Alternate seats: even seats from model A, odd seats from model B, same case and seat identities."""
    print('\n== Mixed-model committees (even seats model A, odd seats model B), share 0%')
    shared = [k for k in cases_a if k in cases_b and not cases_a[k]['valid'] and k[1] == fraction]
    for m, k in REGIMES:
        hits_mix = hits_a = hits_b = n = 0
        for key in shared:
            a, b = cases_a[key]['seats'], cases_b[key]['seats']
            if not all(i in a and i in b for i in range(m)):
                continue
            n += 1
            mix = sum((a if i % 2 == 0 else b)[i][1] for i in range(m))
            hits_mix += mix >= k
            hits_a += sum(a[i][1] for i in range(m)) >= k
            hits_b += sum(b[i][1] for i in range(m)) >= k
        print(f'{k}-of-{m:<4} A only {hits_a}/{n}   B only {hits_b}/{n}   mixed {hits_mix}/{n}')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--model', action='append', required=True, help='Name=glob of sweep roots')
    args = parser.parse_args()
    loaded, results = {}, {}
    for spec in args.model:
        name, pattern = spec.split('=', 1)
        dirs = [d for root in glob(pattern) for d in sorted(Path(root).glob('f*'))]
        loaded[name] = load(dirs)
        results[name] = {'share_0': analyze(name, loaded[name], 0.0), 'share_30': analyze(name, loaded[name], 0.3)}
    if len(loaded) == 2:
        a, b = list(loaded.values())
        mixed(a, b)
    Path('docs/report/independence.json').write_text(json.dumps(results, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
