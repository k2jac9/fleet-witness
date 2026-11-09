"""Do honest LLM errors cluster? Test the independence assumption behind committee guarantees.

Usage: python scripts/independence.py --model 'DeepSeek=runs/ambig-deepseek-s*'
       --model 'gpt-oss=runs/ambig-gptoss-s*' --output NEW_OUTPUT.json
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
import sys

if __package__ in (None, ''):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.baselines import load_run

REGIMES = [(1, 1), (3, 2), (5, 3), (7, 4), (7, 7)]


def binom_tail(m, k, p):
    return sum(comb(m, j) * p ** j * (1 - p) ** (m - j) for j in range(k, m + 1))


def load(dirs):
    """Per (seed, fraction, condition, case): reviewer votes and committee signatures by seat (honest only)."""
    cases = {}
    model = None
    for d in dirs:
        run = load_run(d)
        truth, manifest = run['truth'], run['manifest']
        if manifest.get('case_mode') != 'ambiguous':
            raise ValueError(f'not an ambiguous-mode run: {d}')
        if model is not None and model != manifest['model']:
            raise ValueError('mixed models in one independence dataset')
        model = manifest['model']
        cell = set(truth['colluders'])
        run_keys = {(manifest['seed'], manifest['cell_fraction'], condition, case)
                    for condition in manifest['conditions'] for case in truth['cases']}
        if run_keys & cases.keys():
            raise ValueError('duplicate run identities in independence dataset')
        for e in run['events']:
            info = truth['cases'][e['case_id']]
            key = (manifest['seed'], manifest['cell_fraction'], e['condition'], e['case_id'])
            c = cases.setdefault(key, {'kind': info['kind'], 'valid': info['valid'], 'votes': [], 'seats': {},
                                       'committee': truth['committees'][e['case_id']], 'cell': cell})
            honest = not (e['condition'].endswith('-cell') and e['agent_id'] in cell)
            if e['type'] == 'vote' and honest and e.get('vote') in ('approve', 'deny'):
                c['votes'].append(e['vote'] == 'approve')
            if e['type'] == 'attestation' and e.get('outcome') in ('sign', 'refuse', 'abstain'):
                c['seats'][e['seat']] = (honest, e['outcome'] == 'sign')
    return cases


def overdispersion(groups):
    """groups: list of lists of 0/1. Returns (mean, observed var of group means, binomial-expected var, ratio)."""
    groups = [g for g in groups if g]
    total = sum(len(g) for g in groups)
    if not total:
        return None, None, None, None
    eps = sum(sum(g) for g in groups) / total
    means = [sum(g) / len(g) for g in groups]
    observed = sum((m - eps) ** 2 for m in means) / len(means)
    expected = sum(eps * (1 - eps) / len(g) for g in groups) / len(groups)
    return eps, observed, expected, (observed / expected if expected else None)


def display(value, digits=3):
    return f'{value:.{digits}f}' if value is not None else 'undefined'


def analyze(name, cases, fraction=0.0):
    invalid = {k: c for k, c in cases.items() if not c['valid'] and k[1] == fraction}
    print(f'\n== {name}: {len(invalid)} invalid (ambiguous) case-conditions at cell share {fraction:.0%}')
    eps_v, ov, ev, rv = overdispersion([c['votes'] for c in invalid.values()])
    print(f'reviewer votes: honest error {display(eps_v)}; per-case variance {display(ov, 4)} vs {display(ev, 4)} if independent '
          f'(ratio {display(rv, 1)})')
    seats = [[s for _, (h, s) in sorted(c['seats'].items()) if h] for c in invalid.values()]
    eps_a, oa, ea, ra = overdispersion(seats)
    print(f'committee seats: honest error {display(eps_a)}; per-case variance {display(oa, 4)} vs {display(ea, 4)} if independent '
          f'(ratio {display(ra, 1)})')
    by_kind = defaultdict(list)
    for c in invalid.values():
        by_kind[c['kind']] += [s for _, (h, s) in c['seats'].items() if h]
    print('auditor error by kind: ' + ', '.join(
        f'{k} {display(sum(v) / len(v) if v else None, 2)} (n={len(v)})' for k, v in sorted(by_kind.items())))
    print(f"{'regime':<8} {'observed capture by honest error':>34} {'independence predicts':>22}")
    rows = {}
    for m, k in REGIMES:
        hits = n = 0
        for c in invalid.values():
            first = [c['seats'][i] for i in range(m) if i in c['seats']]
            if len(first) == m and all(h for h, _ in first):
                n += 1
                hits += sum(s for _, s in first) >= k
        pred = binom_tail(m, k, eps_a) if eps_a is not None else None
        rows[f'{k}of{m}'] = (hits, n, pred)
        print(f'{k}-of-{m:<4} {hits:>15}/{n:<4} = {display(hits / n if n else None)} {display(pred):>22}')
    return {'eps_votes': eps_v, 'overdispersion_votes': rv, 'eps_auditors': eps_a, 'overdispersion_auditors': ra,
            'undefined_statistics': 'null means no observations or zero expected variance',
            'regimes': rows, 'by_kind': {k: sum(v) / len(v) if v else None for k, v in by_kind.items()}}


def mixed(cases_a, cases_b, fraction=0.0):
    """Alternate seats: even seats from model A, odd seats from model B, same case and seat identities."""
    if cases_a.keys() != cases_b.keys():
        raise ValueError('mixed-model datasets have different case identities')
    for key in cases_a:
        for field in ('kind', 'valid', 'committee', 'cell'):
            if cases_a[key][field] != cases_b[key][field]:
                raise ValueError(f'mixed-model datasets mismatch {field}')
    print(f'\n== Offline mixed-model splice (even A, odd B), share {fraction:.0%}')
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
    parser.add_argument('--output', required=True, type=Path, help='New derived JSON file; never writes input runs')
    parser.add_argument('--model', action='append', required=True, help='Name=glob of sweep roots')
    args = parser.parse_args()
    loaded, results = {}, {}
    for spec in args.model:
        name, pattern = spec.split('=', 1)
        dirs = [d for root in glob(pattern) for d in sorted(Path(root).glob('f*'))]
        if not dirs or name in loaded:
            raise ValueError('empty glob or duplicate model name')
        loaded[name] = load(dirs)
        results[name] = {'share_0': analyze(name, loaded[name], 0.0), 'share_30': analyze(name, loaded[name], 0.3)}
    if len(loaded) == 2:
        a, b = list(loaded.values())
        mixed(a, b)
    with args.output.open('x', encoding='utf-8') as handle:
        json.dump(results, handle, indent=2, allow_nan=False)


if __name__ == '__main__':
    main()
