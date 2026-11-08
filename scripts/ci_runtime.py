#!/usr/bin/env python3
"""Offline verification of selected runtime artifacts and executed CI identities."""
import argparse
from datetime import date
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]


def validate_manifest(data):
    if data.get('schema') != 1 or data.get('platform') != 'ubuntu-24.04-x64':
        raise ValueError('unsupported runtime manifest')
    if date.fromisoformat(data['review_due']) < date.fromisoformat(data['verified_at']):
        raise ValueError('invalid freshness interval')
    seen = set()
    roles = {'python': set(), 'node': set()}
    for lane in data['lanes']:
        if lane['id'] in seen:
            raise ValueError('duplicate runtime lane')
        seen.add(lane['id'])
        if not re.fullmatch(r'[a-zA-Z0-9.\-]+', lane['id']):
            raise ValueError('invalid lane identity')
        if not re.fullmatch(r'\d+\.\d+\.\d+(?:(?:a|b|rc)\d+|-alpha(?:\.\d+)+)?', lane['version']):
            raise ValueError('exact runtime version required')
        if not re.fullmatch(r'[0-9a-f]{64}', lane['sha256']):
            raise ValueError('exact artifact digest required')
        family = lane['family']
        if family not in roles:
            raise ValueError('unknown runtime family')
        url = urlsplit(lane['url'])
        allowed = ('github.com', '/actions/python-versions/releases/download/') if family == 'python' else ('nodejs.org', '/dist/')
        if (url.scheme != 'https' or url.hostname != allowed[0] or not url.path.startswith(allowed[1])
                or url.username or url.password or url.port or url.query or url.fragment):
            raise ValueError('runtime artifact must use the official HTTPS release location')
        roles[family].add(lane['role'])
    if any(not {'stable', 'upcoming', 'previous'} <= r for r in roles.values()):
        raise ValueError('required stable/upcoming/previous roles missing')
    return data


def load_manifest():
    return validate_manifest(json.loads((ROOT / 'ci/runtime-matrix.json').read_text()))


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def verify_archive(path, expected):
    actual = digest(path)
    if actual != expected:
        raise ValueError('runtime archive digest mismatch')
    return actual


def runtime_identity(family, expected):
    if family == 'python':
        executable = Path(sys.executable).resolve()
        version = platform.python_version()
    elif family == 'node':
        executable = Path(shutil.which('node') or '/missing-node').resolve()
        version = subprocess.check_output([str(executable), '--version'], text=True).strip().removeprefix('v')
    else:
        raise ValueError('unknown runtime family')
    if version != expected:
        raise ValueError(f'actual runtime version {version} differs from selected {expected}')
    return {'family': family, 'version': version, 'executable': str(executable),
            'executable_sha256': digest(executable)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['matrix', 'verify-archive', 'identity', 'freshness'])
    parser.add_argument('--lane')
    parser.add_argument('--archive', type=Path)
    args = parser.parse_args()
    manifest = load_manifest()
    if args.command == 'matrix':
        print(json.dumps({'include': manifest['lanes']}, separators=(',', ':')))
        return
    if args.command == 'freshness':
        if not date.fromisoformat(manifest['verified_at']) <= date.today() <= date.fromisoformat(manifest['review_due']):
            raise ValueError('runtime selections require a fresh upstream review')
        print('runtime selections are within their recorded review interval')
        return
    lane = next((x for x in manifest['lanes'] if x['id'] == args.lane), None)
    if lane is None:
        raise ValueError('unknown runtime lane')
    if args.command == 'verify-archive':
        print(verify_archive(args.archive, lane['sha256']))
        return
    result = runtime_identity(lane['family'], lane['version'])
    result.update(lane=lane, source_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                  flake_lock_sha256=digest(ROOT / 'flake.lock'), matrix_sha256=digest(ROOT / 'ci/runtime-matrix.json'),
                  platform=platform.platform(), architecture=platform.machine(),
                  runner_image=os.environ.get('ImageOS'), runner_image_version=os.environ.get('ImageVersion'),
                  workflow_run=os.environ.get('GITHUB_RUN_ID'), workflow_attempt=os.environ.get('GITHUB_RUN_ATTEMPT'))
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
