"""Package the original Experiment 2 run directories as one shareable ZIP (issue #17).

Reads the local, gitignored run folders and never modifies them. The only change made to the
published copy is replacing the synthetic Stripe-style key from case 02 with a placeholder, so
GitHub secret scanning does not flag the archive. The key was never a real credential.

The ZIP contains, with forward-slash paths and fixed timestamps:
  experiment2-runs/<run folder>/...      cleaned copies of every file
  experiment2-runs/SHA256SUMS-original   hashes of the untouched local files
  experiment2-runs/SHA256SUMS-published  hashes of the files as published in this ZIP
  experiment2-runs/CHANGES.json          which files were changed and how many replacements

Usage:
  python scripts/package_experiment2_runs.py --out data/fleet-witness-judge-runs-2026-11-10.zip
"""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile

RUN_FOLDERS = ['judge', 'judge-frontier', 'judge-v1-stopped', 'judge-frontier-v1-stopped', 'judge-pilot']
FAKE_KEY = ('sk_' + 'live_' + '51HqLyjKpZ8vX2mN4bR7tQ9wE3sD6fG1hJ0kL').encode()
PLACEHOLDER = b'sk_live_FAKE-KEY-REMOVED'
PREFIX = 'experiment2-runs'
STAMP = (2026, 11, 10, 0, 0, 0)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--runs', type=Path, default=Path('runs'))
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        parser.error(f'{args.out} already exists')
    files = sorted(f for folder in RUN_FOLDERS for f in (args.runs / folder).rglob('*') if f.is_file())
    original, published, changes = [], [], {}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(args.out, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        def add(name, data):
            info = zipfile.ZipInfo(f'{PREFIX}/{name}', STAMP)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, data)

        for path in files:
            name = path.relative_to(args.runs).as_posix()
            data = path.read_bytes()
            original.append(f'{hashlib.sha256(data).hexdigest()}  {name}')
            count = data.count(FAKE_KEY)
            if count:
                data = data.replace(FAKE_KEY, PLACEHOLDER)
                changes[name] = {'fake_key_replacements': count}
            published.append(f'{hashlib.sha256(data).hexdigest()}  {name}')
            add(name, data)
        add('SHA256SUMS-original', '\n'.join(original) + '\n')
        add('SHA256SUMS-published', '\n'.join(published) + '\n')
        add('CHANGES.json', json.dumps({
            'replacement': 'synthetic Stripe-style key from case 02 -> sk_live_FAKE-KEY-REMOVED',
            'note': 'prompt_sha256 values in events.jsonl hash the original, unreplaced prompts',
            'files_changed': changes}, indent=2) + '\n')
    digest = hashlib.sha256(args.out.read_bytes()).hexdigest()
    print(f'{len(files)} files, {len(changes)} cleaned, {args.out.stat().st_size / 2**20:.1f} MiB, sha256 {digest}')


if __name__ == '__main__':
    main()
