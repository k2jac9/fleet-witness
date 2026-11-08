# Stratum Witness Initial Slice Implementation Plan

> **For agentic workers:** Use superpowers:subagent-driven-development. Steps use checkbox syntax for tracking.

**Goal:** Deliver a runnable, tested local evidence-and-authorization demo and an ADR-governed development fleet starter.

**Architecture:** One Python application controls SQLite effects and exports a static replay. Independent evaluation separates decision quality from execution authorization. Development task worktrees are separate from the evaluated simulated fleet.

**Tech Stack:** Python 3.11+ standard library, SQLite, HTML/CSS/JavaScript, git.

**Spec:** `docs/architecture.md`; accepted ADRs in `docs/adr/`.

## Global Constraints

- Product name: Stratum Witness. Repository: k2jac9/stratum-witness. Solo human owner: Alejandro Castellanos.
- Python 3.11+ standard library only at runtime and for the baseline tests; browser assets use no CDN, telemetry, or build step.
- Default model backend is `scripted-demo`; default external spend is zero.
- Supervisor proposals never directly create effects. Missing policy denies execution.
- A release and its audit event commit atomically; each run/artifact can be released at most once within an isolated trial (ADR-0007).
- Recheck current authorization inside the effect transaction; retain decision-time authorization separately.
- Verify receipt integrity and exact issuer, claim, artifact, scope, and run applicability.
- Reusable attestations are not authorization tokens. Duplicate effects are prevented by database uniqueness and idempotent execution semantics.
- Paired evidence presentations contain the same facts and reuse the same underlying worker/reviewer trajectory.
- Raw versus explicit presentation outcomes from a scripted supervisor are illustrative, not evidence that one prompt improves a model.
- Render replay strings as text. Viewer serving is read-only and loopback-only by default.
- Development workers do not receive authority to spend, merge, publish, change accepted ADRs, or grant access.

## Review Focus

- Revocation after a correct decision must deny the effect without retroactively changing the decision score (Task 1).
- Concurrent duplicate attempts and an audit write failure must not create an extra or unaudited release (Task 1).
- Malformed/cross-context evidence and supervisor input leakage must fail closed (Task 1).
- Unknown replay versions, malicious text, absent fields, and empty data must produce safe readable viewer states (Task 2).
- Cyclic manifests, overlapping ownership, unsafe paths, and preexisting worktrees must not silently launch or overwrite work (Task 3).

### Task 1: Trusted runtime, scripted experiment, and CLI

**Files:** `stratum_witness/__init__.py`, `__main__.py`, `controller.py`, `evidence.py`, `experiment.py`, `evaluation.py`, `export.py`, `server.py`; `tests/test_controller.py`, `tests/test_experiment.py`, `tests/test_cli.py`, `tests/test_server.py`; `pyproject.toml` optional metadata without runtime deps.

**Interfaces:** Produce `stratum_witness.experiment.run_demo(output_dir: pathlib.Path, seed: int = 42) -> dict`, which creates `witness.sqlite3`, `replay.json`, and copies `stratum_witness/web/` assets if present. Produce `stratum_witness.server.serve(directory: pathlib.Path, port: int = 8765)` for loopback read-only serving. Other internal signatures are implementer-owned and must be documented in the report. Replay fields are exactly those in the spec; no hidden cross-task API assumptions.

- [ ] Write failing unittest cases for valid release; forged/wrong-artifact/wrong-run/insufficient-scope evidence; missing policy; permission revoked after decision; duplicate/concurrent attempts; atomic rollback when audit insert fails. Use real temporary SQLite databases and independently hand-derived expectations.
- [ ] Verify the expected failures, then implement minimal receipt verification and transactional controller. Use a trusted per-demo HMAC key; never export it. Use distinct decisions, attempts, and releases with database constraints.
- [ ] Write failing tests for paired facts, 2 x 2 worker-reviewer coverage, separate evaluation labels, and repeatable scenario identities/outcomes. Implement a clearly labeled deterministic supervisor with raw/scoped presentation policies; no empirical claim.
- [ ] Include the four matrix trajectories and additional forged receipt, wrong artifact, wrong run, missing policy, revocation, and duplicate execution scenarios. Emit both presentations per trajectory, using explicit pair IDs and identical underlying facts. Legitimate approvals must execute; invalid approvals must remain visible even when blocked.
- [ ] Implement the CLI contract from the spec. Existing database output must not be overwritten. Serve only `index.html`, `styles.css`, `app.js`, and `replay.json`; deny traversal, unlisted files, directory listings, and writes. Include useful content types and a restrictive CSP. Server tests use temporary fixture assets until Task 2 arrives.
- [ ] Run `python -m unittest discover -s tests -v`, run a demo into a fresh temporary directory, inspect counts and absence of key leakage, commit owned files, and write a report with RED/GREEN evidence.

### Task 2: Evidence replay dashboard

**Files:** `stratum_witness/web/index.html`, `styles.css`, `app.js`; `tests/viewer.test.mjs` if a meaningful pure-function boundary is exposed. Do not alter runtime modules without reporting an integration need.

**Interfaces:** Consume `replay.json` version 1.0 from Task 1; the viewer is copied into demo output by the runtime. UI data comes exclusively from replay JSON; no invented counts or model claims.

- [ ] Build a polished, responsive local dashboard with a dark navy/teal evidence-console visual language, a visible Scripted demo label, compact outcome metrics, searchable/filterable scenario list, raw/scoped selection, agent-role labels, receipt details, and distinct decision/effect outcomes.
- [ ] Include event stepping (previous/next/reset and optional playback) and a clear selected-event detail. Explain why a genuine build receipt cannot authorize a release. Provide an accessible import control for another replay JSON, with size and schema validation and visible error states.
- [ ] Render every untrusted string with textContent or equivalent safe text nodes. No external assets, dynamic HTML from data, inline script handlers, telemetry, or global map claims. Keep keyboard labels and contrast usable. Unknown schema/empty/malformed input must not break the interface silently.
- [ ] Use Node's built-in test runner only for nontrivial data validation/selection utilities if present, with failing behavioral tests first. Verify the real generated replay in a browser at desktop and narrow viewport; inspect console errors and exercise scenario selection/event stepping. Record actual evidence, not invented screenshots.
- [ ] Commit owned files and write the report with exact checks and limitations.

### Task 3: ADR-governed development fleet starter and project delivery

**Files:** `scripts/fleet.py`, `fleet/tasks.json`, `fleet/README.md`, `tests/test_fleet.py`, `README.md`, `LICENSE`, `docs/ROADMAP.md`, `.github/workflows/ci.yml`, `.github/pull_request_template.md`. Consume accepted ADRs; do not revise them silently.

**Interfaces:** CLI `python scripts/fleet.py validate`, `plan`, and `prepare TASK_ID`. `fleet/tasks.json` has `version:1`, `owner:"k2jac9"`, `default_budget_usd:0`, and a tasks array. Each task has id, title, role, status (`todo` or `done`), depends_on, owned_paths, adrs, acceptance (argv arrays), and brief. The tool computes readiness from dependencies and status; manual status is a planning aid, never proof of verification.

- [ ] Write failing tests against temporary real git repositories for duplicate IDs, unknown dependencies, cycles, unsafe/absolute/traversal paths, overlap among ready tasks, invalid ADR references, blocked task preparation, and existing branch/worktree refusal.
- [ ] Implement manifest validation and an ordered readiness plan without network calls. `prepare` must require a clean tracked worktree, create `.worktrees/<id>` and branch `fleet/<id>`, and place a generated task brief in the ignored `.fleet/` directory within that worktree. Use argv subprocess calls, no shell interpolation. Do not execute acceptance commands or model calls automatically. Verify the intended task and root are not redirected through a symlink.
- [ ] Provide a small, useful next-work DAG: live-model adapter proposal, expanded scenarios, research report, and independent review, with nonoverlapping ready-task paths and dependencies. Reference the accepted ADRs in every task. Default spend stays zero; provider-specific runner and isolation are explicit future decisions.
- [ ] Write README with implemented quickstart, demo interpretation, architecture, ADR index, solo authorship/AI disclosure, and current limitations. Add an MIT license for original code, a practical roadmap, a PR report template, and a CI workflow running Python unittest (and Node test only if Task 2 adds it). Follow current official action references; no secrets or deployment permissions.
- [ ] Run the full test suite, fleet validate/plan, a worktree preparation smoke test in a disposable clone, and demo quickstart. Commit owned files and write report.

## Delivery

After scoped reviews and one whole-branch review, run all documented verification commands, inspect the generated viewer, commit any reviewed fixes, and publish the initial implementation to the new repository. Do not deploy a cloud service, spend credits, invite collaborators, or submit the hackathon entry as part of this build.
