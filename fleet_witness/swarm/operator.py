"""Load explicit private operator authorizations; never issue or infer one."""
import json
import os
from pathlib import Path
import stat
import subprocess


def require_committed_source(root=None):
    """Paid entrypoints run only a committed tree; review acceptance is still external."""
    root = Path(root) if root is not None else Path(__file__).resolve().parents[2]
    try:
        result = subprocess.run(['git', '-C', str(root), 'status', '--porcelain',
                                 '--untracked-files=normal'], check=True,
                                capture_output=True, text=True, timeout=5)
        subprocess.run(['git', '-C', str(root), 'rev-parse', '--verify', 'HEAD'],
                       check=True, capture_output=True, timeout=5)
    except (OSError, subprocess.SubprocessError):
        raise ValueError('paid execution requires verified committed source') from None
    if result.stdout.strip():
        raise ValueError('paid execution requires a clean committed source tree')


def _object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate authorization field')
        result[key] = value
    return result


def load_authorizations(path):
    if path is None:
        raise ValueError('paid requests require --authorization with a qualified operator record')
    descriptor = os.open(Path(path), os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(descriptor, 'rb') as handle:
        metadata = os.fstat(handle.fileno())
        if (not stat.S_ISREG(metadata.st_mode) or metadata.st_uid != os.getuid()
                or metadata.st_nlink != 1 or metadata.st_mode & 0o077):
            raise ValueError('authorization must be an owner-private singly-linked regular file')
        raw = handle.read(262145)
    if len(raw) > 262144:
        raise ValueError('authorization exceeds the byte limit')
    def reject_constant(value):
        raise ValueError('authorization numbers must be finite')
    data = json.loads(raw, object_pairs_hook=_object, parse_constant=reject_constant)
    records = (data.get('authorizations') if isinstance(data, dict)
               and data.get('schema_version') == 'swarm-authorizations-v1' else [data])
    if not isinstance(records, list) or not 1 <= len(records) <= 64:
        raise ValueError('authorization must contain one to 64 explicit model records')
    indexed = {}
    for record in records:
        if not isinstance(record, dict):
            raise ValueError('authorization record must be an object')
        provider, model = record.get('provider'), record.get('model')
        if not isinstance(provider, str) or not isinstance(model, str):
            raise ValueError('authorization must name an explicit provider and model')
        if (provider, model) in indexed:
            raise ValueError('duplicate provider/model authorization')
        indexed[provider, model] = record
    return indexed


def authorized_client(provider, model, authorization_path, *, max_usd=None,
                      max_output_tokens=None, max_concurrency=1, temperature=0.7, timeout=None):
    """Create a client only from the selected explicit record, with no implicit cap changes."""
    records = load_authorizations(authorization_path)
    require_committed_source()
    record = records.get((provider, model))
    if record is None:
        raise ValueError('no authorization for the selected provider/model')
    from .providers import Ledger, ModelClient, validate_record
    record = validate_record(record)
    required = ('run_cap_usd', 'provider_cap_usd', 'ledger_path', 'run_id',
                'max_output_tokens', 'timeout_s')
    if any(field not in record for field in required):
        raise ValueError('authorization is missing its execution bounds')
    if max_usd is not None and float(max_usd) != float(record['run_cap_usd']):
        raise ValueError('--max-usd must match the immutable authorized run cap')
    if max_output_tokens is not None and max_output_tokens != record['max_output_tokens']:
        raise ValueError('--max-output-tokens must match the authorized token cap')
    if max_concurrency != 1:
        raise ValueError('the accepted paid envelope allows one in-flight request')
    if timeout is not None and timeout != record['timeout_s']:
        raise ValueError('timeout must match the authorized request deadline')
    ledger = Ledger(provider, run_cap_usd=record['run_cap_usd'],
                    lifetime_cap_usd=record['provider_cap_usd'],
                    path=Path(record['ledger_path']), run_id=record['run_id'])
    return ModelClient(provider, model, ledger, authorization=record,
                       max_output_tokens=record['max_output_tokens'], temperature=temperature,
                       timeout=record['timeout_s'], max_concurrency=1)


def authorized_clients(provider, models, authorization_path, **kwargs):
    """A multi-model job consumes one explicitly shared run envelope."""
    from .providers import validate_record
    records = load_authorizations(authorization_path)
    require_committed_source()
    selected = []
    for model in sorted(set(models)):
        record = records.get((provider, model))
        if record is None:
            raise ValueError('every requested model needs an explicit authorization')
        selected.append(validate_record(record))
    envelopes = {(r['ledger_path'], r['run_id'], str(r['run_cap_usd']), str(r['provider_cap_usd']),
                  r['request_limit'], r['expires_at']) for r in selected}
    if len(envelopes) != 1:
        raise ValueError('multi-model jobs require one shared authorized run envelope')
    return {model: authorized_client(provider, model, authorization_path, **kwargs)
            for model in sorted(set(models))}
