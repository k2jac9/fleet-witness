"""Closed OpenRouter supervisor profile; provider assertions are not execution authority."""
import re

from . import secure_transport
from .ledger import decimal_usd, units


SCHEMA = 'controlled-openrouter-v1'


def validate_profile(record):
    profile = record.get('openrouter')
    if (record.get('provider') != 'openrouter' or record.get('purpose') != 'calibration' or
            record.get('request_limit') != 1 or not 0 < units(record['run_cap_usd'], exact=True) <= units(15) or
            not 0 < units(record['provider_cap_usd'], exact=True) <= units(50) or
            not 1 <= record['max_output_tokens'] <= 256):
        raise ValueError('controlled OpenRouter envelope refused')
    if not isinstance(profile, dict) or set(profile) != {
            'provider_slug', 'provider_name', 'response_model', 'reasoning_effort',
            'output_token_parameter', 'transport'}:
        raise ValueError('controlled OpenRouter profile missing')
    for field, pattern in (('provider_slug', r'[a-z0-9][a-z0-9._/-]{0,127}'),
                           ('provider_name', r'[A-Za-z0-9][A-Za-z0-9 ._-]{0,127}'),
                           ('response_model', r'[A-Za-z0-9][A-Za-z0-9._/-]{0,127}')):
        if not isinstance(profile[field], str) or not re.fullmatch(pattern, profile[field]):
            raise ValueError('invalid controlled provider identity')
    if not isinstance(record.get('model'), str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._/-]{0,127}', record['model']):
        raise ValueError('controlled model must be a direct reviewed identifier')
    if profile['reasoning_effort'] not in ('none', 'low'):
        raise ValueError('unsupported controlled reasoning effort')
    if profile['output_token_parameter'] not in ('max_tokens', 'max_completion_tokens'):
        raise ValueError('unsupported controlled token parameter')
    secure_transport.validate_profile(profile['transport'])


def request_fields(profile):
    return {'provider': {'only': [profile['provider_slug']], 'order': [profile['provider_slug']], 'allow_fallbacks': False,
                         'require_parameters': True, 'data_collection': 'deny', 'zdr': True},
            'service_tier': 'default', 'store': False,
            'reasoning': {'effort': profile['reasoning_effort'], 'exclude': True},
            'response_format': {'type': 'json_schema', 'json_schema': {
                'name': 'supervisor_recommendation', 'strict': True,
                'schema': {'type': 'object', 'properties': {
                    'recommendation': {'type': 'string', 'enum': ['approve', 'deny']},
                    'reason': {'type': 'string', 'minLength': 1, 'maxLength': 2048}},
                    'required': ['recommendation', 'reason'], 'additionalProperties': False}}}}


def validate_envelope(data, record):
    profile = record['openrouter']
    if (set(data) - {'id', 'model', 'provider', 'object', 'created', 'service_tier', 'choices',
                    'usage', 'system_fingerprint'} or
            data.get('model') != profile['response_model'] or data.get('provider') != profile['provider_name'] or
            data.get('object') != 'chat.completion' or not isinstance(data.get('id'), str) or
            not re.fullmatch(r'[A-Za-z0-9_.:-]{1,128}', data['id']) or
            type(data.get('created')) is not int or not 0 <= data['created'] <= 2**53 or
            data.get('service_tier') not in (None, 'default')):
        raise ValueError('controlled OpenRouter response identity mismatch')
    choices = data.get('choices')
    if not isinstance(choices, list) or len(choices) != 1 or not isinstance(choices[0], dict):
        raise ValueError('expected one controlled assistant choice')
    choice = choices[0]
    if (set(choice) - {'index', 'finish_reason', 'native_finish_reason', 'message', 'logprobs'} or
            type(choice.get('index')) is not int or choice['index'] != 0 or
            choice.get('finish_reason') not in ('stop', 'length') or choice.get('logprobs') is not None):
        raise ValueError('invalid controlled choice envelope')
    native = choice.get('native_finish_reason')
    if native is not None and native != choice['finish_reason']:
        raise ValueError('contradictory native completion status')
    message = choice.get('message')
    if (not isinstance(message, dict) or set(message) - {'role', 'content', 'refusal', 'reasoning',
            'reasoning_details', 'tool_calls', 'function_call', 'annotations'} or
            message.get('role') != 'assistant' or
            not (isinstance(message.get('content'), str) or
                 (choice['finish_reason'] == 'length' and message.get('content') is None)) or
            message.get('refusal') is not None or message.get('reasoning') not in (None, '') or
            message.get('reasoning_details') not in (None, []) or message.get('tool_calls') not in (None, []) or
            message.get('function_call') is not None or message.get('annotations') not in (None, [])):
        raise ValueError('unexpected controlled message content')
    usage = data.get('usage')
    if not isinstance(usage, dict) or 'cost' not in usage:
        raise ValueError('controlled response requires reported total cost')
    decimal_usd(usage['cost'], liability=True)
    if 'is_byok' in usage and usage['is_byok'] is not False:
        raise ValueError('unqualified BYOK cost source')
    for field, total_field in (('prompt_tokens_details', 'prompt_tokens'),
                               ('completion_tokens_details', 'completion_tokens')):
        details = usage.get(field)
        if details is None:
            continue
        if not isinstance(details, dict):
            raise ValueError('invalid controlled usage details')
        for name, count in details.items():
            if type(count) is not int or not 0 <= count <= usage[total_field]:
                raise ValueError('invalid controlled token count')
            if name not in ('reasoning_tokens', 'cached_tokens', 'cache_write_tokens') and count != 0:
                raise ValueError('unqualified nontext usage')
