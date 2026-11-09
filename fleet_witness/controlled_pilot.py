"""Explicit trusted-host pilot entrypoint. Default/import behavior performs no I/O."""
import argparse
import hashlib
import json
from pathlib import Path
import secrets
import uuid

from .controller import Controller
from .gateway import provider_input
from .pilot_design import make_plan, digest, MODEL, validate_plan
from .pilot_store import Store, private_path, export_report, save_report
from .swarm import operator
from .swarm.authorization import validate_record
from .swarm.ledger import ProviderError, canonical_json


def validate_calibration(packet, record):
    """Check retained evidence and operator applicability; not a signature system."""
    try:
        if (packet['schema_version'] != 'calibration-acceptance-v1' or
                packet['applies_to_source_sha256'] != record['source_sha256'] or
                not isinstance(packet['applicability'], str) or not 20 <= len(packet['applicability']) <= 4096 or
                not isinstance(packet['reviewed_by'], str) or not packet['reviewed_by'] or
                digest(packet) != record['study']['calibration_evidence_sha256']):
            raise ValueError('calibration acceptance not bound to runner')
        auth, result_raw, reconciliation = packet['calibration_authorization'], packet['result_raw'], packet['reconciliation']
        result = json.loads(result_raw)
        if (hashlib.sha256(result_raw.encode()).hexdigest() != reconciliation['result_sha256'] or
                auth['schema_version'] != 'controlled-openrouter-v1' or auth['purpose'] != 'calibration' or auth['request_limit'] != 1 or
                auth['provider'] != record['provider'] or auth['model'] != record['model'] or
                auth['openrouter'] != record['openrouter'] or auth['pricing'] != record['pricing'] or
                result['run_id'] != auth['run_id'] or result['outcome']['status'] != 'succeeded' or
                result['outcome']['provider_attempts'] != 1 or len(result['outcome']['attempts']) != 1 or
                result['outcome']['response_contract'] != 'supervisor-v1' or
                reconciliation['accepted'] is not True or reconciliation['read_only'] is not True or
                not reconciliation['checks'] or any(v is not True for v in reconciliation['checks'].values())):
            raise ValueError('calibration identity/schema/reconciliation incomplete')
        from decimal import Decimal
        attempt = result['outcome']['attempts'][0]; generation = reconciliation['generation']
        if (generation['id'] != attempt['provider_request_id'] or generation['model'] != MODEL + '-20260929' or
                generation['provider_name'] != record['openrouter']['provider_name'] or
                Decimal(str(generation['total_cost'])) != Decimal(attempt['provider_reported_cost_usd']) or
                Decimal(str(reconciliation['usage_delta'])) != Decimal(attempt['provider_reported_cost_usd']) or
                generation['native_tokens_prompt'] != attempt['input_tokens'] or
                generation['native_tokens_completion'] != attempt['output_tokens']):
            raise ValueError('calibration account charge or generation mismatch')
        return True
    except (KeyError, TypeError, ValueError):
        raise ValueError('complete source-applicable calibration acceptance packet required') from None


def collect(client, output):
    """Internal collection seam for a qualified client; no retry/resume interface."""
    if client.authorization['schema_version'] != 'controlled-openrouter-pilot-v1':
        raise ValueError('qualified pilot profile required')
    key = secrets.token_bytes(32)
    plan = make_plan(key)
    validate_plan(plan)
    pairs = {p['pair_id']: p for p in plan['pairs']}
    calls = []
    for call in plan['schedule']:
        visible = provider_input(pairs[call['pair_id']]['facts'], call['presentation'])
        body = client._body(visible['instruction'], canonical_json(visible['facts']), client.max_output_tokens)
        calls.append({'call_id': call['trial_id'], 'request_sha256': digest(body)})
    store = Store(output, plan, client.authorization)
    token = client.ledger.claim_cohort(client.authorization, calls, plan_sha256=digest(plan),
                                       output_dir=str(Path(output).resolve()))
    reason = None
    for call in plan['schedule']:
        identity = call['trial_id']; pair = pairs[call['pair_id']]; facts = pair['facts']
        try:
            store.start(identity)
            outcome = client.recommend(facts, call['presentation'], call_id=identity, cohort_token=token)
            store.outcome(identity, outcome)
            if outcome['status'] != 'succeeded':
                reason = 'invalid_output'; store.finish(identity, 'invalid_output'); break
            controller = Controller(store.path, key, identity)
            controller.set_policy(facts['run_id'], facts['artifact_digest'], True)
            proposal = outcome['proposal']; decision_id = uuid.uuid4().hex
            controller.record_decision(decision_id, facts['run_id'], facts['artifact_digest'],
                proposal['recommendation'], proposal['reason'], facts['receipts'],
                provider_input(facts, call['presentation']), actor='live-supervisor')
            if pair['family'] == 'revocation':
                controller.set_policy(facts['run_id'], facts['artifact_digest'], False)
            if proposal['recommendation'] == 'approve':
                controller.execute(decision_id, uuid.uuid4().hex)
                if pair['family'] == 'duplicate': controller.execute(decision_id, uuid.uuid4().hex)
            store.finish(identity, 'completed')
            client.ledger.finish_cohort_call(identity, token)
        except ProviderError as error:
            reason = 'provider_or_accounting_failure'
            # The canonical ledger already retains attempts; do not duplicate exception text.
            store.finish(identity, 'provider_failed', error.status)
            break
        except Exception as error:
            reason = 'local_failure'
            store.finish(identity, 'interrupted', type(error).__name__)
            break
    store.stop(reason)
    client.ledger.stop_cohort(token, reason or 'completed')
    report = export_report(store.path, client.ledger.path)
    save_report(output, report)
    return report


def run_pilot(authorization_path, calibration_path, output_dir, *, live=False):
    if live is not True: raise ValueError('paid pilot requires explicit --live selection')
    operator.require_committed_source()
    records = operator.load_authorizations(authorization_path)
    if len(records) != 1 or ('openrouter', MODEL) not in records:
        raise ValueError('one frozen pilot model required')
    record = validate_record(records['openrouter', MODEL])
    path = private_path(calibration_path)
    if not path.is_file() or path.stat().st_size > 262144: raise ValueError('bounded private calibration packet required')
    packet = json.loads(path.read_text(), object_pairs_hook=operator._object)
    validate_calibration(packet, record)
    # Use the exact detached record whose calibration was checked. Re-reading
    # the filename here could substitute a different otherwise valid profile.
    from .swarm.providers import Ledger, ModelClient
    ledger = Ledger(record['provider'], record['run_cap_usd'], record['provider_cap_usd'],
                    Path(record['ledger_path']), run_id=record['run_id'])
    client = ModelClient(record['provider'], record['model'], ledger, authorization=record,
                         max_output_tokens=record['max_output_tokens'], timeout=record['timeout_s'])
    return collect(client, output_dir)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--authorization', type=Path)
    parser.add_argument('--calibration', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--live', action='store_true')
    parser.add_argument('--recover', type=Path, help='Existing pilot database; export only, never resume')
    parser.add_argument('--ledger', type=Path, help='Canonical ledger for export-only recovery')
    args = parser.parse_args()
    if args.recover:
        if args.live or args.authorization or args.calibration or not args.ledger:
            parser.error('recovery permits only --recover, --ledger and a fresh --output directory')
        output = private_path(args.output); private_path(output.parent); output.mkdir(mode=0o700)
        report = export_report(args.recover, args.ledger); save_report(output, report)
    else:
        if args.ledger: parser.error('--ledger is only for export recovery')
        report = run_pilot(args.authorization, args.calibration, args.output, live=args.live)
    print(canonical_json({'mode': report['mode'], 'summary': report['summary'], 'stop_reason': report['stop_reason']}))


if __name__ == '__main__':
    main()
