"""Time candidate reviewer models on the real review task (same prompt, paper, reasoning effort).

Usage: python scripts/reviewer_speedtest.py --paper docs/report/REPORT.md --out runs/speedtest-new.json \
    --authorization /private/path/review-authorization.json
Reports wall-clock seconds, output tokens, cost, whether the JSON parsed, number of concerns and
rubric scores, so speed can be weighed against substance.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import time
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from fleet_witness.swarm.operator import authorized_clients  # noqa: E402
from fleet_witness.swarm.run_records import PrivateRunLog, public_attempts, runtime_identity  # noqa: E402
from peer_review import REVIEW_TASK, SYSTEM, extract_json  # noqa: E402

CANDIDATES = [
    'x-ai/grok-4.7', 'qwen/qwen3.8-max-0902',            # current slow reviewers (baseline)
    'moonshotai/kimi-k3.1-pro', 'deepseek/deepseek-v4-pro', 'xiaomi/mimo-v2.6-pro', 'meta/muse-spark-1.3',
    'meta/muse-wonder', 'mistralai/mistral-large-4-0', 'minimax/minimax-m3', 'z-ai/glm-5.3', 'tencent/hy3',
    'cohere/command-a-plus', 'stepfun/step-3.7-flash', 'x-ai/grok-4.20', 'openai/gpt-6.1-terra',
    'google/gemini-3.1-pro-preview',
]


def run(model, client, paper, receipts):
    started = time.monotonic()
    task = REVIEW_TASK.format(paper=paper)
    text, attempts, status = None, [], 'provider_error'
    result = None
    try:
        client.extra_body = {'reasoning': {'effort': 'high'}}
        result = client.complete(SYSTEM, task)
        text = result['text']
        attempts = public_attempts(result.get('attempts', []))
        status = result.get('status', 'completed')
        if result.get('truncated') or status not in ('succeeded', 'completed', 'settled'):
            raise ValueError('incomplete review response')
        parsed = extract_json(text)
        return {'model': model, 'seconds': round(time.monotonic() - started, 1), 'ok': 'unparsed' not in parsed,
                'output_tokens': result['output_tokens'], 'cost_usd': result['cost_usd'],
                'concerns': len(parsed.get('concerns', []) or []), 'scores': parsed.get('scores'),
                'verdict': parsed.get('verdict'), 'attempts': attempts, 'status': status,
                'provider_attempts': result.get('provider_attempts', 0),
                'held_usd': result.get('held_usd', 0), 'review': parsed}
    except Exception as error:  # record and continue
        accounting = result if result is not None else {
            key: getattr(error, key, default) for key, default in
            (('attempts', []), ('provider_attempts', 0), ('cost_usd', 0), ('held_usd', 0),
             ('status', 'provider_error'))}
        attempts = public_attempts(accounting.get('attempts', []))
        status = accounting.get('status', 'provider_error')
        return {'model': model, 'seconds': round(time.monotonic() - started, 1), 'ok': False,
                'error': type(error).__name__, 'attempts': attempts, 'status': status,
                'provider_attempts': accounting.get('provider_attempts', 0),
                'cost_usd': accounting.get('cost_usd', 0), 'held_usd': accounting.get('held_usd', 0)}
    finally:
        receipts.write(uuid.uuid4().hex, SYSTEM, task, text, status, attempts)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--paper', required=True)
    parser.add_argument('--out', required=True)
    parser.add_argument('--authorization', type=Path, required=True,
                        help='private model authorizations sharing one run envelope')
    parser.add_argument('--max-usd', type=float, help='must match the frozen authorized cap')
    args = parser.parse_args()
    paper = Path(args.paper).read_text(encoding='utf-8')
    output = Path(args.out)
    receipt_root = output.with_name(output.name + '.run')
    if output.exists() or receipt_root.exists():
        parser.error('output already exists; choose a fresh output')
    clients = authorized_clients('openrouter', CANDIDATES, args.authorization,
                                 max_usd=args.max_usd, temperature=0.3)
    receipt_root.mkdir(mode=0o700)
    receipts = PrivateRunLog(receipt_root)
    from fleet_witness.swarm.providers import source_identity
    manifest = {'schema_version': 'swarm-speedtest-2', 'source': source_identity(),
                'runtime': runtime_identity(), 'paper_sha256': hashlib.sha256(paper.encode()).hexdigest(),
                'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                'status': 'started', 'private_receipts': 'private/requests.jsonl'}
    results = []
    descriptor = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, 'w', encoding='utf-8') as handle:
        try:
            for model in CANDIDATES:
                result = run(model, clients[model], paper, receipts)
                results.append(result)
                if result.get('held_usd') or result.get('status') == 'unresolved':
                    manifest['status'] = 'halted'
                    break
            else:
                manifest['status'] = 'completed'
        except Exception as error:
            manifest.update(status='failed', error=type(error).__name__)
            raise
        finally:
            json.dump(results, handle, indent=2, allow_nan=False)
            manifest.update(receipts.summary())
            (receipt_root / 'manifest.json').write_text(json.dumps(manifest, indent=2, allow_nan=False), encoding='utf-8')
            receipts.close()
    print(f"{'model':<34} {'secs':>6} {'ok':>4} {'out_tok':>8} {'cost':>7} {'concerns':>8}  scores (I/E/P)  verdict")
    for r in sorted(results, key=lambda r: r['seconds']):
        s = r.get('scores') or {}
        sc = f"{s.get('impact_innovation', '-')}/{s.get('execution', '-')}/{s.get('presentation', '-')}"
        print(f"{r['model']:<34} {r['seconds']:>6} {str(r['ok']):>4} {str(r.get('output_tokens', '-')):>8} "
              f"{str(r.get('cost_usd', '-')):>7} {str(r.get('concerns', '-')):>8}  {sc:<14} {r.get('verdict', r.get('error', ''))}")


if __name__ == '__main__':
    main()
