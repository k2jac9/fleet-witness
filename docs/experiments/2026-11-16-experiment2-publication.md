# Experiment 2 publication successor — 16 November 2026

Follow-up to [issue #17](https://github.com/k2jac9/fleet-witness/issues/17),
based on merged PR #20 (`e48a75a331b61cfa7f0b861805f485a0e5c47bc5`).
This is a new derivative of an already-public archive, prepared with AI assistance.
It adds no experimental observations and does not replace historical inputs.

## Exact inputs and outputs

| Artifact | SHA-256 |
| --- | --- |
| `data/fleet-witness-judge-runs-2026-11-10.zip` | `56d38f3dfec31a7c1d87773ff1001f792d105502838342546f0e4a4a12d36eb0` |
| `data/fleet-witness-judge-runs-public-2026-11-16.zip` | `f19127a49dea94e581e3714be3733ba480db7405632f1292b1f737273a23da04` |
| Successor `experiment2-runs/SANITIZATION.json` | `e62c150b8dc562fa9877a4c08270c2f7a34763f7c4dea0c37e9be36a6f062c7c` |

The successor is 16,289,302 bytes, with 78 members totaling 179,076,908
expanded bytes. Verification reads bounded members in memory without extraction.

Eleven run manifests replace `/runtime/python_executable` with
`[REDACTED: machine-local executable path]`. Their JSON is serialized with sorted
keys and two-space indentation. All other fields retain their values. The
remaining 66 data members are byte-identical, including all retained prompts,
responses, events, decisions, labels, SQLite databases and analyses. The three
prior packaging metadata files are omitted from the successor and represented
by their hashes and sizes in the new mapping; they remain in the historical ZIP.

`SANITIZATION.json` names all 80 source members. Each retained member records
its source and successor hashes/sizes, destination, action and changed JSON
pointer. Omitted packaging members have a null destination and an explicit
reason. Neither the removed path values nor a private-original inventory appears
in the new mapping. Historical synthetic-key substitutions remain unchanged.
The map links to the prior **public** archive; it is not a newly obtained inventory
of private originals.

## Verification and limits

```sh
python3 -B scripts/sanitize_experiment2_archive.py verify
python3 -B -m unittest discover -s tests -p 'test_experiment2*.py' -v
```

The verifier pins the source archive identity, verifies its original/public
member hashes, computes the allowed transformation from the source, compares
every successor member and the complete mapping, and runs the existing full
record verifier. The unchanged experimental bytes retain all 41,995 prompt/receipt
bindings across 14 runs and all 46 selected frozen-count comparisons, with no
mismatches. The three incomplete runs and their unknown final liability remain
incomplete; redaction does not fill missing evidence.

The bounded privacy check looks for Windows user-home paths, POSIX home paths,
UNC paths and private-key markers. The initial review's email-like matches were
Python decorators inside retained prompts. This is not an exhaustive privacy,
credential, provenance or provider-authenticity audit. The historical public ZIP
and Git history still contain the removed path values. The successor reduces
their exposure in this new artifact; it does not retract prior publication.

The first build refused a relative Windows path because the UNC detector
misclassified it. A regression test reproduced that failure before correction;
actual and JSON-escaped UNC paths remain refused. The failed log and partial ZIP
are retained outside the repository. No experimental record was edited to make
the scanner pass.

Local Python 3.15.2 validation passed all 412 tests, including 33 focused archive
tests; the five viewer tests, fleet validation/planning, submission verifier and
runtime-freshness check also passed. Full-suite generated scratch used bounded
tmpfs under the owner's expiring task storage exception; retained outputs stayed
in the project artifact directory. Existing SQLite ResourceWarnings remain visible.
Hosted execution and independent review of this successor are recorded in the
PR, separately from these local results.

## Remaining issue acceptance

The [reviewer handoff](experiment2-reviewer-handoff.md) provides exact-input
checks, rebuilding and verification commands, and an unfilled result template.
An agent's rehearsal or code review does not satisfy the second-person human
reproduction requirement.

The source holder still needs to provide a private preservation/search inventory:
which original output directories/backups were checked, recovery dates, original
file sizes and SHA-256 hashes, missing artifacts, and preservation locations.
This task accessed only the existing public archive; it did not search the source
holder's machine or confirm private backups. Provider billing, historical
signature authenticity and unrecorded stopped-run liability remain unknown.
Issue #17 stays open. No paid calls or new credentials were used.
