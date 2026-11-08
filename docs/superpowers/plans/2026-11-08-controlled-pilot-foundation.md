# Controlled pilot foundation implementation plan

> **For agentic workers:** Use inline execution for this bounded foundation,
> with a fresh independent review before owner integration. Keep live activation
> outside this task.

**Goal:** Build and verify an offline provider boundary and persistent shared
budget accounting suitable for the controlled pilot selected by the owner.

**Architecture:** Add an optional standard-library module beside the existing
controller. A trusted envelope stays outside provider-visible facts. An inert
fake provider exercises durable reservation, dispatch, settlement, and ambiguous
failure states. The module cannot create a release or make a network request.

**Tech stack:** Python 3.11+ standard library, SQLite, unittest. Actual development
runtime is Python 3.15.0; the existing Python/viewer suites remain required.

**Spec:** `docs/proposals/live-model-adapter.md`, approach selected by the owner
on 2026-11-08: both directions, beginning with the controlled pilot. This task
implements its offline foundation only; the accepted ADRs remain unchanged.

## Owned paths

- `fleet_witness/gateway.py`: provider-visible validation, fake adapter, and ledger.
- `tests/test_gateway.py`: behavioral security/accounting tests.
- `docs/CONTROLLED_PILOT.md`: actual interfaces, evidence, and live activation gaps.
- This plan and `docs/BUILD_STATUS.md`: source-bound continuation evidence.

No provider credentials, real calls, host changes, accepted ADR revisions,
external publication, task-status changes, or main-branch integration.

## Review focus

- Wrong or nested extra input fields must fail before dispatch.
- An unresolved dispatch must retain its entire reservation after restart.
- Concurrent reservations and duplicate request IDs must not overspend or retry.
- Invalid output and provider failures must not become correct model denials.
- A recommendation alone must have no release authority.

## Task 1: Offline gateway and durable budget accounting

- [x] Write `tests/test_gateway.py` before implementation. Cover exact input
  allowlisting and metadata separation; strict output parsing; integer budget
  limits; concurrent reservations; duplicate IDs; settlement; missing/excess
  usage; timeout and crash; restart preservation; private ledger permissions;
  and atomic reservation/audit rollback using a real SQLite trigger.
- [x] Run `python -m unittest discover -s tests -p test_gateway.py -v` and retain
  the expected missing-module failure before any security-sensitive code.
- [x] Implement `BudgetLedger`, `ProviderReply`, `FakeProvider`, `Gateway`, and
  `provider_input` in the single owned module. One ledger transaction owns every
  state/audit change. Provider execution occurs outside its transaction.
  Use nonnegative integer verified units, no implicit retries, and a shared
  single-dispatch limit. Hold ambiguous reservations and refuse more dispatch.
- [x] Run the focused suite and the complete Python/viewer suites. Correct
  actual failures without weakening accounting or controller authority.

## Task 2: Reproducible handoff and independent review

- [x] Document interfaces, exact commits and test results, fake mode, the
  verified image build, failed worker-boot diagnostics, current account-access
  blocker, and all unexecuted live/security/runtime gates.
- [x] Run fleet validation, link checks, `git diff --check`, and relevant full
  offline smoke; retain logs under the existing continuation artifact packet.
- [x] Commit the candidate and obtain independent review of the whole branch.
  Address material findings and retain the reviewed source identity.

## Completion boundary

Passing this task establishes offline module behavior, not a real provider
adapter, calibrated spend rates, accepted live replay schema, completed pilot,
deployed workers, or production security. The $100 GCP envelope and owner-reported
$1,500 Adaption balance remain separate. Live activation needs verified units,
reachable authorized accounts, the approved successor ADR, and applicable host
acceptance. Public attack observation follows the controlled pilot as a separately
reviewed scope.

## Observed completion

Implementation review at `bf06d99` has no remaining findings after the reproduced
response-status correction. Seventeen focused tests, seventy-two full Python
tests, five viewer tests, full offline smoke, fleet validation and whitespace
checks pass. Python 3.11.17/3.14.8 and Node 24.22.1 installed consumer checks also
pass; this is not the complete fresh upstream CI matrix. The documented fake
example runs with one synthetic unit spent and no held reservation. The GCE
image builds; local worker startup fails before confinement probes. GCP account,
project and credit verification, provider/live activation, and owner integration
remain outside this completion boundary. Full evidence is retained in the
sibling continuation artifact packet.
