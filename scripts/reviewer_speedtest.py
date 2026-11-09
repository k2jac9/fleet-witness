"""Time candidate reviewer models on the real review task (same prompt, paper, reasoning effort).

Usage: python scripts/reviewer_speedtest.py --paper docs/report/REPORT.md --out docs/report/reviews/speedtest.json
Reports wall-clock seconds, output tokens, cost, whether the JSON parsed, number of concerns and
rubric scores, so speed can be weighed against substance.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
os.environ.setdefault('FLEET_WITNESS_LEDGER_TAG', 'speedtest')
from fleet_witness.swarm.providers import Ledger, ModelClient  # noqa: E402
from peer_review import REVIEW_TASK, SYSTEM, extract_json  # noqa: E402

CANDIDATES = [
    'x-ai/grok-4.7', 'qwen/qwen3.8-max-0902',            # current slow reviewers (baseline)
    'moonshotai/kimi-k3.1-pro', 'deepseek/deepseek-v4-pro', 'xiaomi/mimo-v2.6-pro', 'meta/muse-spark-1.3',
    'meta/muse-wonder', 'mistralai/mistral-large-4-0', 'minimax/minimax-m3', 'z-ai/glm-5.3', 'tencent/hy3',
    'cohere/command-a-plus', 'stepfun/step-3.7-flash', 'x-ai/grok-4.20', 'openai/gpt-6.1-terra',
    'google/gemini-3.1-pro-preview',
]


def run(model, ledger, paper):
    started = time.monotonic()
    try:
        client = ModelClient('openrouter', model, ledger, max_output_tokens=8000, temperature=0.3,
                             timeout=900, max_concurrency=1)
        client.extra_body = {'reasoning': {'effort': 'high'}}
        result = client.complete(SYSTEM, REVIEW_TASK.format(paper=paper))
        parsed = extract_json(result['text'])
        return {'model': model, 'seconds': round(time.monotonic() - started, 1), 'ok': 'unparsed' not in parsed,
                'output_tokens': result['output_tokens'], 'cost_usd': round(result['cost_usd'], 4),
                'concerns': len(parsed.get('concerns', []) or []), 'scores': parsed.get('scores'),
                'verdict': parsed.get('verdict'), 'retries': result.get('truncation_retries', 0),
                'review': parsed}
    except Exception as error:  # record and continue
        return {'model': model, 'seconds': round(time.monotonic() - started, 1), 'ok': False, 'error': str(error)[:200]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--paper', required=True)
    parser.add_argument('--out', required=True)
    parser.add_argument('--max-usd', type=float, default=4.0)
    args = parser.parse_args()
    paper = Path(args.paper).read_text(encoding='utf-8')
    ledger = Ledger('openrouter', run_cap_usd=args.max_usd, lifetime_cap_usd=10)
    with ThreadPoolExecutor(len(CANDIDATES)) as pool:
        results = list(pool.map(lambda m: run(m, ledger, paper), CANDIDATES))
    Path(args.out).write_text(json.dumps(results, indent=2), encoding='utf-8')
    print(f"{'model':<34} {'secs':>6} {'ok':>4} {'out_tok':>8} {'cost':>7} {'concerns':>8}  scores (I/E/P)  verdict")
    for r in sorted(results, key=lambda r: r['seconds']):
        s = r.get('scores') or {}
        sc = f"{s.get('impact_innovation', '-')}/{s.get('execution', '-')}/{s.get('presentation', '-')}"
        print(f"{r['model']:<34} {r['seconds']:>6} {str(r['ok']):>4} {str(r.get('output_tokens', '-')):>8} "
              f"{str(r.get('cost_usd', '-')):>7} {str(r.get('concerns', '-')):>8}  {sc:<14} {r.get('verdict', r.get('error', ''))}")


if __name__ == '__main__':
    main()
