# Controlled supervisor calibration integration

Task: `controlled-live-calibration-20261109`. Owner: primary integrator. Base:
`b50569e4ae56c6958f5b7f2ceebc9f70e310f246`. Worktree:
`.worktrees/live-calibration-20261109`, branch
`feat/controlled-live-calibration-20261109`.

Specification: accepted ADR-0010 and the existing live-gateway design. The owner
approved continued implementation and one calibration request, at most one
verified Adaption credit, 30 seconds, no retry, followed by actual billing
reconciliation. GCP's $100 ceiling remains separate. No authorization or
qualification assertion may be fabricated to clear a missing fact.

Owned paths: `fleet_witness/swarm/providers.py`,
`fleet_witness/controlled_calibration.py`, `tests/test_controlled_calibration.py`,
`docs/CONTROLLED_PILOT.md`, `docs/GATES.md`, `docs/BUILD_STATUS.md`, this plan,
and `docs/reviews/controlled-calibration-review.md`. Retained evidence:
`/home/neo/Projects/fleet-witness-artifacts/live-calibration-20261109/`.
Public-provider research is independently delegated, read-only, with exclusive
write ownership of that packet's `provider-public/` directory. No accepted ADR,
historical receipt, controller, or existing fake gateway will be rewritten.

## Task 1: Strict supervisor interface

Write behavioral tests first for the exact visible fact allowlist, equal paired
facts, closed JSON proposals, provider model/response identities, output item
types, failure accounting, no retries, and no controller authority. Implement
`ModelClient.recommend(facts, presentation)` using the existing canonical ledger
and transport. Commit the normalized proposal and contract with the accounting
receipt in one transaction. Invalid proposals must remain billed invalid
outcomes, never correct denials. Preserve the historical swarm parser behavior.

Expected: focused tests fail for the missing interface, then pass; existing
provider security tests continue to pass. Inputs, raw responses, hashes, usage,
status and normalized recommendations remain recoverable from the private ledger.

## Task 2: Bounded calibration entrypoint

Write behavioral tests before a trusted operator entrypoint for one fixed
synthetic supervisor request. Require deliberate live mode, clean/source-bound
authorization, Adaption/direct model, canonical ledger, one request, at most $1
only after the asserted credit conversion is verified, at most 256 output tokens
and 30 seconds. Refuse before credential access on invalid bounds. Retain a
private initial manifest before dispatch and a separate terminal result; never
overwrite prior evidence or retry. Return data only; this transport/schema
calibration does not execute controller effects or count toward the paired study.

Expected: offline mocked-transport tests prove these bounds, persistence and
failure behavior. CLI help is inert; no test reads a real key or calls a provider.

## Task 3: Qualification and independent review

Inspect only relevant credential metadata and accounting locations, recover
official provider terms/rates/API documentation with hashes, and inventory
remaining host/account requirements. Do not read the real key through an
unqualified TLS transport. Run the full Python and viewer suites, then obtain
an independent whole-diff review and fix material findings with failing tests.
Record exact source, commands, outcomes, limitations and unexecuted checks.
Run paid calibration only if every ADR-0010 gate actually closes; preserve a
specific blocked receipt otherwise. Do not create cloud resources for a host
calibration, release holds, or infer a current balance from historical runs.

## Integration rulings

- Reuse existing approved design and user authorization; no repeat permission
  menu is needed. Manual Git worktree creation uses the required Projects path;
  the native creation tool cannot select that destination.
- Keep the synthetic fixture ledgers inert. New controlled requests use the
  hardened shared provider ledger; a separate output manifest is provenance,
  not a second accounting authority.
- Provider qualification assertions remain operator attestations, not proof.
  No real authorization record is issued while billing/handling/host facts are
  unresolved. Test fixtures must state their synthetic nature.
- Preserve the plan, task ledger and failed evidence after review; owner
  preservation policy overrides skill scratch cleanup.
- Tasks 1 and 2 share `recommend` and durable attempt receipt fields; Task 2
  consumes them without parsing the response again or settling another ledger.
