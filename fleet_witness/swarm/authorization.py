"""Validate operator assertions; this module does not issue spending authority.

A record must be supplied by the trusted operator after independent verification.
Booleans and evidence hashes record those attestations; they are not signatures,
provider verification, or protection against a malicious host/operator.
"""
import hashlib
import json
from pathlib import Path
import re
import subprocess
import time
from types import SimpleNamespace

from .ledger import ProviderError, canonical_json, decimal_usd, units

ADAPTION_URL = 'https://api.prod.adaptionlabs.ai/api/v1/responses'
OPENROUTER_URL = 'https://openrouter.ai/api/v1/chat/completions'
ENDPOINTS = {'adaption': ADAPTION_URL, 'openrouter': OPENROUTER_URL}


def source_identity():
    """SHA-256 of canonical JSON mapping package-relative Python paths to hashes."""
    root = Path(__file__).resolve().parents[2]
    files = {str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
             for path in sorted((root / 'fleet_witness').rglob('*.py'))}
    try:
        commit = subprocess.run(['git', '-C', str(root), 'rev-parse', 'HEAD'], check=True,
                                capture_output=True, text=True, timeout=5).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        commit = None
    return {'source_commit': commit, 'source_sha256': hashlib.sha256(canonical_json(files).encode()).hexdigest(),
            'source_files': files, 'digest_algorithm': 'sha256-canonical-json-file-map-v1'}


def _integer(value, low, high):
    return type(value) is int and low <= value <= high


def _hash(value):
    return isinstance(value, str) and re.fullmatch(r'[0-9a-f]{64}', value) is not None


def validate_authorization(value, *, provider, model, ledger, max_output_tokens, timeout):
    """Return detached qualified metadata, before any credential or network I/O."""
    try:
        if not isinstance(value, dict):
            raise ValueError('explicit operator authorization required')
        required = {'schema_version', 'authorization_id', 'approved_by', 'purpose', 'issued_at', 'expires_at',
                    'source_commit', 'source_sha256', 'provider', 'model', 'endpoint', 'ledger_path', 'run_id',
                    'run_cap_usd', 'provider_cap_usd', 'request_limit', 'max_input_bytes', 'max_output_tokens',
                    'max_response_bytes', 'timeout_s', 'pricing', 'qualification'}
        controlled = value.get('schema_version') == 'controlled-openrouter-v1'
        if controlled:
            required.add('openrouter')
        if set(value) != required or value['schema_version'] not in ('swarm-paid-v1', 'controlled-openrouter-v1'):
            raise ValueError('invalid operator authorization schema')
        checked = json.loads(canonical_json(value))
        for name in ('authorization_id', 'approved_by', 'model', 'run_id'):
            if not isinstance(checked[name], str) or not re.fullmatch(r'[A-Za-z0-9._:/@ -]{1,128}', checked[name]):
                raise ValueError('invalid authorization identity')
        now = time.time()
        if (not _integer(checked['issued_at'], 1, 2**53) or
                not _integer(checked['expires_at'], 1, 2**53) or
                not checked['issued_at'] <= now < checked['expires_at'] or
                checked['expires_at'] - checked['issued_at'] > 86400):
            raise ValueError('authorization expired or outside one-day envelope')
        source = source_identity()
        if (not isinstance(checked['source_commit'], str) or not re.fullmatch(r'[0-9a-f]{40}', checked['source_commit']) or
                not _hash(checked['source_sha256']) or
                checked['source_commit'] != source['source_commit'] or checked['source_sha256'] != source['source_sha256']):
            raise ValueError('authorization source identity does not match executing source')
        if (provider not in ENDPOINTS or checked['provider'] != provider or checked['model'] != model or
                checked['endpoint'] != ENDPOINTS[provider] or checked['ledger_path'] != str(ledger.path) or
                ledger.provider != provider or checked['run_id'] != ledger.run_id or
                units(checked['run_cap_usd'], exact=True) != units(ledger.run_cap, exact=True) or
                units(checked['provider_cap_usd'], exact=True) != units(ledger.lifetime_cap, exact=True)):
            raise ValueError('authorization provider/model/ledger/budget mismatch')
        if provider == 'adaption' and not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,127}', model):
            raise ValueError('Adaption requires a direct model identifier')
        for name, low, high in (('request_limit', 1, 100000), ('max_input_bytes', 1, 262144),
                                ('max_output_tokens', 1, 16000), ('max_response_bytes', 1, 1048576)):
            if not _integer(checked[name], low, high):
                raise ValueError('invalid authorization limit')
        if (not _integer(max_output_tokens, 1, checked['max_output_tokens']) or
                isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or
                isinstance(checked['timeout_s'], bool) or not isinstance(checked['timeout_s'], (int, float)) or
                not 0 < timeout <= checked['timeout_s'] <= 30):
            raise ValueError('request exceeds authorized token/deadline limit')
        pricing = checked['pricing']
        if not isinstance(pricing, dict) or set(pricing) != {'unit', 'input_per_million', 'output_per_million',
                'verified_at', 'evidence_sha256', 'all_billable_tokens_included'}:
            raise ValueError('invalid verified pricing record')
        if (pricing['unit'] != 'USD' or pricing['all_billable_tokens_included'] is not True or
                not _hash(pricing['evidence_sha256']) or not _integer(pricing['verified_at'], 1, checked['issued_at'])):
            raise ValueError('USD conversion/all billable usage must be independently verified')
        for name in ('input_per_million', 'output_per_million'):
            decimal_usd(pricing[name])
        qualification = checked['qualification']
        if not isinstance(qualification, dict) or set(qualification) != {'access_verified', 'retention_reviewed',
                'transport_reviewed', 'calibration_accepted', 'evidence_sha256'}:
            raise ValueError('invalid qualification record')
        if (checked['purpose'] not in ('calibration', 'confirmatory') or
                any(qualification[name] is not True for name in ('access_verified', 'retention_reviewed', 'transport_reviewed')) or
                not isinstance(qualification['calibration_accepted'], bool) or
                not _hash(qualification['evidence_sha256']) or
                (checked['purpose'] == 'confirmatory' and qualification['calibration_accepted'] is not True)):
            raise ValueError('provider qualification incomplete')
        if controlled:
            from .openrouter_controlled import validate_profile
            validate_profile(checked)
        return checked
    except (ValueError, TypeError, KeyError, OverflowError):
        raise ProviderError('explicit source-bound, unexpired, verified operator authorization required') from None


def validate_record(record):
    """Validate a candidate before creating/opening its ledger (source reads only)."""
    try:
        if not isinstance(record, dict):
            raise ValueError('authorization must be an object')
        path = Path(record['ledger_path'])
        if not path.is_absolute() or str(path.resolve()) != record['ledger_path']:
            raise ValueError('ledger path must be canonical and absolute')
        ledger = SimpleNamespace(path=path, provider=record['provider'], run_id=record['run_id'],
                                 run_cap=record['run_cap_usd'], lifetime_cap=record['provider_cap_usd'])
        return validate_authorization(record, provider=record['provider'], model=record['model'], ledger=ledger,
                                      max_output_tokens=record['max_output_tokens'], timeout=record['timeout_s'])
    except (KeyError, TypeError, ValueError, OSError):
        raise ProviderError('invalid operator authorization record') from None
