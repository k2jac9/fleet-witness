"""Extract a bounded run ZIP to a fresh directory, including Windows-path archives.

No archive path is trusted. All members are validated before the destination is
created. Existing destinations, links, aliases, special files and overwrites are
refused. This is a local import helper, not a sandbox for concurrent hostile users.
"""
import argparse
import hashlib
import json
from pathlib import Path
import stat
import unicodedata
import zipfile

WINDOWS_DEVICES = {'con', 'prn', 'aux', 'nul', *(f'com{i}' for i in range(1, 10)),
                   *(f'lpt{i}' for i in range(1, 10))}


def extract_archive(archive, destination, *, max_entries=1000, max_total_bytes=128 * 1024 * 1024,
                    max_file_bytes=32 * 1024 * 1024, max_ratio=200):
    archive, destination = Path(archive), Path(destination).absolute()
    if any(value <= 0 for value in (max_entries, max_total_bytes, max_file_bytes, max_ratio)):
        raise ValueError('archive bounds must be positive')
    for parent in (destination, *destination.parents):
        if parent.is_symlink():
            raise ValueError(f'symlink destination path: {parent}')
    if destination.exists() or not destination.parent.is_dir():
        raise ValueError('destination must be new, with an existing directory parent')
    with zipfile.ZipFile(archive) as z:
        entries = z.infolist()
        if not entries or len(entries) > max_entries:
            raise ValueError('empty archive or entry limit exceeded')
        planned, names, spellings, required_dirs, total = [], {}, {}, set(), 0
        for info in entries:
            raw = info.orig_filename.replace('\\', '/')
            directory = raw.endswith('/')
            name = raw[:-1] if directory else raw
            parts = name.split('/')
            if (not name or any(part in ('', '.', '..') or ':' in part or '\x00' in part
                                or part.endswith((' ', '.')) or any(ord(c) < 32 for c in part)
                                or part.split('.')[0].casefold() in WINDOWS_DEVICES
                                for part in parts)):
                raise ValueError(f'unsafe archive path: {info.orig_filename!r}')
            # Case folding and Unicode normalization also reject aliases on common
            # Windows/macOS filesystems, even when extraction happens on Linux.
            key = '/'.join(unicodedata.normalize('NFC', part).casefold() for part in parts)
            for i in range(1, len(parts) + 1):
                prefix, spelling = '/'.join(key.split('/')[:i]), '/'.join(parts[:i])
                if prefix in spellings and spellings[prefix] != spelling:
                    raise ValueError(f'archive directory alias collision: {info.orig_filename!r}')
                spellings[prefix] = spelling
            parents = {'/'.join(key.split('/')[:i]) for i in range(1, len(parts))}
            mode = stat.S_IFMT(info.external_attr >> 16)
            if mode not in (0, stat.S_IFDIR if directory else stat.S_IFREG) or info.flag_bits & 1:
                raise ValueError('links, special files and encrypted members are not supported')
            if (key in names or any(names.get(p) is False for p in parents)
                    or (not directory and key in required_dirs)):
                raise ValueError(f'archive path collision: {info.orig_filename!r}')
            if directory and info.file_size:
                raise ValueError('directory member contains data')
            names[key] = directory
            required_dirs.update(parents)
            total += info.file_size
            if (info.file_size > max_file_bytes or total > max_total_bytes
                    or info.file_size > max_ratio * max(1, info.compress_size)):
                raise ValueError('archive expansion limit exceeded')
            planned.append((info, destination.joinpath(*parts), directory))
        destination.mkdir(mode=0o700)
        written = 0
        for info, target, directory in planned:
            if directory:
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            count = 0
            with z.open(info) as source, target.open('xb') as output:
                while block := source.read(65536):
                    count += len(block)
                    written += len(block)
                    if count > info.file_size or count > max_file_bytes or written > max_total_bytes:
                        raise ValueError('streamed archive expansion limit exceeded')
                    output.write(block)
            if count != info.file_size:
                raise ValueError('archive member length mismatch')
    return {'archive': str(archive.resolve()), 'archive_sha256': hashlib.sha256(archive.read_bytes()).hexdigest(),
            'destination': str(destination), 'entries': len(planned), 'uncompressed_bytes': written}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', type=Path, required=True)
    parser.add_argument('--destination', type=Path, required=True)
    args = parser.parse_args(argv)
    print(json.dumps(extract_archive(args.archive, args.destination), indent=2, allow_nan=False))


if __name__ == '__main__':
    main()
