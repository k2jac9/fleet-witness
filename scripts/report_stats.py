"""Descriptive pooled counts from validated run records; no independent-binomial CIs.

Cases, board conditions and governance regimes share votes and committee draws.
The pooled outcomes are paired; they are not independent Bernoulli observations.
"""
import argparse
import json
from pathlib import Path
import sys

if __package__ in (None, ''):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.baselines import load_root, summarize_root
from fleet_witness.verify_institution import capture_probability
from scripts.baselines import KERNEL_REGIMES


def statistics(root, *, runs=None):
    runs = load_root(root) if runs is None else runs
    baseline = summarize_root(root, runs=runs)
    rows = {}
    for name, counts in baseline['totals'].items():
        n = baseline['denominators']['targets']
        size, quorum, majority = KERNEL_REGIMES.get(name, (0, 0, True))
        expected = seated = 0.0
        if size:
            for run in runs:
                m, truth = run['manifest'], run['truth']
                if m['cell_fraction'] == 0:
                    continue
                for condition in m['conditions']:
                    colluders = set(truth['colluders']) if condition.endswith('-cell') else set()
                    targets = [e for e in run['events'] if e['condition'] == condition
                               and e['type'] == 'attestation' and e['case_id'] in truth['targets']
                               and e['agent_id'] not in colluders and e['outcome'] in ('sign', 'refuse', 'abstain')]
                    eps = sum(e['sign'] for e in targets) / len(targets) if targets else 0.0
                    expected += len(truth['targets']) * capture_probability(m['agents'], len(colluders), size, quorum, eps)
                    seated += sum(len(colluders & set(truth['committees'][case][:size])) >= quorum
                                  for case in truth['targets'])
        rows[name] = {'effects': counts['targets'], 'n_targets': n,
                      'rate': counts['targets'] / n if n else None,
                      'committee_only_expected': expected if size else None,
                      'seated_colluder_bound': int(seated) if size else None}
    return {'root': str(Path(root).resolve()), 'interpretation': 'descriptive paired outcomes; no pooled binomial CI',
            'prediction_note': 'Committee-only predictions assume independent honest errors and compliant colluders. '
                               'Hybrid majority additionally gates execution; these are not full hybrid predictions. '
                               'Zero-seat regimes have no committee capture prediction.', 'rows': rows}


def format_statistics(result):
    lines = [f"== {result['root']}", result['interpretation'], result['prediction_note'],
             f"{'regime':<20} {'observed':>10} {'rate':>8} {'committee expected':>20} {'seat bound':>12}"]
    for name, row in result['rows'].items():
        ratio = f"{row['rate']:.3f}" if row['rate'] is not None else 'undefined'
        expected = f"{row['committee_only_expected']:.2f}" if row['committee_only_expected'] is not None else 'n/a'
        seated = str(row['seated_colluder_bound']) if row['seated_colluder_bound'] is not None else 'n/a'
        lines.append(f"{name:<20} {row['effects']:>4}/{row['n_targets']:<5} {ratio:>8} {expected:>20} {seated:>12}")
    return '\n'.join(lines)


def main(roots, output=None):
    results = [statistics(root) for root in roots]
    for result in results:
        print(format_statistics(result))
    if output:
        with Path(output).open('x', encoding='utf-8') as handle:
            json.dump(results, handle, indent=2, allow_nan=False)
    return results


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('roots', nargs='+', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    main(args.roots, args.output)
