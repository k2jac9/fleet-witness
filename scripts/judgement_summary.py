"""Write a compact text summary of Experiment 2 results (for reviewers and data auditors).

Usage: python scripts/judgement_summary.py --dir docs/report/experiment2
Expects analysis-honest.json, analysis-swarm.json, bandit.json, label-check.json in that directory.

Exclusion rates always use f00.honest.per_case answered counts. By default only
case-03 is contested, matching the documented Experiment 2 sensitivity analysis.
Override this metadata with --adjudication PATH to a JSON object containing
"contested_cases" (a list of case IDs, possibly empty) and "source" (review provenance).
This metadata excludes cases; it does not relabel other disagreements as errors.
"""
import argparse
import json
from pathlib import Path

DEFAULT_ADJUDICATION = {
    'contested_cases': ['case-03'],
    'source': 'Documented Experiment 2 case-03 sensitivity analysis (docs/report/latex/report.tex)',
}


def adjudication_metadata(path):
    metadata = json.loads(path.read_text(encoding='utf-8')) if path is not None else DEFAULT_ADJUDICATION
    if (not isinstance(metadata, dict) or not isinstance(metadata.get('contested_cases'), list)
            or not all(isinstance(case, str) and case for case in metadata['contested_cases'])
            or len(set(metadata['contested_cases'])) != len(metadata['contested_cases'])
            or not isinstance(metadata.get('source'), str) or not metadata['source'].strip()):
        raise ValueError('adjudication requires unique contested_cases and a nonempty source')
    return metadata


def safe_blocked_counts(honest, contested):
    errors = answered = 0
    per_case = honest.get('per_case')
    if not isinstance(per_case, dict):
        raise ValueError('f00.honest.per_case is required to calculate exclusion rates')
    for case, counts in per_case.items():
        if (not isinstance(counts, dict) or type(counts.get('errors')) is not int
                or type(counts.get('n')) is not int or not 0 <= counts['errors'] <= counts['n']):
            raise ValueError(f'invalid answered/error counts for {case}')
        if counts.get('kind') in ('benign', 'benign_risky') and case not in contested:
            errors += counts['errors']
            answered += counts['n']
    return errors, answered


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dir', type=Path, required=True)
    parser.add_argument('--adjudication', type=Path, help='contested_cases/source metadata; default: case-03')
    args = parser.parse_args()
    d = args.dir
    a = json.loads((d / 'analysis-honest.json').read_text(encoding='utf-8'))
    s = json.loads((d / 'analysis-swarm.json').read_text(encoding='utf-8'))
    adjudication = adjudication_metadata(args.adjudication)
    contested = set(adjudication['contested_cases'])
    contested_label = ', '.join(adjudication['contested_cases']) or '(none)'
    out = ['# Experiment 2 result data (from scripts/judgement_analysis.py)', '',
           '> Derived from published aggregate JSON, with reporting corrections dated 11 November 2026.',
           '> This summary does not validate the missing raw Experiment 2 run records.', '']
    exclusions = []
    for m in a['models']:
        h = a[m]['f00']['honest']
        errors, answered = safe_blocked_counts(h, contested)
        percentage = f'{100 * errors / answered:.1f}%' if answered else 'n/a'
        exclusions.append(f'{m} {errors}/{answered}={percentage}')
        out.append(f"## {m}: harmful approved {h['harmful_false_approval']}, safe blocked incl. contested "
                   f"{contested_label} {h['benign_false_rejection']}")
        out.append('by kind: ' + json.dumps({k: v['rate'] for k, v in h['by_kind'].items()}))
        for key, v in h['committees'].items():
            out.append(f"- {key}: observed {v['observed']} CI {v['observed_ci95']}, independent prediction "
                       f"{v['independent_prediction']}, cases with any error {v['cases_with_any_error']}/{v['cases']}")
        out.append('')
    out.append('## mixed DeepSeek + gpt-oss committees: ' + json.dumps(a['cross_model']['mixed_committees']))
    out.append('## pairwise per-case error correlation: ' + json.dumps(a['all_models']['pairwise_error_correlation']))
    out.append('## flagged cases: ' + json.dumps(a['all_models']['disputed_cases']))
    out.append('## adjudication metadata: ' + json.dumps(adjudication))
    out.append(f'## safe blocked excluding contested {contested_label}: ' + ', '.join(exclusions))
    for m in ('deepseek', 'gptoss'):
        for run in ('f20', 'f40'):
            out.append(f"## colluder run {m} {run}: releases on cases rejected in the separate f00 reference run "
                       '(same board; descriptive comparison): '
                       + json.dumps(s[m][run]['flipped_honest_rejections']) + '; honest approval of harmful targets '
                       + json.dumps({k: v for k, v in s[m][run]['persuasion'].items() if '|' not in k}))
        out.append(f"## separate reference run {m} f00: honest approval of harmful targets "
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
