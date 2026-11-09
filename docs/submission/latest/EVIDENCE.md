# Evidence map and reproduction

This package contains the report, editable source, one original figure, bibliography/provenance records, copy-ready submission text and a derived public trial table. It excludes credentials, private account records, provider response envelopes and the large historical archive. The complete implementation and historical archive are in the linked repository.

## Verify the package

From the extracted package directory on Linux:

```sh
sha256sum -c SHA256SUMS
```

The manifest covers every member except itself. SHA-256 identifies the distributed bytes; it is not an external signature or an attestation of provider execution.

## Recompute the new pilot's public totals

Run this standard-library script from the extracted directory. It reads only the included JSON and makes no network calls:

```sh
python3 - <<'PY'
import json
from decimal import Decimal
from pathlib import Path
r = json.loads(Path('paired-pilot-2026-11-09.json').read_text())
t = r['trials']
assert len(t) == 160 and len({x['pair_id'] for x in t}) == 80
for presentation in ('raw', 'scope_explicit'):
    rows = [x for x in t if x['presentation'] == presentation]
    invalid_approvals = sum(x['recommendation'] == 'approve' and not x['decision_valid_at_snapshot'] for x in rows)
    invalid_denials = sum(x['recommendation'] == 'deny' and not x['decision_valid_at_snapshot'] for x in rows)
    print(presentation, len(rows), invalid_approvals, invalid_denials)
assert sum(x['effects'] for x in t) == 30
assert sum(x['execution_attempts'] for x in t) == 68
assert sum(x['authorization_denials'] for x in t) == 28
assert sum(x['duplicate_noops'] for x in t) == 10
assert sum(Decimal(x['provider_reported_cost_usd']) for x in t) == Decimal('0.2605526')
print('effects=30; denied attempts=28; duplicate no-ops=10; charge=$0.2605526')
PY
```

Expected presentation rows: `raw 80 18 0` and `scope_explicit 80 0 40`. These numbers describe 80 pairs, not 160 independent samples. Decision-time labels are evaluator outputs, not model inputs. Public rows omit prompts and reasons; they support aggregate recomputation, not full private-trace replay or independent provider/account authentication.

## Test the code without paid calls

Clone `https://github.com/k2jac9/fleet-witness.git` and use the revision containing this package. `latest.provenance.json` separately pins the historical reanalysis and the completed pilot's source. Use the repository's `ci/runtime-matrix.json` and standard-library runtime:

```sh
python3 -m unittest discover -s tests -v
node --test tests/viewer.test.mjs
python3 -m fleet_witness demo --output runs/submission-demo --seed 42
python3 -m fleet_witness serve --directory runs/submission-demo --port 8765
```

The default demo is scripted, creates local database effects and refuses to overwrite an existing run. Use a fresh output directory. Open http://127.0.0.1:8765. Paid calls, cloud deployment and live observation are not part of these commands.

## Reproduce the historical analysis

From the repository, choose fresh directories with enough admitted disk space:

```sh
python3 scripts/extract_run_archive.py --archive data/fleet-witness-runs-2026-11-08.zip --destination FRESH_INPUT
python3 scripts/reproduce_tables.py --input-root FRESH_INPUT/runs --output-root FRESH_DERIVED --skip-checker
```

The repository's [historical reproduction receipt](https://github.com/k2jac9/fleet-witness/blob/ee7c17e6f8b50684084caf6f6900c577801351c5/docs/report/REPRODUCTION-REVIEW-FIX-2026-11-09.json) records the earlier completed reanalysis and bounded checker. It is linked rather than copied into this portable package because it contains a workstation-local artifact path. Omitting `--skip-checker` runs the checker as well; that can be substantially more expensive than recomputing tables. The publication task did not rerun depth-six exploration or any paid experiment. Historical original provider-attempt counts, raw envelopes, executable identity and issuer keys are incomplete. Fresh synthetic replay cannot authenticate the original receipts.

## Evidence boundaries

- The original swarm experiment has 32,830 completed logical responses, with shared outputs across regimes; its historical costs are not reconciled bills.
- The new pilot has 160 completed provider requests, one live supervisor, synthetic worker/reviewer inputs and 30 local effects. Its provider charge reconciled after a delayed accounting refresh.
- A separate one-call transport stop and calibration calls remain excluded and retained in project evidence. No stopped cohort resumed.
- No uncontrolled web swarm, public honeypot, production isolation or improved useful model judgment is established.
- Full private interaction and billing evidence stays outside this package. The provenance digests identify those records without exposing account details.
