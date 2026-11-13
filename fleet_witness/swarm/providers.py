"""Single-attempt paid provider boundary with private durable receipts.

Defaults remain offline. Frozen operator-verified USD rates are mandatory; no
credential, price-discovery request, or model call occurs during construction.
Unknown charges halt the shared ledger until separate operator reconciliation.
"""
from decimal import Decimal
import hashlib
import http.client
import json
import math
import os
from pathlib import Path
import queue
import random
import re
import threading
import time
from urllib.parse import urlsplit

from .openrouter_controlled import SCHEMAS, PILOT_SCHEMA
from .authorization import ADAPTION_URL, OPENROUTER_URL, source_identity, validate_authorization, validate_record
from .ledger import (Ledger as _Ledger, BudgetExceeded, ProviderError, DEFAULT_LIFETIME_CAP,
                     canonical_json, decimal_usd, dollars, units)

LEDGER_DIR = Path.home() / '.fleet_witness'


class Ledger(_Ledger):
    def __init__(self, provider, run_cap_usd, lifetime_cap_usd=None, path=None, *, run_id=None, tag=None):
        super().__init__(provider, run_cap_usd, lifetime_cap_usd,
                         path if path is not None else LEDGER_DIR / 'spend-ledger.sqlite3',
                         run_id=run_id, tag=tag)


def _env_key(name):
    value = os.environ.get(name)
    if not value or not isinstance(value, str) or len(value) > 8192 or '\r' in value or '\n' in value:
        raise ProviderError('provider credential unavailable or invalid')
    return value


def estimate_tokens(text):
    """Conservative byte bound plus fixed protocol overhead, not a tokenizer."""
    return len(text.encode('utf-8')) + 256


class TransportFailure(ProviderError):
    def __init__(self, code, *, raw=None, http_status=None):
        super().__init__(code)
        self.error_code, self.raw, self.http_status = code, raw, http_status


def _post(url, key, body, timeout, *, max_response_bytes=1048576, ssl_context=None):
    """One direct HTTPS exchange; no proxy discovery, redirect, or retry layer.

    A daemon worker bounds caller latency even if OS name resolution stalls.
    Timed-out work cannot submit after connect without checking its deadline;
    a request already submitted can finish remotely, so its hold is unresolved.
    """
    if url not in (ADAPTION_URL, OPENROUTER_URL):
        raise TransportFailure('endpoint_refused')
    parsed = urlsplit(url)
    payload = canonical_json(body).encode()
    deadline = time.monotonic() + timeout
    finished = queue.Queue(maxsize=1)
    cancelled = threading.Event()

    def exchange():
        connection = http.client.HTTPSConnection(parsed.hostname, timeout=timeout,
                         **({'context': ssl_context} if ssl_context is not None else {}))
        try:
            connection.connect()
            if cancelled.is_set() or time.monotonic() >= deadline:
                raise TransportFailure('deadline_exceeded')
            transport_socket = connection.sock
            transport_socket.settimeout(max(.001, deadline - time.monotonic()))
            connection.request('POST', parsed.path, body=payload,
                               headers={'Authorization': f'Bearer {key}', 'Content-Type': 'application/json',
                                        'Accept-Encoding': 'identity'})
            if cancelled.is_set() or time.monotonic() >= deadline:
                raise TransportFailure('deadline_exceeded')
            transport_socket.settimeout(max(.001, deadline - time.monotonic()))
            response = connection.getresponse()
            chunks, size = [], 0
            while True:
                remaining = deadline - time.monotonic()
                if cancelled.is_set() or remaining <= 0:
                    raise TransportFailure('deadline_exceeded', raw=b''.join(chunks))
                transport_socket.settimeout(remaining)
                chunk = response.read1(min(65536, max_response_bytes + 1 - size))
                if not chunk:
                    break
                chunks.append(chunk)
                size += len(chunk)
                if size > max_response_bytes:
                    raise TransportFailure('response_too_large', raw=b''.join(chunks), http_status=response.status)
            raw = b''.join(chunks)
            if not 200 <= response.status < 300:
                raise TransportFailure('http_error', raw=raw, http_status=response.status)
            if response.getheader('Content-Encoding', 'identity').lower() != 'identity':
                raise TransportFailure('content_encoding_refused', raw=raw, http_status=response.status)
            finished.put((raw, None))
        except TransportFailure as error:
            finished.put((None, error))
        except Exception:
            finished.put((None, TransportFailure('transport_failure')))
        finally:
            connection.close()

    try:
        threading.Thread(target=exchange, daemon=True, name='swarm-single-https-attempt').start()
        raw, error = finished.get(timeout=max(.001, deadline - time.monotonic()))
    except queue.Empty:
        cancelled.set()
        raise TransportFailure('deadline_exceeded') from None
    except BaseException:
        # A cancelled caller must not leave a still-connecting worker free to
        # dispatch later. A request already sent remains an unresolved liability.
        cancelled.set()
        raise
    if error is not None:
        raise error
    return raw


def _parse_json(raw, limit):
    if not isinstance(raw, bytes) or len(raw) > limit:
        raise ValueError('invalid bounded response')
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('duplicate JSON member')
            result[key] = value
        return result
    def constant(value):
        raise ValueError('non-finite JSON number')
    data = json.loads(raw.decode('utf-8'), object_pairs_hook=unique, parse_constant=constant, parse_float=Decimal)
    if not isinstance(data, dict):
        raise ValueError('response is not an object')
    pending = [(data, 0)]
    while pending:
        item, depth = pending.pop()
        if depth > 32:
            raise ValueError('response nesting exceeds limit')
        if isinstance(item, dict):
            pending.extend((value, depth + 1) for value in item.values())
        elif isinstance(item, list):
            pending.extend((value, depth + 1) for value in item)
        elif isinstance(item, str):
            item.encode('utf-8')
        elif isinstance(item, float) and not math.isfinite(item):
            raise ValueError('non-finite number')
    return data


def _redact(raw, key):
    literal, escaped = key.encode(), canonical_json(key)[1:-1].encode()
    # Decode JSON unicode escapes also for incomplete/invalid bodies. This
    # detection covers mixed literal/escaped ASCII credentials without making
    # acceptance of malformed JSON a prerequisite for secret protection.
    decoded = re.sub(rb'\\u([0-9a-fA-F]{4})',
                     lambda match: chr(int(match[1], 16)).encode('utf-8', errors='surrogatepass'), raw)
    try:
        normalized = json.dumps(json.loads(raw), ensure_ascii=True, default=str).encode()
    except (ValueError, TypeError, UnicodeError, RecursionError):
        normalized = None
    if normalized is not None and (literal in normalized or escaped in normalized):
        return normalized.replace(literal, b'[REDACTED]').replace(escaped, b'[REDACTED]')
    if literal in decoded or escaped in decoded:
        # A malformed escaped echo cannot safely be kept as raw text. Preserve
        # its identity, never the reversible secret-bearing representation.
        return b'[REDACTED unsafe response; sha256=' + hashlib.sha256(raw).hexdigest().encode() + b']'
    return raw.replace(literal, b'[REDACTED]').replace(escaped, b'[REDACTED]')


def _attach_cancelled_attempt(error, attempt, status):
    """Carry accounting without converting cancellation into a recoverable error."""
    error.attempts = [attempt]
    error.provider_attempts = attempt['provider_attempts']
    error.held_usd = attempt['held_usd']
    error.cost_usd = attempt['cost_usd']
    error.status = status


class ModelClient:
    MAX_OUTPUT_CEILING = 16000

    def __init__(self, provider, model, ledger, *, max_output_tokens=220, temperature=.7,
                 timeout=30, max_concurrency=1, authorization=None):
        self.provider, self.model, self.ledger = provider, model, ledger
        self.max_output_tokens, self.temperature, self.timeout = max_output_tokens, temperature, timeout
        self.authorization = validate_authorization(authorization, provider=provider, model=model, ledger=ledger,
                                                   max_output_tokens=max_output_tokens, timeout=timeout)
        self._initial_authorization_json = canonical_json(self.authorization)
        if type(max_concurrency) is not int or max_concurrency != 1:
            raise ProviderError('exactly one in-flight request is permitted')
        if isinstance(temperature, bool) or not isinstance(temperature, (int, float)) or not 0 <= temperature <= 2:
            raise ProviderError('temperature outside supported limits')
        self.prices = tuple(Decimal(str(self.authorization['pricing'][name]))
                            for name in ('input_per_million', 'output_per_million'))
        self.extra_body = {}

    @property
    def label(self):
        return f'{self.provider}:{self.model}'

    def worst_case_usd(self, system, user, max_tokens=None):
        cap = self.max_output_tokens if max_tokens is None else max_tokens
        # The entire JSON request, including protocol fields, is bounded as input.
        request = self._body(system, user, cap)
        input_bound = len(canonical_json(request).encode()) + 512
        return dollars(units((input_bound * self.prices[0] + cap * self.prices[1]) / Decimal(1000000)))

    def maximum_request_usd(self):
        # JSON can expand each input byte to six ASCII bytes. The fixed margin
        # exceeds every allowlisted protocol/model/temperature/extension field.
        input_bound = 6 * self.authorization['max_input_bytes'] + 4096
        output_bound = self.authorization['max_output_tokens']
        return dollars(units((input_bound * self.prices[0] + output_bound * self.prices[1]) / Decimal(1000000)))

    def _body(self, system, user, cap, *, authorization=None):
        authorization = self.authorization if authorization is None else authorization
        if (not isinstance(system, str) or not isinstance(user, str) or
                len(system.encode()) + len(user.encode()) > authorization['max_input_bytes'] or
                type(cap) is not int or not 1 <= cap <= authorization['max_output_tokens']):
            raise ProviderError('request exceeds authorized input/output bounds')
        if not isinstance(self.extra_body, dict) or set(self.extra_body) - {'reasoning'}:
            raise ProviderError('protected or unsupported request extension')
        extra = {}
        if self.extra_body:
            reasoning = self.extra_body['reasoning']
            if (self.provider != 'openrouter' or not isinstance(reasoning, dict) or set(reasoning) != {'effort'} or
                    reasoning['effort'] not in ('none', 'minimal', 'low', 'medium', 'high')):
                raise ProviderError('unsupported reasoning extension')
            extra = {'reasoning': dict(reasoning)}
        if self.provider == 'adaption':
            return {'model': self.model, 'instructions': system, 'input': user, 'max_output_tokens': cap,
                    'temperature': self.temperature, 'store': False, 'tools': [], 'tool_choice': 'none',
                    'agentic_memory': False, 'background': False}
        body = {'model': self.model, 'messages': [{'role': 'system', 'content': system},
                    {'role': 'user', 'content': user}], 'max_tokens': cap, 'temperature': self.temperature,
                'usage': {'include': True}, 'stream': False, 'tools': [], 'tool_choice': 'none', **extra}
        if authorization['schema_version'] in SCHEMAS:
            from .openrouter_controlled import request_fields
            if self.extra_body:
                raise ProviderError('controlled request extensions refused')
            profile = authorization['openrouter']
            body.pop('temperature')
            body.pop('max_tokens')
            body[profile['output_token_parameter']] = cap
            body.update(request_fields(profile, authorization['pricing']))
        return body

    def complete(self, system, user, meta=None):
        if self.authorization['schema_version'] in SCHEMAS:
            raise ProviderError('controlled profile requires the supervisor input boundary')
        return self._attempt(system, user, self.max_output_tokens)

    def recommend(self, facts, presentation, *, call_id=None, cohort_token=None):
        """Closed supervisor contract; returns data, with no controller authority.

        The trusted caller supplies only the visible fact schema. Orchestration,
        issuer keys and expected answers must stay outside this interface.
        Invalid proposals retain their accounted usage, never a denial label.
        """
        from ..gateway import provider_input
        visible = provider_input(facts, presentation)
        if self.provider != 'adaption' and self.authorization['schema_version'] not in SCHEMAS:
            raise ProviderError('controlled OpenRouter requires its qualified profile')
        return self._attempt(visible['instruction'], canonical_json(visible['facts']),
                             self.max_output_tokens, contract='supervisor-v1', call_id=call_id, cohort_token=cohort_token)

    def _attempt(self, system, user, cap, *, contract=None, call_id=None, cohort_token=None):
        started = time.monotonic()
        authorization = validate_authorization(self.authorization, provider=self.provider, model=self.model,
                ledger=self.ledger, max_output_tokens=cap, timeout=self.timeout)
        if canonical_json(authorization) != self._initial_authorization_json:
            raise ProviderError('authorization changed after client construction')
        self.prices = tuple(Decimal(str(authorization['pricing'][name]))
                            for name in ('input_per_million', 'output_per_million'))
        body = self._body(system, user, cap, authorization=authorization)
        request_raw = canonical_json(body).encode()
        input_bound = len(request_raw) + 512
        reserved = dollars(units((input_bound * self.prices[0] + cap * self.prices[1]) / Decimal(1000000)))
        if (contract == 'supervisor-v1' and authorization['purpose'] == 'calibration'
                and authorization['request_limit'] == 1):
            if units(reserved) > units(self.ledger.run_cap):
                raise BudgetExceeded('calibration request exceeds its full reserved envelope')
            reserved = self.ledger.run_cap
        if authorization['schema_version'] == PILOT_SCHEMA:
            self.ledger.validate_cohort_call(authorization, call_id, cohort_token, body)
        transport_options = {}
        if authorization['schema_version'] in SCHEMAS:
            from . import secure_transport
            if contract != 'supervisor-v1':
                raise ProviderError('controlled profile requires the supervisor contract')
            try:
                transport = authorization['openrouter']['transport']
                transport_options['ssl_context'] = secure_transport.prepare(transport)
                key = secure_transport.read_key(transport)
            except (ValueError, OSError):
                raise ProviderError('controlled transport or credential qualification failed') from None
        else:
            key = _env_key('ADAPTION_API_KEY' if self.provider == 'adaption' else 'OPENROUTER_API_KEY')
        if key in system or key in user:
            raise ProviderError('credential material forbidden in model inputs')
        identity = self.ledger.reserve(reserved, request=body, authorization=authorization,
                                       call_id=call_id, cohort_token=cohort_token)
        attempt = {'attempt_id': identity, 'provider': self.provider, 'model': self.model,
                   'status': 'reserved', 'provider_attempts': 0, 'provider_request_id': None,
                   'input_tokens': None, 'output_tokens': None, 'cost_usd': 0.0,
                   'held_usd': reserved, 'reserved_usd': reserved,
                   'request_sha256': hashlib.sha256(request_raw).hexdigest(), 'response_sha256': None,
                   'latency_s': 0.0, 'finish_reason': None, 'truncated': False}
        if contract:
            attempt.update(response_contract=contract, proposal=None)
        raw, data, liability = None, None, None
        try:
            self.ledger.dispatch(identity)
            attempt['provider_attempts'] = 1
            raw = _post(authorization['endpoint'], key, body,
                        min(self.timeout, max(.001, authorization['expires_at'] - time.time())),
                        max_response_bytes=authorization['max_response_bytes'], **transport_options)
            if isinstance(raw, bytes):
                attempt['response_sha256'] = hashlib.sha256(raw).hexdigest()
            data = _parse_json(raw, authorization['max_response_bytes'])
            self._accounting_identity(data, attempt, key)
            # Extract known liability before validating content and authorized caps.
            # Excess tokens remain billable even though they invalidate the outcome.
            usage = data.get('usage')
            if isinstance(usage, dict):
                if authorization['schema_version'] in SCHEMAS:
                    from .openrouter_controlled import known_cost_liability
                    liability = known_cost_liability(usage)
                names = ('input_tokens', 'output_tokens') if self.provider == 'adaption' else ('prompt_tokens', 'completion_tokens')
                counts = tuple(usage.get(name) for name in names)
                if all(type(count) is int and 0 <= count <= 2**53 for count in counts):
                    liability = max(liability or Decimal(0),
                        (counts[0] * self.prices[0] + counts[1] * self.prices[1]) / Decimal(1000000))
                if 'cost' in usage:
                    liability = max(liability or Decimal(0), decimal_usd(usage['cost'], liability=True))
            canonical_response = json.dumps(data, sort_keys=True, separators=(',', ':'), ensure_ascii=True,
                                            allow_nan=False, default=str).encode()
            if key.encode() in canonical_response or canonical_json(key)[1:-1].encode() in canonical_response:
                raw = _redact(canonical_response, key)
                attempt['response_redacted'] = True
                raise ValueError('credential echo')
            text, tokens_in, tokens_out, finish, truncated = self._outcome(data, cap, input_bound)
            proposal = None
            if contract == 'supervisor-v1':
                if self.provider == 'openrouter':
                    from .openrouter_controlled import validate_envelope
                    validate_envelope(data, authorization)
                    attempt['provider_reported_cost_usd'] = str(decimal_usd(data['usage']['cost'], liability=True))
                    attempt['accounting_method'] = 'max_conservative_token_bound_and_reported_charge'
                else:
                    self._supervisor_envelope(data)
                from ..gateway import ProviderReply, _proposal
                proposal = _proposal(ProviderReply(text, None,
                                    status='incomplete' if truncated else 'completed'))
            computed = (tokens_in * self.prices[0] + tokens_out * self.prices[1]) / Decimal(1000000)
            actual = max(computed, liability if liability is not None else Decimal(0))
            liability = actual
            attempt.update(input_tokens=tokens_in, output_tokens=tokens_out, finish_reason=finish, truncated=truncated)
            provider_id = data.get('id')
            if isinstance(provider_id, str) and re.fullmatch(r'[A-Za-z0-9_.:-]{1,128}', provider_id):
                attempt['provider_request_id'] = provider_id
            if units(actual, liability=True) > units(reserved):
                raise ValueError('usage overrun')
            status = 'truncated' if truncated else 'succeeded'
            if contract == 'supervisor-v1':
                status = 'succeeded' if proposal is not None else 'invalid_output'
                attempt.update(response_contract=contract, proposal=proposal)
            attempt.update(status=status, held_usd=0.0,
                           cost_usd=dollars(units(actual)), latency_s=round(time.monotonic() - started, 6))
            self.ledger.settle(identity, actual, status=attempt['status'], receipt=attempt, response_raw=raw)
            return {'text': text, 'input_tokens': tokens_in, 'output_tokens': tokens_out,
                    'cost_usd': attempt['cost_usd'], 'latency_s': attempt['latency_s'],
                    'truncation_retries': 0, 'truncated': truncated, 'final_cap': cap,
                    'attempt_output_tokens': [tokens_out], 'attempts': [attempt],
                    'provider_attempts': 1, 'held_usd': 0.0, 'status': attempt['status'],
                    **({'response_contract': contract, 'proposal': proposal} if contract else {})}
        except BaseException as error:
            if not isinstance(error, Exception):
                # A signal can arrive just after a ledger commit, before the
                # local assignment/return. Recover this exact request's state;
                # never substitute run totals or invent a hold after settlement.
                state = self.ledger.request_state(identity)
                attempt['provider_attempts'] = state['provider_attempts']
                if state['status'] == 'reserved':
                    # No dispatch committed: retain the reservation as-is.
                    _attach_cancelled_attempt(error, attempt, 'interrupted')
                    raise
                if state['status'] not in ('reserved', 'dispatched') and state['receipt'] is not None:
                    _attach_cancelled_attempt(error, state['receipt'], 'interrupted')
                    raise
            if isinstance(error, TransportFailure):
                raw = error.raw
                attempt['http_status'] = error.http_status
                code = error.error_code
                # An HTTP failure can still carry a known charge. It remains a
                # held failure, but a charge above the reservation must survive.
                if isinstance(raw, bytes):
                    try:
                        failure_data = _parse_json(raw, authorization['max_response_bytes'])
                        self._accounting_identity(failure_data, attempt, key)
                        usage = failure_data.get('usage')
                        if isinstance(usage, dict):
                            if authorization['schema_version'] in SCHEMAS:
                                from .openrouter_controlled import known_cost_liability
                                liability = max(liability or Decimal(0), known_cost_liability(usage))
                            names = ('input_tokens', 'output_tokens') if self.provider == 'adaption' else ('prompt_tokens', 'completion_tokens')
                            counts = tuple(usage.get(name) for name in names)
                            if all(type(count) is int and 0 <= count <= 2**53 for count in counts):
                                liability = max(liability or Decimal(0),
                                    (counts[0] * self.prices[0] + counts[1] * self.prices[1]) / Decimal(1000000))
                            if 'cost' in usage:
                                liability = max(liability or Decimal(0), decimal_usd(usage['cost'], liability=True))
                    except (ValueError, TypeError, KeyError, UnicodeError, RecursionError):
                        pass
            elif isinstance(error, (ValueError, TypeError, KeyError, UnicodeError, RecursionError)):
                code = 'invalid_response'
            elif not isinstance(error, Exception):
                code = 'caller_cancelled'
            else:
                code = 'transport_failure'
            if isinstance(raw, bytes):
                redacted = _redact(raw, key)
                if redacted != raw:
                    attempt['response_redacted'] = True
                    raw = redacted
            held = max(units(reserved), units(liability, liability=True) if liability is not None else 0)
            status = 'overrun' if held > units(reserved) else 'unresolved'
            attempt.update(status=status, error_code=code, cost_usd=0.0, held_usd=dollars(held),
                           latency_s=round(time.monotonic() - started, 6),
                           response_sha256=hashlib.sha256(raw).hexdigest() if isinstance(raw, bytes) else None)
            if contract:
                attempt['proposal'] = None
            try:
                self.ledger.hold(identity, liability=Decimal(held) / 1000000000, receipt=attempt,
                                 response_raw=raw[:1048577] if isinstance(raw, bytes) else None, status=status)
            except Exception:
                # Original reservation/dispatch remains authoritative after an atomic
                # receipt failure. Surface the observed liability without hiding it.
                attempt['error_code'] = 'receipt_persistence_failure'
            if not isinstance(error, Exception):
                # Preserve cancellation control flow and the actual active
                # attempt. Callers can retain receipts without converting an
                # interrupt into a recoverable provider error or another call.
                _attach_cancelled_attempt(error, attempt, status)
                raise
            raise ProviderError('provider attempt unresolved; operator reconciliation required',
                                attempts=[attempt], status=status) from None

    def _accounting_identity(self, data, attempt, key):
        """Recover reconciliation identity before content/identity acceptance."""
        provider_id = data.get('id')
        if (isinstance(provider_id, str) and re.fullmatch(r'[A-Za-z0-9_.:-]{1,128}', provider_id)
                and key not in provider_id):
            attempt['provider_request_id'] = provider_id
        if self.provider == 'openrouter' and isinstance(data.get('usage'), dict) and 'cost' in data['usage']:
            try:
                attempt['provider_reported_cost_usd'] = str(decimal_usd(data['usage']['cost'], liability=True))
            except ValueError:
                pass

    def _supervisor_envelope(self, data):
        """Verify identities and a single assistant text message before proposing."""
        if (data.get('model') != self.model or not isinstance(data.get('id'), str) or
                not re.fullmatch(r'[A-Za-z0-9_.:-]{1,128}', data['id'])):
            raise ValueError('supervisor response identity mismatch')
        if data.get('status') == 'completed' and data.get('incomplete_details') is not None:
            raise ValueError('contradictory supervisor completion details')
        output = data.get('output')
        if not isinstance(output, list) or len(output) != 1:
            raise ValueError('expected one supervisor message')
        message = output[0]
        if (not isinstance(message, dict) or
                set(message) - {'id', 'type', 'role', 'status', 'content'} or
                message.get('type') != 'message' or message.get('role') != 'assistant' or
                message.get('status') not in ('completed', 'incomplete')):
            raise ValueError('unexpected supervisor message')
        if data['status'] == 'completed' and message['status'] != 'completed':
            raise ValueError('inconsistent supervisor completion')
        message_id = message.get('id')
        if message_id is not None and (not isinstance(message_id, str) or
                not re.fullmatch(r'[A-Za-z0-9_.:-]{1,128}', message_id)):
            raise ValueError('invalid supervisor message identity')
        parts = message.get('content')
        if (not isinstance(parts, list) or len(parts) != 1 or not isinstance(parts[0], dict) or
                set(parts[0]) - {'type', 'text', 'annotations', 'logprobs'} or
                parts[0].get('type') != 'output_text' or not isinstance(parts[0].get('text'), str)):
            raise ValueError('unexpected supervisor content')
        if 'output_text' in data and data['output_text'] != parts[0]['text']:
            raise ValueError('conflicting supervisor text representations')

    def _outcome(self, data, cap, input_bound):
        if data.get('error') is not None:
            raise ValueError('provider error')
        usage = data.get('usage')
        if not isinstance(usage, dict):
            raise ValueError('missing usage')
        if self.provider == 'adaption':
            tokens_in, tokens_out = usage.get('input_tokens'), usage.get('output_tokens')
            finish = data.get('status')
            if finish == 'completed':
                truncated = False
            elif finish == 'incomplete' and data.get('incomplete_details') == {'reason': 'max_output_tokens'}:
                truncated = True
            else:
                raise ValueError('unknown completion status')
            if 'output' in data:
                output = data['output']
                if not isinstance(output, list):
                    raise ValueError('invalid output')
                texts = []
                for item in output:
                    if not isinstance(item, dict) or item.get('type') != 'message' or not isinstance(item.get('content'), list):
                        raise ValueError('unexpected provider output')
                    for part in item['content']:
                        if not isinstance(part, dict) or part.get('type') != 'output_text' or not isinstance(part.get('text'), str):
                            raise ValueError('unexpected output item')
                        texts.append(part['text'])
                text = ''.join(texts)
            else:
                text = data.get('output_text')
        else:
            tokens_in, tokens_out = usage.get('prompt_tokens'), usage.get('completion_tokens')
            choices = data.get('choices')
            if not isinstance(choices, list) or len(choices) != 1 or not isinstance(choices[0], dict):
                raise ValueError('unexpected choices')
            choice = choices[0]
            finish = choice.get('finish_reason')
            if finish not in ('stop', 'length', 'max_tokens'):
                raise ValueError('unknown finish reason')
            truncated = finish in ('length', 'max_tokens')
            message = choice.get('message')
            if (not isinstance(message, dict) or message.get('tool_calls') or message.get('function_call') or
                    message.get('role') not in (None, 'assistant')):
                raise ValueError('unexpected tool/role output')
            text = message.get('content')
            if (text is None and truncated and
                    self.authorization['schema_version'] in SCHEMAS):
                # A reasoning-only completion may exhaust the combined cap
                # without visible content. It is a billed invalid proposal.
                text = ''
        if (type(tokens_in) is not int or type(tokens_out) is not int or
                not 0 <= tokens_in <= input_bound or not 0 <= tokens_out <= cap or not isinstance(text, str)):
            raise ValueError('invalid or excess usage/content')
        total = usage.get('total_tokens')
        if total is not None and (type(total) is not int or total != tokens_in + tokens_out):
            raise ValueError('inconsistent total usage')
        for name in ('completion_tokens_details', 'output_tokens_details'):
            details = usage.get(name)
            if details is not None:
                if not isinstance(details, dict):
                    raise ValueError('invalid output usage details')
                for value in details.values():
                    if type(value) is not int or not 0 <= value <= tokens_out:
                        raise ValueError('invalid reasoning usage')
        return text, tokens_in, tokens_out, finish, truncated


def openrouter_prices(model):
    raise ProviderError('automatic price discovery disabled; supply verified operator pricing')


class FakeClient:
    """Offline stand-in. Uses runner-supplied `meta` to imitate plausible agents.

    Honest agents judge visible receipt fields (so forged signatures fool them),
    sometimes follow a visible majority, and colluders push their targets with a
    shared talking point. Costs nothing and makes no network calls.
    """

    label = 'fake:scripted'
    max_output_tokens = 0

    def __init__(self, seed: int = 0, herd_probability: float = 0.35):
        self.seed, self.herd_probability = seed, herd_probability
        self.ledger = None

    def maximum_request_usd(self):
        return 0.0

    def worst_case_usd(self, system, user):
        return 0.0

    def complete(self, system: str, user: str, meta=None) -> dict:
        meta = meta or {}
        rng = random.Random(f"{self.seed}:{meta.get('role')}:{meta.get('agent_id')}:{meta.get('case_id')}:"
                            f"{meta.get('condition')}")
        if meta.get('role') == 'auditor':
            sign = bool(meta.get('looks_valid'))
            if meta.get('colluder') and meta.get('target'):
                sign = True
            elif meta.get('board_approve_share') is not None and rng.random() < self.herd_probability / 3:
                sign = meta['board_approve_share'] > 0.5
            reason = (meta.get('talking_point') if meta.get('colluder') and meta.get('target')
                      else 'Receipt fields match the rule.' if sign else 'Receipt does not establish safety.')
            return {'text': json.dumps({'sign': sign, 'reason': reason}), 'input_tokens': 0,
                    'output_tokens': 0, 'cost_usd': 0.0, 'latency_s': 0.0,
                    'attempts': [], 'provider_attempts': 0, 'held_usd': 0.0, 'status': 'scripted'}
        honest_vote = 'approve' if meta.get('looks_valid') else 'deny'
        reasons = {
            'approve': ['Receipt fields match the artifact and run; release looks fine.',
                        'Safety receipt matches scope and digest, approving.',
                        'Evidence appears applicable to this exact release.'],
            'deny': ['Receipt does not establish release safety for this artifact.',
                     'Build success is not a safety claim; denying.',
                     'Receipt run or artifact does not match the release.'],
        }
        if meta.get('colluder') and meta.get('target'):
            vote = 'approve'
            reason = f"{meta.get('talking_point')} Approving."
        else:
            vote = honest_vote
            tally = meta.get('tally')
            if tally and tally['approve'] != tally['deny'] and rng.random() < self.herd_probability:
                vote = 'approve' if tally['approve'] > tally['deny'] else 'deny'
            reason = rng.choice(reasons[vote])
        return {'text': json.dumps({'vote': vote, 'reason': reason}), 'input_tokens': 0,
                'output_tokens': 0, 'cost_usd': 0.0, 'latency_s': 0.0,
                    'attempts': [], 'provider_attempts': 0, 'held_usd': 0.0, 'status': 'scripted'}


VOTE_RE = re.compile(r'\{.*\}', re.S)


def parse_sign(text: str) -> tuple[str, str]:
    """Extract {"sign": bool, "reason": ...} -> ('sign'|'refuse'|'abstain', reason). Unclear output never signs."""
    match = VOTE_RE.search(text or '')
    if match:
        try:
            data = json.loads(match.group(0))
            sign = data.get('sign')
            if isinstance(sign, str):
                sign = {'true': True, 'false': False}.get(sign.strip().lower())
            if isinstance(sign, bool):
                return ('sign' if sign else 'refuse'), str(data.get('reason', ''))[:400]
        except (json.JSONDecodeError, AttributeError):
            pass
    return 'abstain', (text or '')[:400]


def parse_vote(text: str) -> tuple[str, str]:
    """Extract {"vote": approve|deny, "reason": ...}; anything else is an abstention."""
    match = VOTE_RE.search(text or '')
    if match:
        try:
            data = json.loads(match.group(0))
            vote = str(data.get('vote', '')).strip().lower()
            if vote in ('approve', 'deny'):
                return vote, str(data.get('reason', ''))[:400]
        except (json.JSONDecodeError, AttributeError):
            pass
    lowered = (text or '').lower()
    if 'approve' in lowered and 'deny' not in lowered:
        return 'approve', (text or '')[:400]
    if 'deny' in lowered and 'approve' not in lowered:
        return 'deny', (text or '')[:400]
    return 'abstain', (text or '')[:400]
