"""Research-script glue for the existing authorized client and private receipts.

This module grants no authority, implements no transport and keeps no separate
balance. ModelClient and its canonical SQLite ledger own dispatch/accounting.
"""
import json
import os
from pathlib import Path
import uuid

from fleet_witness.swarm.operator import authorized_clients, load_authorizations
from fleet_witness.swarm.providers import ProviderError
from fleet_witness.swarm.ledger import decimal_usd
from fleet_witness.swarm.run_records import PrivateRunLog, public_attempts


def paid_arguments(parser):
    parser.add_argument('--authorization', type=Path, required=True,
                        help='owner-private source-bound operator authorization (never created by this script)')
    parser.add_argument('--live', action='store_true', help='explicitly select authorized paid execution')
    parser.add_argument('--max-usd', help='optional assertion; must match the immutable authorized run cap')
    parser.add_argument('--max-tokens', type=int,
                        help='optional assertion; must match the authorized output-token cap')


def research_clients(models, authorization, *, live=False, max_usd=None, max_output_tokens=None,
                     temperature=.7, reasoning=None, max_run_usd=None):
    """Validate the entire shared model envelope before allowing the first call."""
    if live is not True:
        raise ValueError('paid research requires explicit --live and --authorization')
    if os.name != 'posix':
        raise ValueError('the qualified paid client requires a POSIX host; Windows flag shims are refused')
    models = sorted(set(models))
    records = load_authorizations(authorization)
    purposes = []
    for model in models:
        record = records.get(('openrouter', model))
        if record is None or record.get('schema_version') != 'swarm-paid-v1':
            raise ValueError('every research model requires an explicit swarm-paid-v1 authorization')
        if max_run_usd is not None and decimal_usd(record['run_cap_usd']) > decimal_usd(max_run_usd):
            raise ValueError(f'research run cap must not exceed ${max_run_usd}')
        purposes.append(record.get('purpose'))
    if any(purpose != purposes[0] for purpose in purposes[1:]):
        raise ValueError('all research models must share the same authorized purpose')
    if reasoning is not None and reasoning not in ('none', 'minimal', 'low', 'medium', 'high'):
        raise ValueError('unsupported reasoning effort')
    clients = authorized_clients('openrouter', models, authorization, max_usd=max_usd,
                                 max_output_tokens=max_output_tokens, temperature=temperature)
    if reasoning is not None:
        for client in clients.values():
            client.extra_body = {'reasoning': {'effort': reasoning}}
    return clients


def strict_object(text):
    """Parse a whole JSON object; prose, duplicate keys and nonfinite values fail."""
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('duplicate response field')
            result[key] = value
        return result

    def constant(value):
        raise ValueError('nonfinite response number')

    result = json.loads(text, object_pairs_hook=unique, parse_constant=constant)
    if not isinstance(result, dict):
        raise ValueError('required response must be a JSON object')
    return result


class ResearchRequests:
    """Record each required stage, including invalid output and final failures."""
    def __init__(self, output):
        self.receipts = PrivateRunLog(Path(output))
        self.calls = []

    def call(self, client, system, user, label, *, validate=None):
        if not isinstance(system, str) or not isinstance(user, str):
            raise ValueError('only qualified text inputs are supported; image mode is unavailable')
        identity = uuid.uuid4().hex
        result, response, attempts, status = None, None, [], 'refused'
        try:
            result = client.complete(system, user)
            response = result['text']
            attempts = public_attempts(result.get('attempts', []))
            status = result.get('status', 'invalid_output')
            if result.get('truncated') or status != 'succeeded':
                raise ProviderError('required response incomplete; no retry', attempts=attempts,
                                    status='truncated' if result.get('truncated') else status)
            if not isinstance(response, str) or not response.strip():
                raise ProviderError('required response empty; no retry', attempts=attempts, status='invalid_output')
            if validate is None:
                return response
            try:
                return validate(response)
            except (ValueError, TypeError, KeyError, RecursionError):
                raise ProviderError('required response violates its schema; no retry',
                                    attempts=attempts, status='invalid_output') from None
        except BaseException as error:
            if result is None:
                attempts = public_attempts(getattr(error, 'attempts', []))
            status = getattr(error, 'status', 'failed')
            raise
        finally:
            self.receipts.write(identity, system, user, response, status, attempts)
            self.calls.append({'label': label, 'model': client.model, 'logical_request_id': identity,
                               'status': status, 'attempts': attempts,
                               'provider_attempts': sum(a.get('provider_attempts', 0) for a in attempts),
                               'cost_usd': round(sum(a.get('cost_usd', 0) for a in attempts), 9),
                               'held_usd': round(sum(a.get('held_usd', 0) for a in attempts), 9)})

    def summary(self):
        return {**self.receipts.summary(), 'calls': self.calls}

    def close(self):
        self.receipts.close()


def ledger_snapshot(client):
    """The public manifest identifies the run without exposing its private path."""
    return {key: value for key, value in client.ledger.snapshot().items() if key != 'path'}
