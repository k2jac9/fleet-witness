# Controlled paired pilot implementation plan

> **For agentic workers:** Use superpowers:executing-plans for native implementation and an independent whole-branch review. The owner already delegated execution and green integration; preserve that method and authority.

**Goal:** Run and reconcile a bounded exploratory paired supervisor cohort after a fresh accepted calibration.

**Architecture:** Reuse the controlled provider, canonical spend ledger and trusted Controller. Generate sealed paired fixtures, persist all scheduled calls before dispatch, and export committed outcomes in a distinct private live-pilot schema.

**Tech Stack:** Python standard library, pinned Python 3.15.2, SQLite; existing Node viewer compatibility checks.

**Spec:** `docs/superpowers/specs/2026-11-09-paired-pilot-design.md`.

## Global constraints

- One model, eight families, ten pairs per family, 160 calls/80 pairs; exploratory only.
- One in-flight call, no retry, at most 256 output tokens, 4096 input bytes, 30 seconds, $15 pilot/$50 provider, at most two hours.
- Canonical ledger and original credential file; no workers/listeners/cloud changes.
- Keep original failed calibration, accounting reconciliation, accepted ADRs and runtime rollback unchanged.
- Literal owned paths: `fleet_witness/{pilot_design,pilot_store,controlled_pilot}.py`, `fleet_witness/swarm/{authorization,openrouter_controlled,providers}.py`, `fleet_witness/controller.py`, `tests/{test_pilot_design,test_controlled_pilot,test_openrouter_controlled,test_controller}.py`, `docs/{CONTROLLED_PILOT,BUILD_STATUS}.md`, this plan and its spec. Artifacts under `/home/neo/Projects/fleet-witness-artifacts/paired-pilot-20261109/`.

## Review focus

- Oracle/issuer/scenario labels must never enter model-visible data; verify opaque IDs and identical paired facts.
- Partial execution must preserve failed/interrupted/unstarted denominators and never enable replayed dispatch.
- Pilot profile must not bypass credential, route, source, calibration, accounting or generic-interface guards.
- Local persistence failures must not erase already committed effects or misclassify them as absent.
- Report counters, pair comparison and escaped HTML must derive from verified stored outcomes, including hostile model strings.

### Task 1: Freeze scenario design and schedule

Create `pilot_design.py` with `design()` (frozen model/settings/families/prompts),
`design_sha256()` and `make_plan(key)` (80 opaque paired trajectories,160 calls).
Write failing `test_pilot_design.py` cases for exact pairing/order counts, all five
wrong-applicability strata, no visible oracle labels/keys, truth vs signed fixture
checks and deterministic schedule ordering independently of random opaque IDs.
Implement and run focused tests; retain RED/GREEN receipts.

### Task 2: Qualified pilot profile

Extend only the controlled OpenRouter path with `controlled-openrouter-pilot-v1`,
purpose `exploratory` and exact study design/calibration evidence hashes.
Require accepted calibration and complete schedule cost admission before keys.
Write RED behavior cases for accepted qualified pilot calls and refusal of absent
calibration, wrong counts/limits/design, generic completion, changed authorization,
unsupported extensions and an unaffordable full schedule. Existing calibration
tests must remain green. Reuse protected routing/price/TLS and liability logic.

### Task 3: Durable trusted runner and export

Create `pilot_store.py` for private SQLite schedule/results and derived
`live-pilot-1.0` export/validation/escaped HTML. Create `controlled_pilot.py` with
`run_pilot(authorization_path, output_dir, live=False)` and an explicit CLI. It
loads exact source-bound authorization, verifies frozen design and unused run,
persists the whole schedule, then processes one call at a time. Persist provider
outcome before Controller operations; derive decision/effect history from the
Controller's tables. Add a narrow Controller actor parameter, default scripted,
to identify live-supervisor events truthfully; reject unrecognized actors.

Write RED tests using real SQLite/controller/ledger and synthetic HTTPS replies:
valid approvals, revocation, duplicate attempts, invalid output, held transport
failure, pre-dispatch refusals, existing output/reused run, controller/audit
failure, export-only crash recovery, schedule denominator and pair consistency,
nullable invalid outcomes, escaped malicious output and real/live labels.
Implement the runner and export; run full Python/viewer suites.

### Task 4: Review and integration

Run the full baseline commands, Git-free launcher if affected, and exact-source
hosted runtime lanes. Independent reviewer checks the entire branch and study
contract. Fix important findings with RED/GREEN evidence. Merge only green
reviewed source under existing owner authority; retain worktrees and artifacts.
Update BUILD_STATUS with actual evidence and explicit unexecuted gates.

### Task 5: Calibration, collection and reconciliation

Refresh original-key allowance, canonical ledger, endpoint prices and applicable
host evidence. A new source-bound calibration on already reviewed corrected
source is permitted before implementing the runner; its failed predecessor is
not retried or reclassified. After a successful response, verify generation and
key charge and bind that acceptance into the pilot record.

Freeze the final design/prompt hashes and private source-bound 160-call operator
record on merged source, within the remaining shared $50 allowance. Run exactly
one cohort. On any failure halt, preserve all scheduled/unstarted outcomes and
do not replace calls. Reconcile every dispatched generation and key delta,
preserving holds where uncertainty remains. Retain inputs, outputs, findings,
costs/timing and provenance. Report exploratory limitations and remaining future
two-model/worker/public-observation scope separately.
