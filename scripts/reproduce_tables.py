"""Reproduce current derived tables from an immutable extracted run archive.

Explicit input/output roots are required. This is offline synthetic reconstruction
with historical votes, not recovery of historical signatures or model requests.
The default additionally executes the bounded depth-six checker with mutants.
"""
import argparse
import contextlib
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import platform
import subprocess
import sys
import zipfile

REPO = Path(__file__).resolve().parents[1]
if __package__ in (None, ''):
    sys.path.insert(0, str(REPO))
from scripts import baselines, independence, report_stats
from fleet_witness.swarm.sweep import summarize, format_summary
from fleet_witness.verify_institution import MUTANTS

MAIN_ROOTS = ('sweep-deepseek2k', 'sweep-gptoss')
AMBIG_ROOTS = {name: tuple(f'ambig-{stem}-s{seed}' for seed in (3000, 4000, 5000))
               for name, stem in (('DeepSeek', 'deepseek'), ('gpt-oss', 'gptoss'))}
MODELS = {'DeepSeek': 'openrouter:deepseek/deepseek-v4-flash-0731',
          'gpt-oss': 'openrouter:openai/gpt-oss-20b'}
HISTORICAL_ARCHIVE_SHA256 = 'c55e8acf07ed8dd3c11bc3dc8f70269adebaac6bfa14727642cca7314d1f821a'


def _historical_manifest_hashes():
    """Allow only manifest bytes from the preserved, digest-pinned archive."""
    archive = REPO / 'data/fleet-witness-runs-2026-11-08.zip'
    if hashlib.sha256(archive.read_bytes()).hexdigest() != HISTORICAL_ARCHIVE_SHA256:
        raise ValueError('historical archive identity mismatch')
    with zipfile.ZipFile(archive) as source:
        return frozenset(hashlib.sha256(source.read(info)).hexdigest() for info in source.infolist()
                         if info.filename.replace('\\', '/').endswith('/manifest.json') and
                         info.file_size <= 1024 * 1024)


def validate_sweep_identity(name, runs):
    """Bind this published dataset's labels to recorded model and experiment identities."""
    label = 'DeepSeek' if 'deepseek' in name else 'gpt-oss'
    mode = 'standard' if name in MAIN_ROOTS else 'ambiguous'
    seed_base = 1000 if name in MAIN_ROOTS else int(name.rsplit('-s', 1)[1])
    expected = {'agents': 50, 'cases': 24, 'waves': 5, 'max_output_tokens': 2000,
                'conditions': ['hidden-cell', 'visible-cell']}
    for run in runs:
        manifest = run['manifest']
        if manifest.get('model') != MODELS[label]:
            raise ValueError(f'model identity differs from declared dataset: {name}')
        if (any(manifest.get(key) != value for key, value in expected.items())
                or manifest.get('case_mode', 'standard') != mode
                or manifest['seed'] != seed_base + round(manifest['cell_fraction'] * 1000)):
            raise ValueError(f'experiment configuration differs from declared dataset: {name}')
    return {'label': label, 'model': MODELS[label], 'case_mode': mode, 'seed_base': seed_base, **expected}


def _write(root, name, value):
    with (root / name).open('x', encoding='utf-8') as handle:
        json.dump(value, handle, indent=2, allow_nan=False)
        handle.write('\n')


def _checker_report_passed(data):
    """Validate the closed depth-six checker result before accepting it."""
    if (not isinstance(data, dict) or set(data) != {'schema_version', 'depth', 'base', 'mutants', 'passed'} or
            data['schema_version'] != 'institution-check-v1' or data['depth'] != 6 or
            type(data['depth']) is not int or type(data['passed']) is not bool or
            not isinstance(data['base'], dict) or set(data['base']) != {'hybrid', 'committee_only'} or
            not isinstance(data['mutants'], dict) or set(data['mutants']) != set(MUTANTS)):
        return False
    def valid_violation(item):
        return (isinstance(item, dict) and set(item) == {'trace', 'problems'} and
                isinstance(item['trace'], list) and 1 <= len(item['trace']) <= 7 and
                isinstance(item['problems'], list) and 1 <= len(item['problems']) <= 10 and
                all(isinstance(value, str) and 0 < len(value) <= 1024
                    for value in item['trace'] + item['problems']))
    def valid(entry, mutations, verified):
        return (isinstance(entry, dict) and set(entry) == {'depth', 'mutations', 'distinct_states',
                'transitions_checked', 'violations', 'verified', 'seconds'} and entry['depth'] == 6 and
                type(entry['depth']) is int and entry['mutations'] == mutations and
                type(entry['distinct_states']) is int and entry['distinct_states'] > 0 and
                type(entry['transitions_checked']) is int and entry['transitions_checked'] > 0 and
                type(entry['verified']) is bool and entry['verified'] is verified and
                isinstance(entry['violations'], list) and bool(entry['violations']) != verified and
                len(entry['violations']) <= 3 and all(valid_violation(item) for item in entry['violations']) and
                isinstance(entry['seconds'], (int, float)) and not isinstance(entry['seconds'], bool) and
                0 <= entry['seconds'] < float('inf'))
    return (data['passed'] and all(valid(entry, [], True) for entry in data['base'].values()) and
            all(valid(data['mutants'][name], [name], False) for name in MUTANTS))


def _run_checker(output_root):
    command = [sys.executable, '-m', 'fleet_witness.verify_institution', '--depth', '6', '--mutants', '--json']
    result = {'executed': True, 'command': command, 'returncode': None, 'passed': False}
    with (output_root / 'verify-depth6.json').open('x', encoding='utf-8') as stdout, \
            (output_root / 'verify-depth6.stderr').open('x', encoding='utf-8') as stderr:
        try:
            completed = subprocess.run(command, cwd=REPO, stdout=stdout, stderr=stderr, check=False)
            result['returncode'] = completed.returncode
        except OSError as error:
            stderr.write(f'checker launch failed: {error}\n')
    try:
        raw = (output_root / 'verify-depth6.json').read_bytes()
        if len(raw) > 1024 * 1024:
            raise ValueError('checker result exceeds limit')
        def unique(pairs):
            out = {}
            for key, value in pairs:
                if key in out:
                    raise ValueError('duplicate checker result field')
                out[key] = value
            return out
        report = json.loads(raw, object_pairs_hook=unique, parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
        result['passed'] = result['returncode'] == 0 and _checker_report_passed(report)
    except (ValueError, TypeError, UnicodeError, RecursionError):
        pass
    return result


def reproduce(input_root, output_root, *, skip_checker=False):
    input_root, output_root = Path(input_root).resolve(), Path(output_root).absolute()
    if output_root.exists() or output_root.is_symlink():
        raise ValueError('output root must be fresh')
    if any(parent.is_symlink() for parent in output_root.parents):
        raise ValueError('output root has symlink parent')
    if output_root.resolve().is_relative_to(input_root):
        raise ValueError('output root must be outside the immutable input root')
    roots = [*MAIN_ROOTS, *(name for group in AMBIG_ROOTS.values() for name in group)]
    loaded, identities = {}, {}
    historical_manifest_hashes = _historical_manifest_hashes()
    # Validate every required main/near-miss input before creating output. A
    # missing fraction is not silently turned into a smaller report denominator.
    for name in roots:
        root = input_root / name
        if not root.is_dir():
            raise ValueError(f'missing required sweep: {root}')
        runs = baselines.load_root(root)
        expected = {0, .1, .2, .3, .4, .5} if name in MAIN_ROOTS else {0, .3}
        if {r['manifest']['cell_fraction'] for r in runs} != expected:
            raise ValueError(f'incomplete sweep fractions: {root}')
        identities[name] = validate_sweep_identity(name, runs)
        loaded[name] = runs
    input_hashes = {str(p.relative_to(input_root)): hashlib.sha256(p.read_bytes()).hexdigest()
                    for p in input_root.rglob('*') if p.is_file()}
    output_root.mkdir(mode=0o700, parents=True)
    baseline_results, stats = [], []
    text = io.StringIO()
    with contextlib.redirect_stdout(text):
        for name in MAIN_ROOTS:
            result = baselines.summarize_root(input_root / name, runs=loaded[name])
            baseline_results.append(result)
            print(baselines.format_summary(result))
            statistic = report_stats.statistics(input_root / name, runs=loaded[name])
            stats.append(statistic)
            print(report_stats.format_statistics(statistic))
            views = {r['directory']: r['decisions'] for r in loaded[name]}
            summary = summarize([input_root / name], analysis_root=output_root / 'analyses', decision_overrides=views,
                                historical_manifest_hashes=historical_manifest_hashes)
            _write(output_root, name + '-summary.json', summary)
            print(format_summary(summary))
        ambiguous, independent_results = {}, {}
        for label, names in AMBIG_ROOTS.items():
            directories = [r['directory'] for name in names for r in loaded[name]]
            ambiguous[label] = independence.load(directories)
            independent_results[label] = {
                'model': MODELS[label],
                'share_0': independence.analyze(label, ambiguous[label], 0.0),
                'share_30': independence.analyze(label, ambiguous[label], 0.3)}
        independence.mixed(*ambiguous.values())
    _write(output_root, 'baselines.json', baseline_results)
    _write(output_root, 'report-stats.json', stats)
    _write(output_root, 'independence.json', independent_results)
    (output_root / 'tables.txt').write_text(text.getvalue(), encoding='utf-8')
    print(text.getvalue(), end='')
    checker = {'executed': False, 'reason': 'explicit --skip-checker'}
    if not skip_checker:
        checker = _run_checker(output_root)
    after = {str(p.relative_to(input_root)): hashlib.sha256(p.read_bytes()).hexdigest()
             for p in input_root.rglob('*') if p.is_file()}
    if after != input_hashes:
        raise ValueError('input evidence changed during reproduction')
    source_paths = ['scripts/baselines.py', 'scripts/independence.py', 'scripts/report_stats.py',
                    'scripts/reproduce_tables.py', 'scripts/extract_run_archive.py', 'fleet_witness/institution.py',
                    'fleet_witness/swarm/sweep.py', 'fleet_witness/swarm/world.py',
                    'fleet_witness/swarm/detect.py', 'fleet_witness/verify_institution.py',
                    'fleet_witness/evidence.py', 'fleet_witness/swarm/runner.py']
    provenance = {**baselines.PROVENANCE, 'generated_at': datetime.now(timezone.utc).isoformat(),
                  'python': platform.python_version(), 'executable': sys.executable, 'platform': platform.platform(),
                  'source_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=REPO, text=True).strip(),
                  'source_worktree_dirty': bool(subprocess.check_output(
                      ['git', 'status', '--porcelain'], cwd=REPO, text=True).strip()),
                  'source_files_sha256': {p: hashlib.sha256((REPO / p).read_bytes()).hexdigest() for p in source_paths},
                  'dataset_identities': identities,
                  'input_root': str(input_root), 'input_files_sha256': input_hashes,
                  'inputs_unchanged': True, 'checker': checker,
                  'output_files_sha256': {str(p.relative_to(output_root)): hashlib.sha256(p.read_bytes()).hexdigest()
                                         for p in output_root.rglob('*') if p.is_file()}}
    _write(output_root, 'reproduction-provenance.json', provenance)
    if checker['executed'] and not checker['passed']:
        raise RuntimeError('bounded checker failed; see retained output and provenance')
    return provenance


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input-root', type=Path, required=True, help='Extracted runs/ directory')
    parser.add_argument('--output-root', type=Path, required=True, help='Fresh derived artifact directory')
    parser.add_argument('--skip-checker', action='store_true', help='Explicitly omit the bounded checker')
    args = parser.parse_args(argv)
    reproduce(args.input_root, args.output_root, skip_checker=args.skip_checker)


if __name__ == '__main__':
    main()
