# Bounded Live Gateway Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans for inline execution. An independent reviewer checks the whole diff before any live calibration.

**Goal:** Make one separately authorized, traceable real-model calibration possible without granting worker or model authority.

**Architecture:** A separate trusted-host live gateway builds a closed synthetic model input, reserves an entire one-credit budget in private SQLite, invokes only the fixed provider endpoint using a reviewed transport and TLS trust, and records bounded provenance and usage atomically. Existing offline fake and controller stay separate.

**Tech Stack:** Python 3.11+ standard library, SQLite, reviewed system curl/TLS, unittest; no new baseline runtime dependency.

**Spec:** `docs/superpowers/specs/2026-11-08-live-gateway-design.md` and `docs/adr/0010-trusted-live-model-gateway.md`.

## Global Constraints

No live activation from import, unit tests, CI, fixtures or workers. No retries, redirects, arbitrary URL, proxy, provider tools, memory or stored conversations. Existing GCP VM remains stopped. Never print credentials. The one-credit, one-request calibration is separately labeled and is not the confirmatory study. A held or unresolved request blocks further dispatch.

## Review Focus

- Concurrent callers and repeated IDs cannot spend or dispatch twice.
- Crash, timeout, bad usage, unexpected provider status, audit failure and overrun retain liability and halt; never silently retry or invent a denial.
- Adversarial evidence, duplicate JSON keys, oversized/deep output, tool calls, invalid Unicode and malicious metadata never affect authorization or escape the bounded schema.
- Redirects, proxies, invalid TLS trust, non-private keys, unsafe paths and leaked stderr cannot expose credentials.
- Live observations must not be labeled scripted, contain privileged scenario truth or be claimed as a paired-study result.

## Task 1: Durable live accounting and bounded input

**Files:** Create `fleet_witness/live_gateway.py`; create `tests/test_live_gateway.py`.

**Interfaces:** The current offline `LiveLedger(path, authorization)` fixture exposes `reserve(request_id, facts, presentation)`, `dispatch(request_id)`, `settle(request_id, response)`, `uncertain(request_id, reason)`, and `snapshot()`. Its output is explicitly labeled `offline-calibration-fixture`; it has no network or credential access. A production authorization additionally needs a verified provider account, unique authorization ID, canonical shared ledger and exact source identity. The fixture's arbitrary path must not be used as a production spending gate.

- [x] Write failing tests for fixture authorization validation, atomic reserve/audit, concurrent reservations, repeated IDs, dispatch deadline and recovery with held budget; run and retain the failing output.
- [x] Implement the fixture ledger and validation, preserving its authorization on restart.
- [x] Add failing tests for fixture response usage, errors, output validation, schema/identity limits and atomic settlement; implement and retest.
- [ ] Design and implement the single-use production authorization registry with canonical ledger, account and source binding; verify cross-process, restart and alternate-path refusal before any live transport.

### Offline registry subtask

**Owned paths:** `fleet_witness/calibration_registry.py`,
`tests/test_calibration_registry.py`, this plan and `docs/BUILD_STATUS.md`.
The same primary owner uses the isolated `fleet/controlled-pilot` worktree.
`FixtureRegistry(path)` provides `claim(authorization_id, account_id,
source_commit, ledger_path)`, `consume(authorization_id)` and
`snapshot(authorization_id)`. Claims are immutable and unique in one private
SQLite registry; changing the ledger, account or source cannot reuse a claim.
Consumption and its audit event commit together exactly once across processes.
`BoundFixtureRunner` checks the registry's account, source and canonical ledger
against a `FixtureRunner`, validates the visible input, then consumes the claim
before running that inert fixture. A crash after consumption is fail-closed;
the fixture is not retried automatically. The two SQLite files are not one
transaction, so the sequence deliberately prefers losing an unused fixture
attempt over allowing a second one.
This is a fixture, not the production global gate: a real entry point must pin
one canonical registry and validate the actual account, source and ledger
identities. No component may activate a network request yet.

- [x] Write failing tests for immutable claims, alternate-path refusal,
  concurrent consumption, crash/restart recovery, atomic audit failures and
  private paths; run them and retain the failing result.
- [x] Implement the minimum fixture registry, retest, and independently review
  its cross-process and crash guarantees before reporting it complete.

## Task 2: Trusted transport and calibration orchestration

**Files:** `fleet_witness/live_gateway.py`; `tests/test_live_gateway.py`; optionally an explicit trusted operator command under `scripts/`.

**Interfaces:** `build_provider_request(facts, presentation)` and `parse_provider_response(raw)` are pure offline functions. `FixtureRunner` accepts only `FixtureTransport`, which has no URL, key or network code. A future production adapter must accept one validated model-visible payload and return a bounded untrusted response using the fixed HTTPS endpoint and owner-private key. Live dispatch requires an explicit authorization record and opt-in entry point; no worker interface is introduced.

- [x] Write failing tests for the closed request settings and bounded response parser; implement and retest without actual provider calls.
- [x] Exercise request, accounting and failure recovery with an inert fixture; its results are labeled offline, not live.
- [ ] Write failing tests for fixed endpoint/method, proxy/redirect/retry denial, credential handling, complete-call deadline and transport response caps; implement and retest without actual provider calls.
- [ ] Test that live failures preserve reservations across restart and that a verified real response is labeled live, retained with usage, and cannot execute an effect.
- [ ] Independently review the exact diff and trust/rate evidence; fix review findings using failing tests first.
- [ ] Run full `python3 -m unittest discover -s tests -v`, `node --test tests/viewer.test.mjs`, `python3 scripts/fleet.py validate`, and `git diff --check`; retain actual outputs and commit identities.
- [ ] Complete pre-calibration security, source, provenance, accounting, privacy and operator authorization gates. If any fact remains unknown, keep live dispatch disabled and record it.
- [ ] Only after all gates pass, run at most one calibration request in a new terminal; preserve ledger, provider ID, response, usage, cost comparison, failure state and billing reconciliation. Keep confirmatory work unstarted until calibration reconciles.
