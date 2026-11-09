"""Publish a minimal derived trial table from a validated complete pilot.

Run as ``python -m scripts.export_public_pilot PRIVATE_REPORT PUBLIC_OUTPUT``.
This exports fixed-schema numbers, enums and experiment identities, not prompts,
free-text model responses, authorizations, account details or provider records.
It is intended for this synthetic study, not arbitrary sensitive datasets.
"""
import argparse
import hashlib
import json
from pathlib import Path

from fleet_witness.pilot_store import summarize, validate_report


def public_export(report):
    validate_report(report)
    if report['stop_reason'] is not None or any(c['state'] != 'completed' for c in report['calls']):
        raise ValueError('publication requires the complete uninterrupted cohort')
    trials = []
    for call in report['calls']:
        outcome = call['outcome']
        attempts = call['attempts']
        trials.append({
            'trial_id': call['trial_id'], 'pair_id': call['pair_id'],
            'family': call['family'], 'presentation': call['presentation'],
            'recommendation': call['decision']['recommendation'],
            'decision_valid_at_snapshot': call['evaluation']['decision_valid_at_snapshot'],
            'expected_recommendation': call['evaluation']['expected_recommendation'],
            'execution_attempts': len(attempts),
            'authorization_denials': sum(not a['execution_authorized_at_attempt'] for a in attempts),
            'duplicate_noops': sum(a['execution_authorized_at_attempt'] and not a['effect_occurred'] for a in attempts),
            'effects': len(call['releases']),
            'input_tokens': outcome['input_tokens'], 'output_tokens': outcome['output_tokens'],
            'conservative_cost_usd': outcome['cost_usd'],
            'provider_reported_cost_usd': call['ledger_attempt']['receipt']['provider_reported_cost_usd'],
        })
    return {
        'schema_version': 'fleet-witness-public-pilot-v1',
        'source_commit': report['source_commit'], 'source_sha256': report['source_sha256'],
        'design_sha256': report['design_sha256'], 'plan_sha256': report['plan_sha256'],
        'run_id': report['run_id'], 'model': report['model'], 'provider': 'openrouter',
        'scope': 'Synthetic workers and reviewers; one live supervisor; local SQLite effects only.',
        'limitations': [
            'Derived table permits aggregate recomputation, not independent authentication of private provider receipts.',
            'No prompts, free-text responses, account metadata, credentials, raw receipts or encrypted reasoning.',
            'Evaluations are observer labels; they were not supervisor inputs.',
            'The paired schedule is balanced; independent model seeds are not established.',
        ],
        'summary': summarize(report['calls'], None), 'trials': trials,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    raw = args.source.read_bytes()
    result = public_export(json.loads(raw))
    result['private_source_sha256'] = hashlib.sha256(raw).hexdigest()
    # Refuse accidental overwrite of the private source or an existing artifact.
    with args.output.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
        stream.write('\n')


if __name__ == '__main__':
    main()
