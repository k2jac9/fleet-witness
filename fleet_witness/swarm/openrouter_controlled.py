"""Closed OpenRouter supervisor profile; provider assertions are not execution authority."""
import re
from decimal import Decimal

from . import secure_transport
from .ledger import decimal_usd, units


SCHEMA = 'controlled-openrouter-v1'
PILOT_SCHEMA = 'controlled-openrouter-pilot-v1'
SCHEMAS = (SCHEMA, PILOT_SCHEMA)


def validate_profile(record):
    profile = record.get('openrouter')
    pilot = record.get('schema_version') == PILOT_SCHEMA
    if (record.get('provider') != 'openrouter' or record.get('purpose') != ('exploratory' if pilot else 'calibration') or
            record.get('request_limit') != (160 if pilot else 1) or not 0 < units(record['run_cap_usd'], exact=True) <= units(15) or
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
    if pilot:
        from ..pilot_design import design_sha256, MODEL
        study = record.get('study')
        if (not isinstance(study, dict) or set(study) != {'design_sha256', 'calibration_evidence_sha256'} or
                study['design_sha256'] != design_sha256() or
                not isinstance(study['calibration_evidence_sha256'], str) or
                not re.fullmatch(r'[0-9a-f]{64}', study['calibration_evidence_sha256']) or
                record['model'] != MODEL or profile['response_model'] != MODEL or
                profile['provider_slug'] != 'azure/us' or profile['provider_name'] != 'Azure' or
                profile['reasoning_effort'] != 'low' or profile['output_token_parameter'] != 'max_completion_tokens' or
                record['max_input_bytes'] != 4096 or record['max_output_tokens'] != 256 or
                record['timeout_s'] != 30 or record['expires_at'] - record['issued_at'] > 7200):
            raise ValueError('frozen pilot profile mismatch')
        pricing = record['pricing']
        bound = ((6 * 4096 + 4096) * decimal_usd(pricing['input_per_million']) +
                 256 * decimal_usd(pricing['output_per_million'])) / Decimal(1000000)
        if units(bound) * 160 > units(record['run_cap_usd'], exact=True):
            raise ValueError('complete pilot schedule exceeds authorized cap')


def request_fields(profile, pricing):
    return {'provider': {'only': [profile['provider_slug']], 'order': [profile['provider_slug']], 'allow_fallbacks': False,
                         'require_parameters': True, 'data_collection': 'deny', 'zdr': True,
                         'max_price': {'prompt': float(pricing['input_per_million']),
                                       'completion': float(pricing['output_per_million']), 'request': 0}},
            'service_tier': 'default', 'store': False,
            'reasoning': {'effort': profile['reasoning_effort'], 'exclude': True},
            'response_format': {'type': 'json_schema', 'json_schema': {
                'name': 'supervisor_recommendation', 'strict': True,
                'schema': {'type': 'object', 'properties': {
                    'recommendation': {'type': 'string', 'enum': ['approve', 'deny']},
                    'reason': {'type': 'string', 'minLength': 1, 'maxLength': 2048}},
                    'required': ['recommendation', 'reason'], 'additionalProperties': False}}}}


COST_FIELDS = {'upstream_inference_cost', 'upstream_inference_prompt_cost',
               'upstream_inference_completions_cost'}


def known_cost_liability(usage):
    """Preserve known monetary amounts even when other usage fields are invalid."""
    amounts = []
    def amount(value):
        try:
            return decimal_usd(value, liability=True)
        except (ValueError, TypeError):
            return Decimal(0)
    amounts.append(amount(usage.get('cost')))
    details = usage.get('cost_details')
    if isinstance(details, dict):
        amounts.append(amount(details.get('upstream_inference_cost')))
        amounts.append(amount(details.get('upstream_inference_prompt_cost')) +
                       amount(details.get('upstream_inference_completions_cost')))
    return max(amounts)


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
    # OpenRouter normalizes finish_reason; Azure may retain its native
    # Responses status "completed" alongside normalized "stop".
    accepted_native = {'stop': {'stop', 'completed'}, 'length': {'length'}}
    if native is not None and native not in accepted_native[choice['finish_reason']]:
        raise ValueError('contradictory native completion status')
    message = choice.get('message')
    if (not isinstance(message, dict) or set(message) - {'role', 'content', 'refusal', 'reasoning',
            'reasoning_details', 'tool_calls', 'function_call', 'annotations'} or
            message.get('role') != 'assistant' or
            not (isinstance(message.get('content'), str) or
                 (choice['finish_reason'] == 'length' and message.get('content') is None)) or
            message.get('refusal') is not None or message.get('reasoning') not in (None, '') or
            message.get('tool_calls') not in (None, []) or
            message.get('function_call') is not None or message.get('annotations') not in (None, [])):
        raise ValueError('unexpected controlled message content')
    _opaque_reasoning(message.get('reasoning_details'), record)
    usage = data.get('usage')
    if (not isinstance(usage, dict) or not {'cost', 'prompt_tokens', 'completion_tokens', 'total_tokens'} <= set(usage) or
            set(usage) - {'cost', 'prompt_tokens', 'completion_tokens', 'total_tokens', 'is_byok',
                         'prompt_tokens_details', 'completion_tokens_details', 'cost_details'}):
        raise ValueError('controlled response requires reported total cost')
    cost = decimal_usd(usage['cost'], liability=True)
    for name in ('prompt_tokens', 'completion_tokens', 'total_tokens'):
        if type(usage[name]) is not int or not 0 <= usage[name] <= 2**53:
            raise ValueError('invalid controlled token total')
    if usage['total_tokens'] != usage['prompt_tokens'] + usage['completion_tokens']:
        raise ValueError('inconsistent controlled token totals')
    if 'is_byok' in usage and usage['is_byok'] is not False:
        raise ValueError('unqualified BYOK cost source')
    details = usage.get('cost_details')
    if details is not None:
        if not isinstance(details, dict) or set(details) - COST_FIELDS:
            raise ValueError('unqualified cost detail')
        amounts = {name: decimal_usd(value, liability=True) for name, value in details.items() if value is not None}
        parts = ('upstream_inference_prompt_cost', 'upstream_inference_completions_cost')
        if all(name in amounts for name in parts) and 'upstream_inference_cost' in amounts:
            if amounts[parts[0]] + amounts[parts[1]] != amounts['upstream_inference_cost']:
                raise ValueError('inconsistent upstream cost breakdown')
        # Discounts/BYOK may explain differences, but this profile has not
        # qualified a larger upstream liability than the reported total charge.
        if known_cost_liability(usage) > cost:
            raise ValueError('upstream liability exceeds reported charge')
    for field, total_field, billable, zero_only in (
            ('prompt_tokens_details', 'prompt_tokens', {'cached_tokens', 'cache_write_tokens'}, {'audio_tokens', 'video_tokens'}),
            ('completion_tokens_details', 'completion_tokens', {'reasoning_tokens'},
             {'audio_tokens', 'image_tokens', 'accepted_prediction_tokens', 'rejected_prediction_tokens'})):
        details = usage.get(field)
        if details is None:
            continue
        if not isinstance(details, dict) or set(details) - billable - zero_only:
            raise ValueError('invalid controlled usage details')
        for name, count in details.items():
            if type(count) is not int or not 0 <= count <= usage[total_field]:
                raise ValueError('invalid controlled token count')
            if name in zero_only and count != 0:
                raise ValueError('unqualified nontext usage')


def _opaque_reasoning(details, record):
    """Accept a reviewed inert wrapper, not a claim that its bytes are authentic.

    Never decode or replay this payload. The caller uses only assistant content;
    bounded raw response evidence is retained privately for reconciliation.
    """
    if details is None or details == []:
        return
    profile = record['openrouter']
    if (record['model'] != 'openai/gpt-6.1-sol' or profile['provider_slug'] != 'azure/us' or
            profile['provider_name'] != 'Azure' or not isinstance(details, list) or len(details) != 1):
        raise ValueError('unqualified reasoning metadata')
    item = details[0]
    if (not isinstance(item, dict) or set(item) != {'type', 'format', 'id', 'index', 'data'} or
            item['type'] != 'reasoning.encrypted' or item['format'] != 'azure-openai-responses-v1' or
            type(item['index']) is not int or item['index'] != 0 or
            not isinstance(item['id'], str) or not re.fullmatch(r'rs_[A-Za-z0-9_-]{1,125}', item['id']) or
            not isinstance(item['data'], str) or not re.fullmatch(r'[A-Za-z0-9_.=\-]{1,32768}', item['data'])):
        raise ValueError('invalid opaque reasoning metadata')
