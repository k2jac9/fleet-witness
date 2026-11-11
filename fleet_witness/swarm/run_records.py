"""Bounded private run receipts and public accounting views; no provider I/O."""
import hashlib
from functools import lru_cache
import json
import math
import os
from pathlib import Path
import platform
import sys
import threading
import zipfile

from .providers import STRICT_SWARM_PARSER

ATTEMPT_FIELDS = frozenset({
    'attempt_id', 'provider', 'model', 'status', 'provider_request_id', 'provider_attempts',
    'input_tokens', 'output_tokens', 'cost_usd', 'held_usd', 'reserved_usd',
    'request_sha256', 'response_sha256', 'latency_s', 'finish_reason', 'truncated',
    'http_status', 'error_code',
})
MAX_PRIVATE_TEXT_BYTES = 65536
HISTORICAL_ARCHIVE_SHA256 = 'c55e8acf07ed8dd3c11bc3dc8f70269adebaac6bfa14727642cca7314d1f821a'
RUN_INPUTS = ('manifest.json', 'truth.json', 'events.jsonl', 'decisions.json')


@lru_cache(maxsize=2)
def _historical_fingerprints(archive, identity):
    """Hash members only after verifying the full preserved archive."""
    if hashlib.sha256(archive.read_bytes()).hexdigest() != HISTORICAL_ARCHIVE_SHA256:
        raise ValueError('historical archive identity mismatch')
    index = {}
    with zipfile.ZipFile(archive) as source:
        for info in source.infolist():
            parts = info.filename.replace('\\', '/').split('/')
            if len(parts) == 4 and parts[0] == 'runs' and parts[-1] in RUN_INPUTS:
                if info.file_size > 32 * 1024 * 1024:
                    raise ValueError('historical member exceeds limit')
                key = (parts[1], parts[2])
                row = index.setdefault(key, {})
                if parts[-1] in row:
                    raise ValueError('duplicate historical member')
                row[parts[-1]] = hashlib.sha256(source.read(info)).hexdigest()
    return {key: value for key, value in index.items() if set(value) == set(RUN_INPUTS)}


def classify_run_treatment(directory):
    """Classify a completed run; legacy identity binds path and all raw inputs."""
    directory = Path(directory)
    try:
        raw = (directory / 'manifest.json').read_bytes()
        manifest = json.loads(raw)
        if not isinstance(manifest, dict):
            raise ValueError('invalid treatment manifest')
        treatment = manifest.get('parser_treatment')
        if treatment == STRICT_SWARM_PARSER:
            start = json.loads((directory / 'run-start.json').read_text(encoding='utf-8'))
            if (not isinstance(start, dict) or start.get('schema_version') != 'swarm-run-start-v1' or
                    start.get('parser_treatment') != treatment or start.get('source') != manifest.get('source')):
                raise ValueError('run start and parser treatment mismatch')
            return treatment
        if treatment is None:
            archive = Path(__file__).resolve().parents[2] / 'data/fleet-witness-runs-2026-11-08.zip'
            info = archive.stat()
            identity = (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)
            legacy_fingerprints = _historical_fingerprints(archive, identity)
            key = (directory.parent.name, directory.name)
            expected = legacy_fingerprints.get(key)
            actual = {name: hashlib.sha256((directory / name).read_bytes()).hexdigest() for name in RUN_INPUTS}
            if expected is not None and expected == actual:
                return 'legacy-recorded'
        raise ValueError('unknown or unverified parser treatment')
    except (OSError, TypeError, ValueError, AttributeError, RecursionError) as error:
        raise ValueError(f'invalid parser treatment: {error}') from None


def prompt_digest(system, user):
    encoded = json.dumps({'system': system, 'user': user}, sort_keys=True,
                         separators=(',', ':'), ensure_ascii=False).encode('utf-8')
    return hashlib.sha256(encoded).hexdigest()


def public_attempts(attempts):
    """Copy scalar accounting fields only; prompts and raw responses stay private."""
    output = []
    for attempt in attempts:
        if not isinstance(attempt, dict):
            raise ValueError('attempt metadata must be an object')
        row = {}
        for key in ATTEMPT_FIELDS & attempt.keys():
            value = attempt[key]
            if value is None or type(value) in (bool, int):
                row[key] = value
            elif type(value) is float and math.isfinite(value):
                row[key] = value
            elif isinstance(value, str) and len(value) <= 256:
                row[key] = value
            else:
                raise ValueError('unbounded or non-scalar attempt metadata')
        output.append(row)
    return output


def runtime_identity():
    return {'python_version': platform.python_version(),
            'python_implementation': platform.python_implementation(),
            'python_executable': sys.executable, 'platform': sys.platform,
            'machine': platform.machine()}


def _bounded_text(value):
    if value is None:
        return None, False
    encoded = value.encode('utf-8')
    return encoded[:MAX_PRIVATE_TEXT_BYTES].decode('utf-8', 'ignore'), len(encoded) > MAX_PRIVATE_TEXT_BYTES


class PrivateRunLog:
    def __init__(self, output: Path):
        directory = output / 'private'
        directory.mkdir(mode=0o700)
        descriptor = os.open(directory / 'requests.jsonl',
                             os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        try:
            os.fchmod(descriptor, 0o600)
        except BaseException:
            os.close(descriptor)
            raise
        self._handle = os.fdopen(descriptor, 'w', encoding='utf-8')
        self._lock = threading.Lock()
        self._attempts = []
        self._logical_requests = 0

    def write(self, logical_request_id, system, user, response_text, status, attempts):
        system_text, system_cut = _bounded_text(system)
        user_text, user_cut = _bounded_text(user)
        response, response_cut = _bounded_text(response_text)
        receipt = {'logical_request_id': logical_request_id, 'prompt_sha256': prompt_digest(system, user),
                   'request': {'system': system_text, 'user': user_text},
                   'response_text': response, 'status': status, 'attempts': attempts,
                   'retention_truncated': {'system': system_cut, 'user': user_cut, 'response': response_cut}}
        with self._lock:
            self._handle.write(json.dumps(receipt, sort_keys=True, ensure_ascii=False, allow_nan=False) + '\n')
            self._handle.flush()
            os.fsync(self._handle.fileno())
            self._attempts.extend(attempts)
            self._logical_requests += 1

    def summary(self):
        with self._lock:
            return {'logical_requests': self._logical_requests,
                    'provider_attempts': sum(a.get('provider_attempts', 0) for a in self._attempts),
                    'reservations': len(self._attempts),
                    'attempt_ids': [a['attempt_id'] for a in self._attempts],
                    'cost_usd': round(sum(a.get('cost_usd') or 0.0 for a in self._attempts), 9),
                    'held_usd': round(sum(a.get('held_usd') or 0.0 for a in self._attempts), 9)}

    def close(self):
        self._handle.close()
