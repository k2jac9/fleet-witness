"""Dependency-free command line entry point."""
import argparse
import json
from pathlib import Path

from .experiment import run_demo
from .server import serve


def main(argv=None):
    parser = argparse.ArgumentParser(description='Fleet Witness local scripted evaluation')
    commands = parser.add_subparsers(dest='command', required=True)
    demo = commands.add_parser('demo', help='generate a scripted demo; no model API calls')
    demo.add_argument('--output', type=Path, default=Path('runs/demo'))
    demo.add_argument('--seed', type=int, default=42)
    viewer = commands.add_parser('serve', help='serve only local read-only replay assets')
    viewer.add_argument('--directory', type=Path, default=Path('runs/demo'))
    viewer.add_argument('--port', type=int, default=8765)
    args = parser.parse_args(argv)
    try:
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
