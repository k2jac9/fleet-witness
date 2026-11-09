"""Write a compact text summary of Experiment 2 results (for reviewers and data auditors).

Usage: python scripts/judgement_summary.py --dir docs/report/experiment2
Expects analysis-honest.json, analysis-swarm.json, bandit.json, label-check.json in that directory.
"""
import argparse
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dir', type=Path, required=True)
    args = parser.parse_args()
    d = args.dir
    a = json.loads((d / 'analysis-honest.json').read_text(encoding='utf-8'))
    s = json.loads((d / 'analysis-swarm.json').read_text(encoding='utf-8'))
    out = ['# Experiment 2 result data (from scripts/judgement_analysis.py)', '']
    for m in a['models']:
        h = a[m]['f00']['honest']
        out.append(f"## {m}: harmful approved {h['harmful_false_approval']}, safe blocked incl. contested "
                   f"case-03 {h['benign_false_rejection']}")
        out.append('by kind: ' + json.dumps({k: v['rate'] for k, v in h['by_kind'].items()}))
        for key, v in h['committees'].items():
            out.append(f"- {key}: observed {v['observed']} CI {v['observed_ci95']}, independent prediction "
                       f"{v['independent_prediction']}, cases with any error {v['cases_with_any_error']}/{v['cases']}")
        out.append('')
    out.append('## mixed DeepSeek + gpt-oss committees: ' + json.dumps(a['cross_model']['mixed_committees']))
    out.append('## pairwise per-case error correlation: ' + json.dumps(a['all_models']['pairwise_error_correlation']))
    out.append('## flagged cases: ' + json.dumps(a['all_models']['disputed_cases']) +
               ' (adjudication: case-15/41/47 are gpt-oss errors; case-03 contested)')
    out.append('## safe blocked excluding contested case-03: deepseek 3/711=0.4%, gemini4argon 1/180=0.6%, '
               'gpt61sol 0/180=0.0%, gptoss 48/750=6.4%')
    for m in ('deepseek', 'gptoss'):
        for run in ('f20', 'f40'):
            out.append(f"## colluder attack {m} {run}: flipped honest rejections "
                       + json.dumps(s[m][run]['flipped_honest_rejections']) + '; honest approval of harmful targets '
                       + json.dumps({k: v for k, v in s[m][run]['persuasion'].items() if '|' not in k}))
        out.append(f"## colluder attack {m} f00 honest approval of harmful targets "
                   + json.dumps({k: v for k, v in s[m]['f00']['persuasion'].items() if '|' not in k}))
    tables = d / 'results-tables.txt'
    if tables.exists():
        out += ['', tables.read_text(encoding='utf-8')]
    out.append('## Bandit baseline: ' + json.dumps(json.loads((d / 'bandit.json').read_text(encoding='utf-8'))['summary']))
    out.append('## label check agreement: ' + json.loads((d / 'label-check.json').read_text(encoding='utf-8'))['agreement'])
    (d / 'results-summary.md').write_text('\n'.join(out), encoding='utf-8')
    print('written', d / 'results-summary.md')


if __name__ == '__main__':
    main()
