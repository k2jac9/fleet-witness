"""Exact 95% confidence intervals and a-priori expectations for pooled capture rates.

Usage: python scripts/report_stats.py runs/sweep-deepseek2k runs/sweep-gptoss
Pools all shares > 0 (both board conditions), as in the report's main table.
"""
import json
import sys
from math import comb
from pathlib import Path


def binom_cdf(k, n, p):
    return sum(comb(n, i) * p ** i * (1 - p) ** (n - i) for i in range(0, k + 1))


def clopper_pearson(x, n, alpha=0.05):
    def solve(f, lo=0.0, hi=1.0):
        for _ in range(80):
            mid = (lo + hi) / 2
            if f(mid):
                hi = mid
            else:
                lo = mid
        return (lo + hi) / 2
    lower = 0.0 if x == 0 else solve(lambda p: 1 - binom_cdf(x - 1, n, p) >= alpha / 2)
    upper = 1.0 if x == n else solve(lambda p: binom_cdf(x, n, p) <= alpha / 2)
    return lower, upper


def main(roots):
    for root in roots:
        summary = json.loads((Path(root) / 'sweep-summary.json').read_text(encoding='utf-8'))
        pooled = {}
        for row in summary['table']:
            if row['fraction'] == 0:
                continue
            for regime, g in row['regimes'].items():
                n = g['n_targets']
                p = pooled.setdefault(regime, [0, 0, 0.0, 0.0])
                p[0] += round(g['observed_capture'] * n)
                p[1] += n
                p[2] += (g['predicted_capture'] or 0) * n
                p[3] += (g['seated_capture'] or 0) * n
        print(f'== {root}')
        print(f"{'regime':<18} {'observed':>9} {'rate':>6} {'95% CI':>15} {'a-priori expected':>18} {'seat bound':>10}")
        for regime, (x, n, expected, seated) in pooled.items():
            lo, hi = clopper_pearson(x, n)
            exp = f'{expected:.1f}' if regime != 'direct' else 'n/a'
            st = f'{seated:.0f}' if regime != 'direct' else 'n/a'
            print(f'{regime:<18} {x:>4}/{n:<4} {x / n:>6.3f}  [{lo:.3f}, {hi:.3f}] {exp:>18} {st:>10}')


if __name__ == '__main__':
    main(sys.argv[1:])
