# Evidence map and reproduction

This package contains the report, editable source, one original figure, bibliography/provenance records, copy-ready submission text, two PNG images, a standalone verifier and a derived public trial table. It excludes credentials, private account records, provider response envelopes and the large historical archive. The complete implementation and historical archive are in the linked repository.

## Verify the package

From the repository checkout (Python standard library only):

```sh
python3 -m scripts.verify_submission
```

This checks the ZIP against the current repository bytes. To check a downloaded
ZIP without extracting it, use a trusted copy of the verifier:

```sh
python3 -m scripts.verify_submission --package PATH_TO_ZIP
```

From an extracted package directory, the included standalone copy also works:

```sh
python3 -B verify_submission.py
```

Use a verifier obtained from a trusted checkout. A script inside an arbitrary
archive is code; checksums alone do not establish its authenticity.

The verifier rejects unexpected, missing, duplicate, linked and oversized files.
It checks exact checksum coverage, current provenance hashes, title/author/abstract
consistency and every public trial's closed scalar schema. It recomputes balanced
pairs, cell outcomes, effects, attempts, token totals and charges, then checks the
immutable public-table digest. Interpretation labels must match the published
contrast. Only stored and DEFLATE ZIP members are supported. It makes no
network calls, extracts nothing, executes no bundled code and never repairs inputs.
Success is JSON on stdout; failure is a nonzero exit with a sanitized message.

Expected results: **160 trials, 80 pairs; raw 18 invalid approvals and zero invalid
denials; scope explicit zero invalid approvals and 40 invalid denials; 30 effects,
68 attempts, 28 authorization denials, ten duplicate no-ops; $0.2605526 provider
charge**. These are 80 pairs, not 160 independent samples. `valid_decisions` in the
source summary means schema-accepted decisions, not correct recommendations.

SHA-256 identifies bytes; it is not a signature or evidence of provider execution.
Public rows omit prompts and reasons, so aggregate consistency is not full private
trace replay. PDF layout and the separate video are inspected independently.

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
