# Assurance integration — 16 November 2026

This candidate integrates the preserved assurance, SQLite fixture cleanup and
source-consistency work with main `206fc9997a7de5e7d46753f5e7f33d8fe222c486`.
The pending provenance work was first preserved at
`1cfc5e0fb05bf99d6358f211258e9bf8f63689fc`. The qualified code commit is
`4ef98144d8395e4268159c3bac9ff6ad4bde5b43`; the containing documentation commit
adds this report without changing that tested code. Original branches, archives,
reports, accepted ADRs and prior failed receipts are preserved.

Malformed institutional evidence and attestations are refused safely. Checker
violations and uncaught mutants produce failing exit statuses and structured
results; explored SQLite connections are closed. New swarm runs use the strict
`swarm-strict-v1` response treatment, private output files and an anchored run
directory. Interrupted runs retain their start record and an incomplete manifest.
Summaries reject unknown or mixed treatments; sweep resume binds the recorded
source, model, authorization and experiment settings, including the six visible
prior comments used by new sweep fractions.

Source maps and matching start/final records establish consistency only. They do
not authenticate a producer or prove which bytes executed; changes reverted
between snapshots can escape detection. Reproduction uses a fresh process and
checks source and input hashes again before issuing a successful receipt.

## Observed local validation

The clean code commit above passed on NixOS x86_64, Python 3.15.2 and local
Node 26.13.0 (the retained stable lane, not the matrix's selected 26.13.1):

- `python3 -B -m unittest discover -s tests -v`: 446 passed in 38.765 seconds;
  no SQLite ResourceWarnings appeared.
- `node --test tests/viewer.test.mjs`: five passed.
- `python3 -B scripts/fleet.py validate` and `plan`: passed.
- `python3 -B scripts/verify_submission.py`: passed offline consistency checks.
- `python3 -B scripts/ci_runtime.py freshness`: passed the November 16 matrix's
  freshness gate; its next review is November 23.
- `python3 -B -m fleet_witness demo --output <fresh-output> --seed 42`: passed,
  using scripted agents.

The first integration run had three failures among 444 tests: two newer synthetic
fixtures returned combined vote/sign objects rejected by the strict parser, and
an older interruption test expected no final manifest. Fixtures now return the
requested role's schema; a separate test requires the combined object to abstain
while preserving charges and receipts. Interruption assertions require a private,
incomplete manifest with matching source/treatment and interruption details.

Independent review also found that sweep resume omitted `recent_comments`. A new
test failed before the correction, then all 68 focused reproduction, provenance
and research-request tests passed. The reviewer approved the corrected code and
verified full-suite log hashes; no Critical, Important or Minor findings remained
in the corrected delta. The earlier November 10 interrupted automated review
remains a separate incomplete review, not an approval.

## Fresh historical reconstruction

```sh
python3 -B scripts/extract_run_archive.py \
  --archive data/fleet-witness-runs-2026-11-08.zip --destination <fresh-import>
python3 -B scripts/reproduce_tables.py \
  --input-root <fresh-import>/runs --output-root <fresh-derived>
```

Both commands exited zero. The archive SHA-256 is
`c55e8acf07ed8dd3c11bc3dc8f70269adebaac6bfa14727642cca7314d1f821a`.
The receipt binds 147 input files, 63 package/script source files and 20 derived
outputs. Inputs, source hashes and HEAD stayed unchanged; the checkout was clean.
Both main-model summaries retain six runs and twelve rows under `legacy-recorded`.
The reproduction also evaluates the six named near-miss datasets.

| Depth-six check | Distinct states | Transitions | Result |
| --- | ---: | ---: | --- |
| Hybrid | 23,376 | 105,708 | No invariant violations |
| Committee only | 27,636 | 120,456 | No invariant violations |
| Seven deliberately broken variants | Separate searches | Separate searches | All caught |

This is synthetic reconstruction using fresh local signing keys and retained
votes/boolean attestations. It does not verify historical signatures, provider
authenticity, billing or exact historical execution, and adds no model observations.
The reproduction receipt SHA-256 is
`d255db5c0f80f548826c4a5a5a7ad65ce931388c223dee93dbdda00f611e5d4e`.

## Retained evidence and remaining boundaries

Local packet:
`/home/neo/Projects/fleet-witness-artifacts/assurance-integration-20261116T101944Z/`.
It contains checkpoint/diff identities, failed and passing logs, review records,
source maps and the new reconstruction. Validation declared 2 GiB retained disk
growth and 1 GiB tmpfs scratch under the existing owner-authorized exception,
expiring November 17 at 05:00 UTC. Shared reservations, metadata/UUID checks and
the ENOSPC latch stayed enforced; the global storage policy was not changed.

Hosted checks for this candidate are recorded on its PR; local results above do
not establish execution of the twelve pinned hosted runtime lanes. Deployment,
provider access, paid calls, fresh human reproduction and historical evidence
authentication are outside these checks. The 32 KiB attestation limit is per
submission, not an aggregate quota or public-service qualification.

The owner closed [issue #17](https://github.com/k2jac9/fleet-witness/issues/17)
after PR #21 merged. The [status reconciliation](https://github.com/k2jac9/fleet-witness/issues/17#issuecomment-6913793535)
preserves that closure and distinguishes it from the outstanding private-original
inventory, second-human reproduction, stopped-run and provider evidence limits.
[Issue #18](https://github.com/k2jac9/fleet-witness/issues/18) remains open: passing
current-environment TLS tests does not diagnose the unavailable historical host.
