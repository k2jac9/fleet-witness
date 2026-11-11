# PR 16 review corrections

The owner authorized fixing the findings from the review of PR 16 at
`c244c8cb43a0b1e6720ef3b3dfb7f9dba4a60e2c`. This patch updates that PR; it does
not authorize a paid experiment, external submission, or merge to main.

## Approach

Reuse the existing source-bound operator authorization, single-attempt model
client, and durable shared ledger for future research requests. A second
standalone accounting/transport implementation would duplicate the boundary
that already handles reservations, timeouts and unknown charges. Existing
gateway limits remain in force; unsupported image inputs must be refused
explicitly or handled in a clearly labelled text-only review, not silently
flattened or granted new authority.

Keep historical experiment and review records immutable. Correct the report's
public evidence claims and distinguish existing aggregate calculations from
unpublished source events. Add a dated correction note; do not invent missing
Experiment 2 runs, repair old audit receipts, or claim fresh model execution.

Repair the static-analysis adapter and derived summary generator with behavioral
tests. Add retained judgement-mode coverage for case composition, sealed labels,
receipt binding and unchanged pre-existing modes. Rebuild and inspect the PDF
after correcting its source.

## Acceptance

- Missing authorization, insufficient budget and unsupported input cause zero
  provider dispatches. Paid calls remain deliberate and independently qualified.
- Shared reservations and unknown charges persist across clients/processes;
  failures retain attempted-call metadata and never trigger implicit retries.
- Truncated, empty or malformed required reviews/audits produce a partial or
  failed review record, with their usage receipts retained.
- An unavailable scanner cannot report a clean scan. Unsupported and unparsed
  cases remain distinct from successfully scanned negatives.
- Summary numbers are calculated from the supplied input, including exclusions.
- Every universal reproduction statement is scoped to the available evidence;
  attack comparisons avoid unsupported causal attribution.
- Offline tests, the actual merge candidate, report build and an independent
  review are completed before the existing PR branch is advanced.

## Constraints and baseline

Python 3.11+ and the standard library remain the runtime/test baseline. No
credentials or live provider calls are needed. Accepted ADRs are not silently
changed. The pre-existing TLS root-count test fails in this runtime on both the
PR and main because an empty SSL context already contains an environment root;
retain and report that baseline instead of weakening TLS checks.
