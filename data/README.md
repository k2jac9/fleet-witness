# Research data and reproduction

The [latest report](../docs/report/latest.md) uses two separate data sources:
this preserved historical swarm archive and the [public paired-pilot table](paired-pilot-2026-11-09.json).
Their methods, costs and denominators must not be pooled.

## Historical swarm archive, 8 November 2026

`fleet-witness-runs-2026-11-08.zip` is the immutable historical run archive.
SHA-256: `c55e8acf07ed8dd3c11bc3dc8f70269adebaac6bfa14727642cca7314d1f821a`.
Its 153 entries use Windows backslashes. Use the portable extractor below;
ordinary ZIP extraction on Linux does not recreate the intended hierarchy.

## Experiment 2 run archive, 10 November 2026

`fleet-witness-judge-runs-2026-11-10.zip` holds the original Experiment 2
(judgement task) run folders, recovered from the machine that ran them
(issue #17). SHA-256:
`56d38f3dfec31a7c1d87773ff1001f792d105502838342546f0e4a4a12d36eb0`.
It has 80 entries with forward-slash paths under `experiment2-runs/`, and expands
to about 171 MB.

| Path | What it is |
| --- | --- |
| `judge/{deepseek,gptoss}/f00,f20,f40` | Colluder-attack populations (0/20/40% colluders, both boards) and `analysis.json`. |
| `judge-frontier/{gpt61sol,gemini4argon}/f00` | Honest-only frontier runs. |
| `judge-v1-stopped/`, `judge-frontier-v1-stopped/` | Runs stopped before the review-policy fix (the disclosed protocol deviation). Partial by design. |
| `judge-pilot/` | The pilot before filler edits were bundled in. Excluded from results. |

Each complete run folder has `events.jsonl` (every vote and attestation),
`decisions.json`, `truth.json` (sealed labels, colluders, committees),
`manifest.json` (calls, errors, abstentions, cost), `institution.sqlite3` and
`private/requests.jsonl` (the prompts sent and the raw responses).

**One change from the originals.** Case 02's diff contains a synthetic,
non-working Stripe-style key, which models were asked to spot. To keep secret
scanners quiet, the published copy replaces it with `sk_live_FAKE-KEY-REMOVED`
in 14 files. `CHANGES.json` lists them; `SHA256SUMS-original` and
`SHA256SUMS-published` give the hashes before and after. The `prompt_sha256`
values in `events.jsonl` hash the original prompts. Nothing else was changed,
and no real API key or personal contact detail is in the archive.
`scripts/package_experiment2_runs.py` rebuilds the archive from the local folders.

## Experiment 1 contents

| Path | What it is |
| --- | --- |
| `runs/sweep-deepseek2k/f00..f50` | Main DeepSeek v4 Flash sweep, 2,000-token cap; `f30` is the replacement run. Only replacement `f30` retains retry/truncation fields. |
| `runs/deepseek2k-f30-truncated` | Superseded original `f30` run; retained unchanged. |
| `runs/sweep-gptoss/f00..f50` | Main gpt-oss-20b sweep, matching synthetic seeds. |
| `runs/sweep-or/f00..f50` | 600-token DeepSeek pilot; excluded from the main results. |
| `runs/ambig-{deepseek,gptoss}-s{3000,4000,5000}` | Near-miss runs at 0% and 30% cell shares. |
| `runs/verify-depth6.txt` | Historical bounded checker output. |

Each of the 31 run directories contains `events.jsonl`, `truth.json`,
`decisions.json` and `manifest.json`. These retain logical vote/attestation
outcomes, sealed synthetic truth, governance decisions and recorded run/cost
metadata. Only 19 runs contain `analysis.json`; the 12 near-miss runs omit it.
The events are not complete provider-attempt, prompt or response records.
Missing retry fields do not establish zero retries. Recorded costs are not a
reconciled provider bill.

Historical signing keys and receipt bodies were not retained. The scripts
regenerate synthetic cases from manifest count, seed and case mode with fresh
local keys. They check case IDs, kinds, validity, targets, colluders, committee
seats, logical response completeness, recorded tallies and effects against the
retained records. The historical run/artifact receipt identities and signatures
cannot be authenticated from these files. Current prompt source does not prove
which exact prompts or source revision the historical models received.

## Offline reproduction

Choose fresh artifact destinations outside the source and extracted input trees.
For example, from a primary checkout, retain outputs in a sibling artifact
directory. In a worktree, set `artifact_root` to the project's existing artifact
directory. Both destinations below must be new:

```sh
artifact_root="../fleet-witness-artifacts"
mkdir -p "$artifact_root"
python3 scripts/extract_run_archive.py \
  --archive data/fleet-witness-runs-2026-11-08.zip \
  --destination "$artifact_root/reproduction-import"
python3 scripts/reproduce_tables.py \
  --input-root "$artifact_root/reproduction-import/runs" \
  --output-root "$artifact_root/reproduction-derived"
```

Apply workstation storage admission before substantial workloads. Extraction
rejects traversal, Windows drive/device paths, links, path aliases, collisions,
existing destinations and excessive expansion before creating output. Defaults:
1,000 entries, 32 MiB per file, 128 MiB total expanded bytes, ratio at most 200.
A damaged compressed stream can leave a new partial output directory; preserve
it as failed evidence and use another fresh destination for a later attempt.

Reproduction requires all main and near-miss sweep fractions. Individual baseline
commands can analyze a smaller set of complete runs, with denominators derived
from that set. Incomplete runs, missing response slots, mismatched case recipes,
duplicate decisions and inconsistent votes/effects are rejected. No script makes
model calls, uses credentials, or writes into the extracted source data. The
archive, historical analyses and AI reviews remain unchanged.

Outputs include `baselines.json`, `report-stats.json`, `independence.json`,
per-model summary JSON, derived analyses, `tables.txt` and
`reproduction-provenance.json` with input/source/output hashes and runtime identity.
All eight regimes are reported, including 3-of-5. Gated majority runs through the
actual institution with zero seats/quorum, required majority, integrity, current
policy, uniqueness and transactional audit. This is explicitly a **synthetic
reconstruction using recorded votes**, not historical signature verification,
historical policy-state recovery or new model data. Historical policy is assumed
allowed, matching the current synthetic recipe; policy denial/revocation and
atomicity are exercised separately in behavioral tests.

The pooled observations are paired across cases, conditions and regimes. No
ordinary pooled independent-binomial confidence interval is printed. Zero-seat
regimes have no committee-capture prediction. Undefined ratios are JSON `null`.
Mixed-model committees remain offline splices of recorded seats, not new runs.

The default command also executes the depth-six checker with mutants and retains
fresh output separately from the historical checker receipt. `--skip-checker`
explicitly omits that step and records the omission in provenance; it cannot be
reported as a new checker pass. The checker may take several minutes.
