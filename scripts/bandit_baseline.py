"""Run optional Bandit on the new-side Python snippets of each case's own change.

Routine bundled edits are excluded. A finding means a medium/high severity issue;
"clean" means only that a successfully scanned snippet has no such finding, not
that the pull request is safe. Unparseable, unsupported and failed scans remain
unknown. Mixed-coverage cases are partial, even when one file scans successfully.
The legacy ``parsed`` row field means at least one validated scan; ``coverage``
and ``status`` establish whether every extracted file was scanned. Usage:
  python scripts/bandit_baseline.py --out docs/report/experiment2/bandit.json

Scanner failures write diagnostic results and exit 2. Expected limitations of
snippet coverage (unsupported files or unparseable hunks) do not fail the command.
"""
import argparse
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import textwrap

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fleet_witness.swarm.judgement_cases import PR_CASES  # noqa: E402

SCAN_TIMEOUT = 30
SCANNED = frozenset({'clean', 'findings'})


def new_side(diff):
    """New-side lines per file, retaining unsupported files for coverage accounting."""
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
    return {n: '\n'.join(lines) for n, lines in files.items()}


def tool_info():
    """Verify the optional executable and retain its reported version and diagnostics."""
    info = {'version': None, 'returncode': None, 'stderr': '', 'error': None}
    try:
        out = subprocess.run([sys.executable, '-m', 'bandit', '--version'], capture_output=True,
                             text=True, timeout=SCAN_TIMEOUT)
    except (OSError, subprocess.TimeoutExpired) as error:
        info['error'] = str(error)
        return info
    info.update(returncode=out.returncode, stderr=out.stderr)
    # ``python -m bandit`` reports argparse's __main__.py program name.
    version = re.search(r'^(?:bandit|__main__\.py)\s+(\S+)', out.stdout, re.MULTILINE)
    if out.returncode != 0 or version is None:
        info['error'] = 'Bandit is unavailable or did not report a version'
    else:
        info['version'] = version.group(1)
    return info


def _unknown(status, error, *, tool=None, source_form=None):
    tool = tool or {}
    return {'status': status, 'flagged': None, 'issues': [], 'error': error,
            'tool_version': tool.get('version'),
            'returncode': tool.get('returncode') if tool.get('error') else None,
            'stderr': tool.get('stderr', ''), 'source_form': source_form}


def _validated_issues(out, filename):
    """Require both a complete JSON result and evidence that this file was scanned."""
    if out.returncode not in (0, 1):
        raise ValueError(f'Bandit failed with exit status {out.returncode}')
    document = json.loads(out.stdout)
    if not isinstance(document, dict) or not isinstance(document.get('results'), list):
        raise ValueError('Bandit results must be a JSON list')
    if document.get('errors') != []:
        raise ValueError('Bandit reported file errors or omitted its errors list')
    metrics = document.get('metrics')
    scanned = metrics.get(filename) if isinstance(metrics, dict) else None
    if not isinstance(scanned, dict) or type(scanned.get('loc')) is not int or scanned['loc'] < 1:
        raise ValueError('Bandit did not confirm scanning the requested file')
    results = document['results']
    if out.returncode == 1 and not results:
        raise ValueError('Bandit exited nonzero without findings')
    issues = []
    for result in results:
        if (not isinstance(result, dict) or result.get('filename') != filename
                or not isinstance(result.get('test_id'), str) or not result['test_id']
                or not isinstance(result.get('issue_text'), str) or not result['issue_text']
                or result.get('issue_severity') not in ('LOW', 'MEDIUM', 'HIGH')):
            raise ValueError('Bandit returned a malformed or misbound finding')
        if result['issue_severity'] in ('MEDIUM', 'HIGH'):
            issues.append(result['test_id'] + ':' + result['issue_text'][:60])
    return issues


def scan(code, *, tool=None):
    """Return a structured scan outcome; failure/unknown never means ``flagged=False``."""
    dedented = textwrap.dedent(code)
    candidates = [('module', dedented), ('function', 'def _wrapped():\n' + textwrap.indent(dedented, '    '))]
    for source_form, text in candidates:
        try:
            compile(text, 'snippet', 'exec')
        except SyntaxError:
            continue
        tool = tool if tool is not None else tool_info()
        if tool['error']:
            return _unknown('tool_error', tool['error'], tool=tool, source_form=source_form)
        result = _unknown('tool_error', None, tool=tool, source_form=source_form)
        try:
            with tempfile.TemporaryDirectory(prefix='bandit-baseline-') as temporary:
                filename = Path(temporary) / 'snippet.py'
                filename.write_text(text, encoding='utf-8')
                out = subprocess.run([sys.executable, '-m', 'bandit', '-q', '-f', 'json', str(filename)],
                                     capture_output=True, text=True, timeout=SCAN_TIMEOUT)
                result.update(returncode=out.returncode, stderr=out.stderr)
                issues = _validated_issues(out, str(filename))
        except (OSError, subprocess.TimeoutExpired, ValueError) as error:
            result['error'] = str(error)
            return result
        result.update(status='findings' if issues else 'clean', flagged=bool(issues), issues=issues)
        return result
    return _unknown('unparsed', 'Neither the standalone nor function-wrapped snippet parses', tool=tool)


def file_coverage(files):
    return {'total': len(files), 'scanned': sum(f['status'] in SCANNED for f in files),
            **{status: sum(f['status'] == status for f in files)
               for status in ('unparsed', 'unsupported', 'tool_error')}}


def scan_case(diff, tool):
    files = []
    for name, code in new_side(diff).items():
        result = (scan(code, tool=tool) if name.endswith('.py') else
                  _unknown('unsupported', 'Only Python new-side snippets are supported', tool=tool))
        files.append({'file': name, **result})
    coverage = file_coverage(files)
    issues = [issue for file in files for issue in file['issues']]
    complete = bool(files) and coverage['scanned'] == coverage['total']
    if complete:
        status = 'findings' if issues else 'clean'
    elif coverage['scanned']:
        status = 'partial'
    else:
        status = next((s for s in ('tool_error', 'unparsed') if coverage[s]), 'unsupported')
    return {'status': status, 'parsed': bool(coverage['scanned']),
            'flagged': True if issues else (False if complete else None),
            'issues': issues, 'coverage': coverage, 'files': files}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    tool = tool_info()
    rows = []
    for index, (kind, _valid, _lv, title, _desc, diff, _why) in enumerate(PR_CASES, 1):
        rows.append({'case': f'case-{index:02d}', 'kind': kind, 'title': title, **scan_case(diff, tool)})
    summary = {}
    for kind in sorted({r['kind'] for r in rows}):
        sub = [r for r in rows if r['kind'] == kind]
        counts = ', '.join(f"{sum(r['status'] == status for r in sub)} {status}"
                           for status in ('clean', 'partial', 'unparsed', 'unsupported', 'tool_error'))
        summary[kind] = f"{sum(r['flagged'] is True for r in sub)}/{len(sub)} cases with findings; {counts}"
    coverage = {'cases': {'total': len(rows), 'fully_scanned': sum(r['status'] in SCANNED for r in rows),
                           'partially_scanned': sum(r['status'] == 'partial' for r in rows),
                           **{s: sum(r['status'] == s for r in rows)
                              for s in ('unparsed', 'unsupported', 'tool_error')}},
                'files': file_coverage([file for row in rows for file in row['files']])}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps({'schema_version': 'bandit-baseline-2',
                                   'tool': 'bandit (medium/high severity)', 'tool_version': tool['version'],
                                   'tool_status': tool, 'python_executable': sys.executable,
                                   'coverage': coverage, 'summary': summary, 'rows': rows}, indent=1), encoding='utf-8')
    print(json.dumps(summary, indent=1))
    return 2 if tool['error'] or coverage['files']['tool_error'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
