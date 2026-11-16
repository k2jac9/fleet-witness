# Experiment 2 recovered-record verification — 16 November 2026

Follow-up to [issue #17](https://github.com/k2jac9/fleet-witness/issues/17).
PR #19 published the archive and merged as
`2160a55324404d6bf9d35d5c7f7132607bbe590f`. This is a new retrospective
verification of that input, not evidence that raw files were available for the
11 November review. The dated correction, original aggregates and archive are
preserved unchanged.

## Reproduction

From the checkout containing this verifier, using the standard library only:

```sh
python -B scripts/verify_experiment2_archive.py > /path/to/new-artifact/experiment2-verification.json
python -B scripts/verify_judgement_aggregates.py --dir docs/report/experiment2
python -B -m unittest discover -s tests -p test_experiment2_archive.py -v
```

Choose a new output file in the project's retained artifact directory. The
verifier reads ZIP members in memory and creates no extracted files, databases,
model calls or network requests. It bounds the archive to 1,000 members,
256 MiB expanded and 32 MiB per member. These limits do not change the existing
extractor's stricter defaults. Record the checkout revision and the emitted
verifier, archive and aggregate hashes with the output; use storage admission
before larger extraction or full-suite workloads.

Input archive SHA-256:
`56d38f3dfec31a7c1d87773ff1001f792d105502838342546f0e4a4a12d36eb0`.
The observed runtime was Python 3.15.2 on the NixOS workstation. The initial
verification used a worktree based on `2160a55`; the script's emitted hash
identifies the additional verifier implementation.

## Observed results

- All 77 data members match `SHA256SUMS-published`; the three metadata members
  bring the ZIP total to 80. Expanded member sizes total 179,062,112 bytes.
- All 63 unchanged members match their original hashes. Reversing only the
  disclosed synthetic-key replacement in memory reconstructs all 14 changed
  members' original hashes. This checks transformation consistency; it does
  not prove that the original files remain preserved on the source machine.
- Across 14 run directories, 41,995 event identities match retained request
  receipts, their restored prompt hashes, recorded attempt details and status.
  Completed manifests agree with response coverage and recorded accounting.
  Per-request costs agree with their bound attempt records, preventing errors
  on different requests from cancelling in a run total. The historical attempt
  objects omit their own held-liability and dispatch-count fields; these are
  explicitly reported as unverified. Event/manifest values for those fields
  are retained but are not an independent accounting cross-check.
- All 46 selected comparisons with frozen `analysis-honest.json` and
  `analysis-swarm.json` match: honest per-case/by-kind counts, attestation
  counts, regime release totals, and persuasion counts by board and wave.
- Main DeepSeek and gpt-oss sweeps each contain 16,416 recorded calls, with
  zero recorded failed calls or retries. Event and receipt cost sums are
  respectively $2.421851620 and $1.339598180. These are recorded charges,
  not independently reconciled provider invoices.
- DeepSeek has 230 abstentions: 203 votes and 27 attestations. Of these, 225
  have a recorded length finish reason, 222 concern safe/forged cases, and
  eight concern harmful cases; six of those eight are from colluders.
  gpt-oss separately has six abstentions, including one harmful-case vote.
- In the gpt-oss 20%/40% attack runs, three of ten harmful gated-majority
  releases require the colluder votes under the within-run tally; honest votes
  alone form a majority for the other seven. This is a tally decomposition,
  not a causal estimate of how comments changed honest responses.

The frozen attestation denominator counts every recorded boolean signature,
including an abstention as no signature. The verifier preserves this convention
for comparison and reports abstentions separately. Vote error rates exclude
unanswered votes. These denominators must not be conflated.

## Incomplete and superseded records

| Run | Retained calls | Recorded event/receipt cost | Missing files |
| --- | ---: | ---: | --- |
| `judge-v1-stopped/deepseek/f00` | 1,823 | $0.267507349 | Manifest, decisions, SQLite database |
| `judge-v1-stopped/gptoss/f00` | 2,915 | $0.220538182 | Manifest, decisions, SQLite database |
| `judge-frontier-v1-stopped/gemini4argon/f00` | 393 | $0.934016000 | Manifest, decisions, SQLite database |
| `judge-frontier-v1-stopped/gpt61sol/f00` | 912 | $1.713158000 | None; manifest declares complete |

The last row is inside a superseded `v1-stopped` collection but is itself a
completed retained run. Directory names do not establish execution status.
For the first three, retained events cannot establish whether additional
requests were dispatched without a durable record. Their full final liability
and completion state remain unknown. Both pilot runs are retained and excluded
from the main results.

## Open acceptance requirements

Issue #17 remains open. This verification does not establish source-holder
private inventory/backup preservation, the completeness of the original search,
external provider authenticity or billing, historical signature authenticity,
or a second human's reproduction from a fresh checkout. It does not re-run the
bootstrap intervals, reference-pairing statistics, scanner or incomplete round-4
model audit. The existing aggregate verifier covers selected arithmetic only.

The published manifests still include machine-local runtime paths. Their
presence is a publication-sanitization follow-up; this report does not repeat
the paths or overwrite the historical archive. Review a separately identified
sanitized successor before making any further publication claim.

Twenty focused verifier tests passed, including tampered hashes, missing
receipts, false transformation counts and altered decision tallies. The first
implementation exposed a verifier error that omitted auditor abstentions;
a failing behavioral fixture was added and the calculation corrected. Those
failed receipts are retained. Independent review additionally found per-request
accounting cancellation and malformed-manifest coverage gaps; regression cases
failed before those checks were corrected. The follow-up independent review
found no remaining code findings and independently passed all twenty verifier
tests. The owner subsequently confirmed a temporary storage override; all 399
tests passed on the current host and each of seven pinned Python runtimes,
including the twenty verifier tests. All five Node lanes also passed. The
[local runtime receipt](../../ci/runtime-validation-20261116.json) retains the
scope and identities. Hosted CI and the historical evidence requirements above
remain open; local tests do not establish external provenance or provider billing.
