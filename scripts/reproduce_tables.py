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

REPO = Path(__file__).resolve().parents[1]
if __package__ in (None, ''):
    sys.path.insert(0, str(REPO))
from scripts import baselines, independence, report_stats
from fleet_witness.swarm.sweep import summarize, format_summary

MAIN_ROOTS = ('sweep-deepseek2k', 'sweep-gptoss')
AMBIG_ROOTS = {name: tuple(f'ambig-{stem}-s{seed}' for seed in (3000, 4000, 5000))
               for name, stem in (('DeepSeek', 'deepseek'), ('gpt-oss', 'gptoss'))}


def _write(root, name, value):
    with (root / name).open('x', encoding='utf-8') as handle:
        json.dump(value, handle, indent=2, allow_nan=False)
        handle.write('\n')


def reproduce(input_root, output_root, *, skip_checker=False):
    input_root, output_root = Path(input_root).resolve(), Path(output_root).absolute()
    if output_root.exists() or output_root.is_symlink():
        raise ValueError('output root must be fresh')
    if any(parent.is_symlink() for parent in output_root.parents):
        raise ValueError('output root has symlink parent')
    if output_root.resolve().is_relative_to(input_root):
        raise ValueError('output root must be outside the immutable input root')
    roots = [*MAIN_ROOTS, *(name for group in AMBIG_ROOTS.values() for name in group)]
    loaded = {}
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
            summary = summarize([input_root / name], analysis_root=output_root / 'analyses', decision_overrides=views)
            _write(output_root, name + '-summary.json', summary)
            print(format_summary(summary))
        ambiguous, independent_results = {}, {}
        for label, names in AMBIG_ROOTS.items():
            directories = [r['directory'] for name in names for r in loaded[name]]
            ambiguous[label] = independence.load(directories)
            independent_results[label] = {
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
        command = [sys.executable, '-m', 'fleet_witness.verify_institution', '--depth', '6', '--mutants']
        with (output_root / 'verify-depth6.txt').open('x', encoding='utf-8') as handle:
            result = subprocess.run(command, cwd=REPO, stdout=handle, stderr=subprocess.STDOUT, check=False)
        checker = {'executed': True, 'command': command, 'returncode': result.returncode}
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
                  'input_root': str(input_root), 'input_files_sha256': input_hashes,
                  'inputs_unchanged': True, 'checker': checker,
                  'output_files_sha256': {str(p.relative_to(output_root)): hashlib.sha256(p.read_bytes()).hexdigest()
                                         for p in output_root.rglob('*') if p.is_file()}}
    _write(output_root, 'reproduction-provenance.json', provenance)
    if checker.get('returncode', 0):
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
