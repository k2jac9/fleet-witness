# Run logs for the Fleet Witness swarm report (2026-11-08)

`fleet-witness-runs-2026-11-08.zip` holds every run used in `docs/report/REPORT.md`. Extract it
at the repository root to recreate `runs/`.

## Contents

| Path | What it is |
| --- | --- |
| `runs/sweep-deepseek2k/f00..f50` | Main sweep, DeepSeek v4 Flash, 2,000-token cap with truncation audit. `f30` is the pre-declared re-run. |
| `runs/deepseek2k-f30-truncated` | The superseded original `f30` run (one colluder response hit the cap). Kept for transparency. |
| `runs/sweep-gptoss/f00..f50` | Main sweep, gpt-oss-20b, same seeds. |
| `runs/sweep-or/f00..f50` | 600-token DeepSeek pilot (not used for main results; source of the truncation-by-role observation). |
| `runs/ambig-{deepseek,gptoss}-s{3000,4000,5000}` | Near-miss (ambiguous-mode) runs, 0% and 30% cells. |
| `runs/verify-depth6.txt` | Bounded checker output (depth 6, with mutants). |

Each run directory contains:
- `events.jsonl`: the public log, one line per vote or attestation, with token usage and cost;
- `truth.json`: sealed ground truth (colluders, targets, committees, case kinds);
- `decisions.json`: the outcome under every governance regime;
- `manifest.json`: model, seed, share, calls, errors, cost and completeness;
- `analysis.json`: detector and metrics output.

Prompts are in `fleet_witness/swarm/runner.py`. Signing keys are never written to disk. The
logs contain only synthetic tasks and model outputs, with no personal data.

## Reproduce every table

```sh
python scripts/reproduce_tables.py
```

This makes no model calls. The bounded checker takes about 5 minutes.
