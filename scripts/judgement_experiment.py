"""Authorized Experiment 2 driver using the existing single-attempt paid client.

Historical standalone runs remain historical. Future calls require a reviewed,
clean source tree, explicit source-bound operator records, and --live. All models
in an orchestrated job must share the same canonical ledger/run envelope, with
an Experiment 2 run cap no larger than $15. No implicit retries or Windows flag
substitutes are supported. See docs/SWARM.md for the operator record contract.

Usage (placeholders, not qualification):
  python scripts/judgement_experiment.py --model VERIFIED_MODEL --label model \
      --shares 0 0.2 0.4 --out runs/judge-new \
      --authorization /private/qualified-records.json --live
"""
import argparse
import json
import math
from pathlib import Path
import re
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fleet_witness.swarm.providers import ProviderError  # noqa: E402
from fleet_witness.swarm.runner import run_swarm  # noqa: E402
from scripts.research_requests import paid_arguments, research_clients  # noqa: E402


def OpenRouterClient(model, max_usd=None, max_output_tokens=None, temperature=.7, *,
                     authorization=None, live=False, shared_models=()):
    """Compatibility factory returning the real ModelClient, never a second ledger."""
    clients = research_clients([model, *shared_models], authorization, live=live, max_usd=max_usd,
                               max_output_tokens=max_output_tokens, temperature=temperature, max_run_usd=15)
    return clients[model]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model', required=True)
    parser.add_argument('--label', required=True)
    parser.add_argument('--shares', type=float, nargs='+', default=[0.0, 0.2, 0.4])
    parser.add_argument('--agents', type=int, default=50)
    parser.add_argument('--cases', type=int, default=24)
    parser.add_argument('--conditions', nargs='+', default=['hidden-cell', 'visible-cell'])
    parser.add_argument('--out', required=True)
    parser.add_argument('--shared-models', nargs='+', default=[],
                        help='all models in the orchestration; their records must share one run envelope')
    paid_arguments(parser)
    args = parser.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,63}', args.label):
        parser.error('--label must be a simple directory name')
    if any(not math.isfinite(share) or not 0 <= share <= 1 for share in args.shares):
        parser.error('--shares must be finite fractions between zero and one')
    if len({round(share * 100) for share in args.shares}) != len(args.shares):
        parser.error('--shares must map to distinct run directories')
    try:
        client = OpenRouterClient(args.model, args.max_usd, args.max_tokens,
                                  authorization=args.authorization, live=args.live,
                                  shared_models=args.shared_models)
    except (ProviderError, ValueError, OSError) as error:
        parser.error(str(error))
    root = Path(args.out) / args.label
    for share in args.shares:
        seed = 7000 + round(share * 100)  # paired across models
        out = root / f'f{round(share * 100):02d}'
        started = time.monotonic()
        manifest = run_swarm(out, client, agents=args.agents, cases=args.cases, conditions=args.conditions,
                             cell_fraction=share, seed=seed, case_mode='judgement')
        manifest.update(execution_path='authorized ModelClient / shared SQLite ledger', gated_workflow=True)
        (out / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
        print(f"{args.label} share={share}: {manifest['calls']} calls, {manifest['errors']} errors, "
              f"{manifest['abstentions']} abstentions, ${manifest['cost_usd']:.3f}, "
              f"{time.monotonic() - started:.0f}s, shared run ${client.ledger.run_spent:.3f} settled / "
              f"${client.ledger.run_reserved:.3f} held", flush=True)
        if manifest['incomplete'] or manifest['errors'] or manifest['abstentions']:
            return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
