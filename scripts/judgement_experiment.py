"""Experiment 2 driver: live swarm on pull-request review cases (case_mode='judgement').

Standalone execution path, NOT the repository's gated paid workflow: run by a team member with their own
OpenRouter key before the hackathon deadline (see docs/report/JUDGEMENT_PLAN.md). It reuses the unmodified
swarm runner and institution kernel; only the model client differs. Every request and response is written
to each run's private/requests.jsonl, and a hard global spend cap aborts the run when reached.

Usage:
  python scripts/judgement_experiment.py --model deepseek/deepseek-v4-flash-0731 --label deepseek \
      --shares 0 0.2 0.4 --out runs/judge --max-usd 8
"""
import argparse
import json
import os
from pathlib import Path
import sys
import threading
import time
import urllib.error
import urllib.request

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
# Windows lacks these POSIX open() flags used by the run logger; without symlinks in the fresh
# output directory they have no effect, so a zero stand-in keeps behaviour identical.
for _flag in ('O_NOFOLLOW', 'O_DIRECTORY'):
    if not hasattr(os, _flag):
        setattr(os, _flag, 0)
from fleet_witness.swarm.providers import BudgetExceeded, ProviderError  # noqa: E402
from fleet_witness.swarm.runner import run_swarm  # noqa: E402

URL = 'https://openrouter.ai/api/v1/chat/completions'


class OpenRouterClient:
    """Minimal client matching the interface run_swarm expects (ledger=None enables parallel requests)."""

    ledger = None
    authorization = None

    def __init__(self, model, max_usd, max_output_tokens=2000, temperature=0.7, timeout=180):
        self.model, self.label = model, f'openrouter:{model}'
        self.max_output_tokens, self.temperature, self.timeout = max_output_tokens, temperature, timeout
        self.cap, self.spent, self.lock = max_usd, 0.0, threading.Lock()

    def maximum_request_usd(self):
        return 0.0

    def complete(self, system, user, meta=None):
        with self.lock:
            if self.spent >= self.cap:
                raise BudgetExceeded(f'spend cap ${self.cap} reached')
        body = json.dumps({'model': self.model, 'temperature': self.temperature,
                           'max_tokens': self.max_output_tokens, 'usage': {'include': True},
                           'messages': [{'role': 'system', 'content': system},
                                        {'role': 'user', 'content': user}]}).encode()
        headers = {'Authorization': f"Bearer {os.environ['OPENROUTER_API_KEY']}",
                   'Content-Type': 'application/json', 'X-Title': 'fleet-witness experiment 2'}
        started = time.monotonic()
        attempts = []
        for attempt in range(1, 4):  # transport retries only; recorded
            try:
                request = urllib.request.Request(URL, data=body, headers=headers, method='POST')
                with urllib.request.urlopen(request, timeout=self.timeout) as response:
                    payload = json.loads(response.read())
                if 'choices' not in payload:
                    raise ProviderError(f"no choices: {str(payload)[:200]}")
                break
            except urllib.error.HTTPError as error:
                attempts.append({'attempt': attempt, 'status': f'http_{error.code}'})
                if error.code not in (408, 429, 500, 502, 503, 504) or attempt == 3:
                    raise ProviderError(f'HTTP {error.code}')
            except (urllib.error.URLError, TimeoutError, ConnectionError, ProviderError) as error:
                attempts.append({'attempt': attempt, 'status': f'transport:{type(error).__name__}'})
                if attempt == 3:
                    raise ProviderError(str(error)[:200])
            time.sleep(2 * attempt)
        choice = payload['choices'][0]
        usage = payload.get('usage') or {}
        cost = float(usage.get('cost') or 0.0)
        with self.lock:
            self.spent += cost
        finish = choice.get('finish_reason')
        attempts.append({'attempt': len(attempts) + 1, 'status': 'succeeded', 'finish_reason': finish,
                         'cost_usd': cost})
        return {'text': choice['message'].get('content') or '', 'latency_s': round(time.monotonic() - started, 3),
                'input_tokens': usage.get('prompt_tokens'), 'output_tokens': usage.get('completion_tokens'),
                'cost_usd': cost, 'status': 'completed', 'truncated': finish == 'length',
                'attempts': attempts, 'provider_attempts': len(attempts)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--model', required=True)
    parser.add_argument('--label', required=True)
    parser.add_argument('--shares', type=float, nargs='+', default=[0.0, 0.2, 0.4])
    parser.add_argument('--agents', type=int, default=50)
    parser.add_argument('--cases', type=int, default=24)
    parser.add_argument('--conditions', nargs='+', default=['hidden-cell', 'visible-cell'])
    parser.add_argument('--out', required=True)
    parser.add_argument('--max-usd', type=float, required=True)
    parser.add_argument('--max-tokens', type=int, default=2000)
    args = parser.parse_args()
    if 'OPENROUTER_API_KEY' not in os.environ:
        parser.error('OPENROUTER_API_KEY is not set')
    client = OpenRouterClient(args.model, args.max_usd, max_output_tokens=args.max_tokens)
    root = Path(args.out) / args.label
    for share in args.shares:
        seed = 7000 + round(share * 100)  # paired across models
        out = root / f'f{round(share * 100):02d}'
        started = time.monotonic()
        manifest = run_swarm(out, client, agents=args.agents, cases=args.cases, conditions=args.conditions,
                             cell_fraction=share, seed=seed, case_mode='judgement')
        manifest['execution_path'] = 'standalone (scripts/judgement_experiment.py); not the gated paid workflow'
        (out / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
        print(f"{args.label} share={share}: {manifest['calls']} calls, {manifest['errors']} errors, "
              f"{manifest['abstentions']} abstentions, ${manifest['cost_usd']:.3f}, "
              f"{time.monotonic() - started:.0f}s, total ${client.spent:.3f}", flush=True)


if __name__ == '__main__':
    main()
