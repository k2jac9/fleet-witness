"""Turn Experiment 2 analysis JSON into LaTeX table rows (numbers are copied by code, not by hand).

Usage: python scripts/judgement_tex.py --honest runs/judge-all/analysis.json --swarm runs/judge/analysis.json
Prints LaTeX snippets: honest-error table, committee table, regime table.
"""
import argparse
import json

NAMES = {'gpt61sol': 'GPT-6.1 Sol', 'gemini4argon': 'Gemini 4 Argon', 'deepseek': 'DeepSeek v4 Flash',
         'gptoss': 'gpt-oss-20b'}
REGIMES = [('direct', 'Direct majority'), ('gated-majority', 'Gated majority'), ('auditor-1of1', 'Auditor 1-of-1'),
           ('committee-2of3', 'Committee 2-of-3'), ('committee-3of5', 'Committee 3-of-5'),
           ('committee-4of7', 'Committee 4-of-7'), ('unanimous-7of7', 'Unanimous 7-of-7'),
           ('hybrid-maj+4of7', 'Hybrid (majority \\& 4-of-7)')]


def pct(x):
    return '--' if x is None else f'{100 * x:.1f}\\%'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--honest', required=True)
    parser.add_argument('--swarm')
    args = parser.parse_args()
    a = json.load(open(args.honest, encoding='utf-8'))
    print('% honest error: model & harmful approved & safe blocked & harmful cases with any error & safe cases with any error')
    for m in a['models']:
        h = a[m]['f00']['honest']
        c1 = h['committees']
        print(f"{NAMES.get(m, m)} & {pct(h['harmful_false_approval'])} & {pct(h['benign_false_rejection'])} & "
              f"{c1['1-of-1:unsafe_release_on_harmful']['cases_with_any_error']}/{c1['1-of-1:unsafe_release_on_harmful']['cases']} & "
              f"{c1['1-of-1:blocked_benign']['cases_with_any_error']}/{c1['1-of-1:blocked_benign']['cases']} \\\\")
    print('% committee: model & committee & observed blocked-safe [CI] & independent prediction & observed unsafe & independent')
    for m in a['models']:
        c = a[m]['f00']['honest']['committees']
        for key in ('2-of-3', '3-of-5', '4-of-7', '7-of-7'):
            b, u = c[f'{key}:blocked_benign'], c[f'{key}:unsafe_release_on_harmful']
            print(f"{NAMES.get(m, m)} & {key} & {pct(b['observed'])} [{pct(b['observed_ci95'][0])}, {pct(b['observed_ci95'][1])}] & "
                  f"{pct(b['independent_prediction'])} & {pct(u['observed'])} & {pct(u['independent_prediction'])} \\\\")
    if 'cross_model' in a:
        print('% cross-model', json.dumps(a['cross_model'])[:3000])
    if args.swarm:
        s = json.load(open(args.swarm, encoding='utf-8'))
        print('% regimes pooled over shares 20/40 and both boards: unsafe/targets, valid/valid, forged/forged per model')
        for key, label in REGIMES:
            cells = []
            for m in s['models']:
                tot = {'unsafe_targets': 0, 'targets': 0, 'valid_released': 0, 'valid': 0, 'forged_released': 0, 'forged': 0}
                for run in ('f20', 'f40'):
                    for board in ('hidden-cell', 'visible-cell'):
                        cell = s[m].get(run, {}).get('regimes', {}).get(f'{key}|{board}')
                        if cell:
                            for k2 in tot:
                                tot[k2] += cell[k2]
                cells.append(tot)
            print(label + ' & ' + ' & '.join(f"{t['unsafe_targets']}/{t['targets']}" for t in cells) + ' & ' +
                  ' & '.join(f"{t['valid_released']}/{t['valid']}" for t in cells) + ' & ' +
                  ' & '.join(f"{t['forged_released']}/{t['forged']}" for t in cells) + ' \\\\')


if __name__ == '__main__':
    main()
