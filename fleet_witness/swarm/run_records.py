"""Bounded private run receipts and public accounting views; no provider I/O."""
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import sys
import threading

ATTEMPT_FIELDS = frozenset({
    'attempt_id', 'provider', 'model', 'status', 'provider_request_id', 'provider_attempts',
    'input_tokens', 'output_tokens', 'cost_usd', 'held_usd', 'reserved_usd',
    'request_sha256', 'response_sha256', 'latency_s', 'finish_reason', 'truncated',
    'http_status', 'error_code',
})
MAX_PRIVATE_TEXT_BYTES = 65536


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
