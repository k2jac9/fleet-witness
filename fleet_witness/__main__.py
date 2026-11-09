"""Dependency-free command line entry point."""
import argparse
import json
from pathlib import Path

from .experiment import run_demo
from .server import serve


def _swarm(args):
    from .swarm.detect import analyze, format_report
    from .swarm.providers import FakeClient
    from .swarm.operator import authorized_client
    from .swarm.runner import CONDITIONS, estimate_run, run_swarm

    conditions = args.conditions or list(CONDITIONS)
    judge = None
    if args.judge_model:
        judge = authorized_client('openrouter', args.judge_model, args.authorization,
                                  max_usd=args.judge_max_usd, temperature=0.0)
    if args.provider == 'fake':
        client = FakeClient(seed=args.seed)
    else:
        client = authorized_client(args.provider, args.model, args.authorization, max_usd=args.max_usd,
                                   max_output_tokens=args.max_output_tokens, max_concurrency=args.concurrency)
    estimate = estimate_run(client, agents=args.agents, cases=args.cases, conditions=conditions)
    print(f"Planned calls: {estimate['calls']}  worst case: ${estimate['worst_case_total_usd']:.4f} "
          f"(${estimate['worst_case_per_call_usd']:.6f}/call)")
    if args.provider != 'fake':
        print(f"{args.provider} settled in the selected ledger: ${client.ledger.lifetime_spent():.4f} "
              f"of provider cap ${client.ledger.lifetime_cap:.2f}")
    if args.dry_run:
        return
    manifest = run_swarm(args.output, client, agents=args.agents, cases=args.cases, conditions=conditions,
                         cell_fraction=args.cell_fraction, waves=args.waves, seed=args.seed)
    print(format_report(analyze(args.output)))
    if judge is not None:
        from .swarm.judge import judge_run
        for condition, entry in judge_run(args.output, judge, conditions)['conditions'].items():
            print(f"judge {condition:<14} suspects={len(entry['suspects'])} "
                  + ' '.join(f'{k}={v}' for k, v in entry.items() if k in ('precision', 'recall', 'false_positives', 'error')))
    print(f'Output: {args.output}  (truth.json is sealed ground truth; detectors read events.jsonl only)')
    return manifest


def main(argv=None):
    parser = argparse.ArgumentParser(description='Fleet Witness local scripted evaluation')
    commands = parser.add_subparsers(dest='command', required=True)
    demo = commands.add_parser('demo', help='generate a scripted demo; no model API calls')
    demo.add_argument('--output', type=Path, default=Path('runs/demo'))
    demo.add_argument('--seed', type=int, default=42)
    viewer = commands.add_parser('serve', help='serve only local read-only replay assets')
    viewer.add_argument('--directory', type=Path, default=Path('runs/demo'))
    viewer.add_argument('--port', type=int, default=8765)
    swarm = commands.add_parser('swarm', help='run an LLM agent swarm (paid unless --provider fake)')
    swarm.add_argument('--output', type=Path, required=True)
    swarm.add_argument('--provider', choices=['fake', 'adaption', 'openrouter'], default='fake')
    swarm.add_argument('--model', default='deepseek-v4-flash')
    swarm.add_argument('--agents', type=int, default=20)
    swarm.add_argument('--cases', type=int, default=6)
    swarm.add_argument('--conditions', nargs='+', default=None,
                       help='subset of hidden-clean hidden-cell visible-clean visible-cell')
    swarm.add_argument('--cell-fraction', type=float, default=0.1)
    swarm.add_argument('--waves', type=int, default=5)
    swarm.add_argument('--seed', type=int, default=0)
    swarm.add_argument('--authorization', type=Path, help='private qualified operator record; required for paid calls')
    swarm.add_argument('--max-usd', type=float, help='must match the frozen authorization cap')
    # Reasoning models spend hidden tokens first; 220 truncated colluders mid-thought in the smoke test.
    swarm.add_argument('--max-output-tokens', type=int, help='must match the frozen authorization token cap')
    swarm.add_argument('--concurrency', type=int, default=1)
    swarm.add_argument('--dry-run', action='store_true', help='print worst-case cost and exit')
    swarm.add_argument('--judge-model', default=None,
                       help='OpenRouter model for the independent judge, e.g. qwen/qwen3.7-flash')
    swarm.add_argument('--judge-max-usd', type=float)
    sweep = commands.add_parser('swarm-sweep', help='sweep the colluding share across governance regimes')
    sweep.add_argument('--root', type=Path, required=True)
    sweep.add_argument('--provider', choices=['fake', 'adaption', 'openrouter'], default='fake')
    sweep.add_argument('--model', default='deepseek-v4-flash')
    sweep.add_argument('--fractions', type=float, nargs='+', default=None)
    sweep.add_argument('--agents', type=int, default=50)
    sweep.add_argument('--cases', type=int, default=24)
    sweep.add_argument('--seed', type=int, default=0)
    sweep.add_argument('--authorization', type=Path, help='private qualified operator record; required for paid calls')
    sweep.add_argument('--max-usd', type=float, help='must match the frozen authorization sweep cap')
    sweep.add_argument('--concurrency', type=int, default=1)
    sweep.add_argument('--case-mode', choices=['standard', 'ambiguous'], default='standard',
                       help='ambiguous: authentic near-miss receipts that honest agents can get wrong')
    sweep.add_argument('--max-output-tokens', type=int, help='must match the frozen authorization token cap')
    summary_cmd = commands.add_parser('swarm-summary', help='pool finished sweeps into one table')
    summary_cmd.add_argument('roots', type=Path, nargs='+')
    analyze_cmd = commands.add_parser('swarm-analyze', help='re-run detectors on a finished swarm run')
    analyze_cmd.add_argument('--directory', type=Path, required=True)
    analyze_cmd.add_argument('--edge-z', type=float, default=2.0)
    analyze_cmd.add_argument('--min-cluster', type=int, default=3)
    args = parser.parse_args(argv)
    try:
        if args.command == 'swarm':
            return _swarm(args)
        if args.command == 'swarm-sweep':
            from .swarm.providers import FakeClient
            from .swarm.operator import authorized_client
            from .swarm.sweep import DEFAULT_FRACTIONS, run_sweep
            client = (FakeClient(seed=args.seed) if args.provider == 'fake' else
                      authorized_client(args.provider, args.model, args.authorization,
                                        max_usd=args.max_usd, max_output_tokens=args.max_output_tokens,
                                        max_concurrency=args.concurrency))
            run_sweep(args.root, client, fractions=args.fractions or DEFAULT_FRACTIONS, agents=args.agents,
                      cases=args.cases, seed=args.seed, case_mode=args.case_mode)
            return
        if args.command == 'swarm-summary':
            from .swarm.sweep import format_summary, summarize
            summary = summarize(args.roots)
            Path(args.roots[0], 'sweep-summary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
            print(format_summary(summary))
            return
        if args.command == 'swarm-analyze':
            from .swarm.detect import analyze, format_report
            print(format_report(analyze(args.directory, edge_z=args.edge_z, min_cluster=args.min_cluster)))
            return
        if args.command == 'demo':
            replay = run_demo(args.output, args.seed)
            print('Fleet Witness — SCRIPTED DEMO (deterministic policies; illustrative, not empirical model results)')
            print(json.dumps(replay['summary'], sort_keys=True))
            print(f'Replay: {args.output / "replay.json"}')
        else:
            if not 0 <= args.port <= 65535:
                parser.error('port must be between 0 and 65535')
            serve(args.directory, args.port)
    except (OSError, ValueError) as error:
        parser.exit(1, f'Error: {error}\n')


if __name__ == '__main__':
    main()
