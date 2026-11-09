"""Non-LLM baseline for Experiment 2: run the Bandit static analyser on the new-side code of each case's own
change (not the bundled routine edits). A case is flagged if Bandit reports any issue of medium or high
severity. Unparseable snippets are retried wrapped in a function. Usage:
  python scripts/bandit_baseline.py --out docs/report/experiment2/bandit.json
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import textwrap

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fleet_witness.swarm.judgement_cases import PR_CASES  # noqa: E402


def new_side(diff):
    """New-side Python lines per file (context + added), skipping non-Python files."""
    files, current, name = {}, [], None
    for line in diff.splitlines():
        if line.startswith('+++ '):
            name = line[4:].removeprefix('b/')
            current = files.setdefault(name, [])
        elif line.startswith(('--- ', '@@')):
            continue
        elif name and line.startswith('+'):
            current.append(line[1:])
        elif name and line.startswith(' '):
            current.append(line[1:])
    return {n: '\n'.join(lines) for n, lines in files.items() if n.endswith('.py') or n.endswith('.txt')}


def scan(code):
    candidates = [textwrap.dedent(code), 'def _wrapped():\n' + textwrap.indent(textwrap.dedent(code), '    ')]
    for text in candidates:
        try:
            compile(text, 'snippet', 'exec')
        except SyntaxError:
            continue
        with tempfile.NamedTemporaryFile('w', suffix='.py', delete=False, encoding='utf-8') as handle:
            handle.write(text)
        out = subprocess.run([sys.executable, '-m', 'bandit', '-q', '-f', 'json', handle.name],
                             capture_output=True, text=True)
        Path(handle.name).unlink(missing_ok=True)
        results = json.loads(out.stdout or '{}').get('results', [])
        return True, [r['test_id'] + ':' + r['issue_text'][:60] for r in results
                      if r['issue_severity'] in ('MEDIUM', 'HIGH')]
    return False, []


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    rows = []
    for index, (kind, valid, _lv, title, _desc, diff, _why) in enumerate(PR_CASES, 1):
        parsed_any, issues = False, []
        for name, code in new_side(diff).items():
            if name.endswith('.txt'):
                continue
            ok, found = scan(code)
            parsed_any |= ok
            issues += found
        rows.append({'case': f'case-{index:02d}', 'kind': kind, 'title': title, 'parsed': parsed_any,
                     'flagged': bool(issues), 'issues': issues})
    summary = {}
    for kind in sorted({r['kind'] for r in rows}):
        sub = [r for r in rows if r['kind'] == kind]
        summary[kind] = f"{sum(r['flagged'] for r in sub)}/{len(sub)} flagged ({sum(r['parsed'] for r in sub)} parsed)"
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps({'tool': 'bandit (medium/high severity)', 'summary': summary, 'rows': rows},
                                   indent=1), encoding='utf-8')
    print(json.dumps(summary, indent=1))


if __name__ == '__main__':
    main()
