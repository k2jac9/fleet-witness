# Swarm Stabilization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Repair the reviewed swarm spending, evidence and reproduction defects and prepare one tested integration candidate.
**Architecture:** Keep historical evidence immutable; separate a transactional private provider ledger from public detector data. Use explicit one-attempt requests and a real kernel baseline replay. No automatic live qualification.
**Tech Stack:** Python 3.11+ standard library, SQLite, unittest, existing Node viewer tests and report rendering tools.
**Spec:** `docs/superpowers/specs/2026-11-09-swarm-stabilization-design.md`

## Global Constraints

- Preserve existing ADRs, original ZIP and AI reviews; zero paid calls in stabilization.
- One owner per task and isolated worktree; workers do not merge or publish.
- Record failing regressions before security-sensitive fixes and full suites after integration.
- Keep raw prompts/private receipts outside public detector events and shared dashboard assets.
- Budget units are fixed-point USD only after an explicit verified operator record; GCP remains separate.

## Review Focus

- Cross-process requests and restarts must not reset or oversubscribe budgets.
- Unknown, malformed, negative, non-finite or excess usage must retain liabilities and stop dispatch.
- A timeout or persistence failure after dispatch must remain visible even when no logical answer completes.
- ZIP traversal/alias collisions and incomplete/mismatched datasets must fail without overwriting evidence.
- Reconstruction must use the kernel and must never be described as historical cryptographic replay or new model data.

## Task 1: Shared provider accounting and one-attempt transport

**Files:** `fleet_witness/swarm/providers.py`, new `fleet_witness/swarm/ledger.py`, new `fleet_witness/swarm/authorization.py` if needed, `tests/test_swarm.py` provider/ledger sections, new `tests/test_swarm_provider.py`, `tests/test_swarm_ledger.py`.
**Interfaces:** Preserve imports `Ledger`, `BudgetExceeded`, `ProviderError`, `ModelClient`, `FakeClient`. `ModelClient.complete(system,user,meta=None)` returns final text/usage/cost plus `attempts` (bounded records), `provider_attempts`, `held_usd`, and terminal `status`; failures attach `attempts` to the exception. `Ledger.snapshot()` supplies run/provider settled and held totals. Constructor accepts `authorization` mapping; absent/unqualified records fail before key/network access. Tags never select a budget file. Keep `FakeClient` offline-compatible.

- [x] Write and run behavioral failures for shared tags/processes, restart holds, cap changes, invalid/overrun charges, no retry on length/429/stop, extension collisions and authorization-before-I/O.
- [x] Implement fixed-point transactional reservations/audit and fail-closed legacy detection; retain one-attempt receipts and request identity on failures.
- [x] Verify bounded direct transport, protected fields and closed outcomes with synthetic credentials and network doubles only.
- [x] Run focused tests then the canonical full Python suite; retain red/green logs and commit owned paths.

## Task 2: Portable evidence and executable baseline

**Files:** `scripts/baselines.py`, `scripts/independence.py`, `scripts/report_stats.py`, `scripts/reproduce_tables.py`, new `scripts/extract_run_archive.py`, `data/README.md`, `fleet_witness/institution.py`, `fleet_witness/swarm/sweep.py`, `tests/test_institution.py`, new `tests/test_reproduction.py`.
**Interfaces:** Kernel permits `committee_size=quorum=0` only with `require_majority=True`. Baseline reconstruction uses fresh synthetic keys and recorded vote totals, validates regenerated case identities against archived truth, and emits explicit reconstruction provenance. Extraction accepts an archive and fresh destination. Reproduction supports an explicit data/output root and writes strict JSON without mutating raw evidence or historical review files.

- [x] Write failing archive traversal/collision/overwrite and partial-denominator tests; test zero-committee policy/integrity/majority/uniqueness/audit behavior before kernel change.
- [x] Implement portable extractor and actual kernel baseline, dynamic denominators and complete-run validation, all eight regime rows.
- [x] Remove inappropriate pooled confidence intervals; output null for undefined statistics and distinguish paired outcomes from seating draws.
- [x] Run focused/full tests and offline archive reproduction; retain original archive hash and commit owned paths.

## Task 3: Run provenance and current publication

**Files:** `fleet_witness/swarm/runner.py`, `fleet_witness/__main__.py`, `scripts/peer_review.py`, `scripts/reviewer_speedtest.py`, new `tests/test_swarm_provenance.py`, `scripts/make_figures.py`, `docs/report/REPORT.md`, current HTML/PDF/figures/independence output, new report provenance/correction records, `docs/SWARM.md`, `docs/GATES.md`, `docs/BUILD_STATUS.md`, `docs/TESTING.md`.
**Interfaces:** Consume Task 1 attempt records and ledger snapshot; consume Task 2 reconstructed baseline and extraction. Public event attempts contain only safe accounting metadata; raw prompts/responses stay in private operator records. New manifests bind source tree, runtime and model configuration. Paid command entrypoints require the operator record and report pending qualification accurately.

Execution ownership split: parent owns runner/CLI/review-script wiring, new provenance tests and current operational handoff. Independent publication worker owns `scripts/make_figures.py`, new `tests/test_report_figures.py`, `docs/report/REPORT.md`, current HTML/PDF/figures and new correction/provenance documents. It preserves historical `docs/report/reviews/`, `review-data.md` and the data ZIP. Parent alone installs newly reproduced `independence.json` after Task 2 integration. Publication does not depend on new provider behavior.

Integration ruling: parent also owns new `swarm/operator.py`, `swarm/run_records.py`,
`swarm/judge.py` and narrow integration updates to `tests/test_reproduction.py`.
These implement Task 3's authorization/private-receipt boundary for every existing
paid entrypoint and adapt raw-input hashing to the new private receipt directory.
No accepted ADR, old review or original dataset is changed. Paid source must be
clean and committed; review acceptance remains an independently recorded gate.

- [x] Write failing tests for failed-attempt accounting, public prompt separation, private receipt provenance, source/config identity and a real gated-majority regime.
- [x] Wire durable provider outcomes into runner/CLI and review scripts; label logical decisions, attempted requests and held liability separately.
- [x] Fix conventional medians with a behavioral fixture; correct prose/encoding/figure labels and regenerate artifacts from retained data.
- [x] Record current evidence, pending live qualification and historical-data limits without rewriting accepted decisions or old receipts.
- [x] Run full suites, replay reproduction and artifact checks; commit focused changes.

## Task 4: Independent review and integration

**Files:** Evidence packet and current build-status handoff only, plus narrowly justified tested fixes.
**Interfaces:** Exact final commits, full logs and archive/artifact hashes from Tasks 1–3.

- [x] Independent reviewer checks the full candidate and five Review Focus items.
- [x] Reproduce and fix material findings with failing tests; preserve all receipts.
- [ ] Run complete checks on final source, push the stabilization branch and verify hosted CI before integration.
- [ ] Integrate only the reviewed exact candidate; report source, results and any remaining paid-canary gates.

Execution ruling: prior owner approval covers this plan; no repeated design or execution-method approval is requested. Parent owns integration. Independent components may proceed concurrently under the dispatching-parallel-agents skill, with separate owned paths/worktrees. Retained evidence is never deleted by skill workspace cleanup.
