"""Regenerate every reported table from the published run logs (no model calls).

  python scripts/reproduce_tables.py            # expects runs/ extracted from data/fleet-witness-runs-2026-11-08.zip
Runs: per-cell summaries, pooled stats, exact intervals, gated-majority baseline and per-share counts,
near-miss honest-error analysis, and the bounded checker (depth 6 with mutants; about 5 minutes).
"""
import subprocess
import sys

STEPS = [
    [sys.executable, '-m', 'fleet_witness', 'swarm-summary', 'runs/sweep-deepseek2k'],
    [sys.executable, '-m', 'fleet_witness', 'swarm-summary', 'runs/sweep-gptoss'],
    [sys.executable, 'scripts/report_stats.py', 'runs/sweep-deepseek2k', 'runs/sweep-gptoss'],
    [sys.executable, 'scripts/baselines.py', 'runs/sweep-deepseek2k', 'runs/sweep-gptoss'],
    [sys.executable, 'scripts/independence.py', '--model', 'DeepSeek=runs/ambig-deepseek-s*',
     '--model', 'gpt-oss=runs/ambig-gptoss-s*'],
    [sys.executable, '-m', 'fleet_witness.verify_institution', '--depth', '6', '--mutants'],
]

for step in STEPS:
    print('\n$ ' + ' '.join(step), flush=True)
    subprocess.run(step, check=True)
