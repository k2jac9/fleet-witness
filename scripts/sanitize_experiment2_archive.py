"""Build or verify a path-redacted successor of the pinned public Experiment 2 ZIP.

This is a specific publication transformation, not a general privacy scanner.
No extraction, model calls, credentials, or private-original access is needed.
"""
import argparse
import io
import json
import os
from pathlib import Path
import re
import stat
import sys
import zipfile

try:
    from scripts import verify_experiment2_archive as original
except ModuleNotFoundError:  # Direct invocation from the scripts directory.
    import verify_experiment2_archive as original


SOURCE_SHA256 = '56d38f3dfec31a7c1d87773ff1001f792d105502838342546f0e4a4a12d36eb0'
SOURCE = Path('data/fleet-witness-judge-runs-2026-11-10.zip')
SUCCESSOR = Path('data/fleet-witness-judge-runs-public-2026-11-16.zip')
PREFIX = original.PREFIX
METADATA = 'SANITIZATION.json'
REDACTED = '[REDACTED: machine-local executable path]'
MAX_COMPRESSED = 64 * 1024 * 1024
PRIVACY_PATTERNS = (
    rb'[A-Za-z]:[\\/]+(?:Users|Documents and Settings)[\\/]+',
    rb'/(?:home|Users)/[^/\s"\\]+',
    rb'(?<![A-Za-z0-9_.\\])(?:\\\\){1,2}[A-Za-z0-9_.-]+\\',
    rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',
)


def encoded(value):
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False,
                       allow_nan=False) + '\n').encode('utf-8')


def bounded_bytes(path):
    with Path(path).open('rb') as stream:
        data = stream.read(MAX_COMPRESSED + 1)
    original.require(len(data) <= MAX_COMPRESSED, 'compressed archive size limit')
    return data


def source_bytes(path):
    data = bounded_bytes(path)
    original.require(original.digest(data) == SOURCE_SHA256, 'source archive identity mismatch')
    return data


def privacy_check(data):
    # Report neither the offending value nor its surrounding content.
    original.require(not any(re.search(pattern, data, re.IGNORECASE)
                             for pattern in PRIVACY_PATTERNS),
                     'publication privacy pattern remains')


def transformed(name, data):
    fields = []
    if name.endswith('/manifest.json'):
        manifest = original.decode_json(data)
        original.require(isinstance(manifest, dict), 'invalid run manifest')
        runtime = manifest.get('runtime', {})
        original.require(isinstance(runtime, dict), 'invalid runtime metadata')
        if 'python_executable' in runtime:
            original.require(isinstance(runtime['python_executable'], str)
                             and runtime['python_executable'], 'invalid executable metadata')
            runtime['python_executable'] = REDACTED
            data = encoded(manifest)
            fields = ['/runtime/python_executable']
    privacy_check(data)
    return data, fields


def members(source, source_hash):
    """Yield verified payloads and then a complete mapping, one member at a time."""
    original.verify_hashes(source)
    mapping = {}
    for info in sorted(source.infolist(), key=lambda entry: entry.filename):
        name = info.filename.removeprefix(PREFIX)
        before = source.read(info)
        row = {'source_sha256': original.digest(before), 'source_bytes': len(before)}
        if name in original.METADATA:
            row.update(destination=None, action='superseded packaging metadata')
        else:
            after, fields = transformed(name, before)
            row.update(destination=name, published_sha256=original.digest(after),
                       published_bytes=len(after), changed_fields=fields,
                       action='redact runtime path' if fields else 'unchanged')
            yield name, after
        mapping[name] = row
    manifest = {'schema': 1, 'source_archive_sha256': source_hash, 'files': mapping,
                'redaction': {'json_pointer': '/runtime/python_executable', 'replacement': REDACTED},
                'scope': 'Machine-local executable path redaction of a pinned public archive. '
                         'Historical synthetic-key substitutions remain unchanged. '
                         'Original packaging metadata is mapped by hash, not copied. '
                         'No private-original preservation or exhaustive privacy claim.'}
    yield METADATA, encoded(manifest)


def write_successor(source, destination, source_hash):
    for name, data in members(source, source_hash):
        info = zipfile.ZipInfo(PREFIX + name, (2026, 11, 16, 0, 0, 0))
        info.create_system = 3
        info.external_attr = (stat.S_IFREG | 0o644) << 16
        info.compress_type = zipfile.ZIP_DEFLATED
        destination.writestr(info, data, compresslevel=9)


def compare_successor(source, successor, source_hash):
    """Compare all bytes to the allowed transform; do not trust supplied hashes."""
    entries = successor.infolist()
    original.require(0 < len(entries) <= 1000, 'archive entry limit')
    original.require(sum(e.file_size for e in entries) <= 256 * 1024 * 1024,
                     'archive total size limit')
    original.require(not successor.comment, 'unexpected ZIP metadata')
    names = set()
    for entry in entries:
        name = entry.filename
        original.require(name == entry.orig_filename and name.startswith(PREFIX)
                         and original.safe_name(name) and not entry.is_dir(), 'unsafe archive member')
        original.require(name not in names, 'duplicate archive member')
        names.add(name)
        original.require(stat.S_IFMT(entry.external_attr >> 16) in (0, stat.S_IFREG)
                         and not entry.flag_bits & 1, 'unsupported archive member type')
        original.require(not entry.comment and not entry.extra, 'unexpected ZIP metadata')
        original.require(entry.file_size <= 32 * 1024 * 1024, 'archive member size limit')
        if name == PREFIX + METADATA:
            original.require(entry.file_size <= 1024 * 1024, 'archive metadata size limit')
    expected_names = set()
    manifest = None
    for name, expected in members(source, source_hash):
        full_name = PREFIX + name
        expected_names.add(full_name)
        original.require(full_name in names, 'successor member missing')
        original.require(successor.read(full_name) == expected, 'successor differs from allowed transformation')
        if name == METADATA:
            manifest = original.decode_json(expected)
    original.require(expected_names == names, 'successor membership mismatch')
    rows = list(manifest['files'].values())
    return {'source_archive_sha256': source_hash,
            'changed_manifests': sum(row['action'] == 'redact runtime path' for row in rows),
            'unchanged_data_members': sum(row['action'] == 'unchanged' for row in rows),
            'omitted_packaging_members': sum(row['destination'] is None for row in rows),
            'successor_members': len(entries),
            'sanitization_manifest_sha256': original.digest(encoded(manifest)),
            'privacy_scope': 'Declared home-directory/UNC path and private-key markers only; '
                             'not an exhaustive privacy or credential audit.'}


def build(source, destination):
    destination = Path(destination)
    if os.path.lexists(destination):
        raise FileExistsError('destination already exists; preserve it and choose a fresh path')
    data = source_bytes(source)
    with zipfile.ZipFile(io.BytesIO(data)) as old:
        original.verify_hashes(old)
        # Exclusive mode also refuses a destination created after the first check.
        # Any partial output on failure is retained as evidence, never silently deleted.
        with destination.open('xb') as stream, zipfile.ZipFile(stream, 'w') as new:
            write_successor(old, new, SOURCE_SHA256)
    return {'archive_sha256': original.digest(bounded_bytes(destination)),
            'source_archive_sha256': SOURCE_SHA256}


def verify(source, successor, aggregates):
    source_data, successor_data = source_bytes(source), bounded_bytes(successor)
    with zipfile.ZipFile(io.BytesIO(source_data)) as old, zipfile.ZipFile(io.BytesIO(successor_data)) as new:
        comparison = compare_successor(old, new, SOURCE_SHA256)
    baseline = original.verify(Path(source), Path(aggregates))
    original.require(baseline['archive_sha256'] == SOURCE_SHA256, 'source changed during verification')
    return {'schema': 1, 'archive_sha256': original.digest(successor_data),
            'publication_verifier_sha256': original.digest(Path(__file__).read_bytes()),
            'comparison': comparison, 'source_verification': baseline,
            'qualification': 'Experimental data bytes are unchanged; the source verification '
                             'applies to the successor. This is not a new experiment or human reproduction.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    builder = commands.add_parser('build')
    builder.add_argument('--source', type=Path, default=SOURCE)
    builder.add_argument('--output', type=Path, required=True)
    checker = commands.add_parser('verify')
    checker.add_argument('--source', type=Path, default=SOURCE)
    checker.add_argument('--archive', type=Path, default=SUCCESSOR)
    checker.add_argument('--aggregates', type=Path, default=Path('docs/report/experiment2'))
    args = parser.parse_args()
    try:
        result = build(args.source, args.output) if args.command == 'build' else verify(
            args.source, args.archive, args.aggregates)
    except (ValueError, KeyError, TypeError, OSError, zipfile.BadZipFile) as exc:
        print('Experiment 2 publication failed: ' + str(exc), file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
    return int(bool(result.get('source_verification', {}).get(
        'frozen_aggregate_comparison', {}).get('mismatches')))


if __name__ == '__main__':
    raise SystemExit(main())
