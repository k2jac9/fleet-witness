# PR 16 Review Fixes Implementation Plan

> **For agentic workers:** Use test-first implementation and independent review in isolated worktrees. The owner has authorized execution of these review fixes.

**Goal:** Correct the six groups of findings in PR 16 and update its existing branch after verification.

**Architecture:** Use the existing authorized provider client and shared durable ledger, preserve historical evidence, and make fresh derived outputs explicit about coverage and provenance.

**Tech stack:** Python 3.11+ standard library, existing SQLite ledger, LaTeX report, Node viewer tests.

**Spec:** `docs/superpowers/specs/2026-11-11-pr16-review-fixes-design.md`

## Global constraints

- No paid calls, credential inspection, new authorization records, deployments or external messages.
- Do not expand accepted ADR limits or rewrite historical run/review outputs.
- One owner and isolated worktree per task. Root integrates and updates the PR.
- Retain the known pre-existing TLS test failure as evidence; do not suppress it.

## Review focus

1. Concurrent clients and process restarts must preserve the shared budget.
2. Timeouts and missing charges must retain liabilities and attempted-call records.
3. Truncated or invalid required review output must remain incomplete.
4. Missing tools and malformed/unsupported scanner inputs must not become negatives.
5. Changed input counts must change generated exclusion rates and evidence claims.

## Task A: research request and audit boundaries

Owner: budget worker. Paths: `scripts/judgement_experiment.py`,
`scripts/peer_review_visual.py`, `scripts/label_check.py`,
`scripts/run_experiment2.ps1`, a small shared research-client helper if needed,
and `tests/test_research_requests.py` / `tests/test_peer_review.py`.

Independent review extended this ownership to minimal cancellation changes in
`fleet_witness/swarm/providers.py`, `ledger.py` and `runner.py`, with exact
request-state recovery and an unchanged pre-dispatch pilot expectation.

- [x] Reproduce pre-dispatch budget, failed-attempt and incomplete-review bugs with offline behavioral tests.
- [x] Replace the direct unqualified HTTP clients with existing `ModelClient` / `Ledger` and explicit operator authorization. Preserve existing gateway bounds and one-attempt behavior.
- [x] Serialize requests consistently with the accepted gateway; ensure orchestration shares the same ledger/cap and cannot create a second spend allowance.
- [x] Validate required review/audit JSON and terminal completion; preserve receipts on every exit path.
- [x] Run targeted tests and commit the owned paths. Report exact interface changes and remaining qualification requirements.

## Task B: scanner, summaries and judgement regression coverage

Owner: analysis worker. Paths: `scripts/bandit_baseline.py`,
`scripts/judgement_summary.py`, `tests/test_judgement_reporting.py`,
`tests/test_judgement_cases.py`.

- [x] Write and run failing tests for absent Bandit, malformed scanner output, partial coverage and stale exclusion rates.
- [x] Validate execution and structured results, retaining a separate unsupported/error outcome and tool version.
- [x] Calculate exclusion counts from `f00.honest.per_case` with explicit contested-case metadata.
- [x] Add behavioral checks for case composition, receipt validation and sealed prompt inputs without changing kernel behavior.
- [x] Run targeted tests and commit owned paths. Root regenerates summaries after integration.

## Task C: report and evidence corrections

Owner: report worker. Paths: `docs/report/latex/report.tex`, `README.md`,
`docs/submission/FINAL.md`, new dated correction/evidence notes, and an optional
offline aggregate verifier with its behavioral tests. Historical JSON and
pre-registration/review records remain untouched.

- [x] Scope archive reproduction to Experiment 1 and explicitly describe Experiment 2's aggregate-only public evidence.
- [x] Correct scanner coverage, erroneous absolute reviewer claims, missing-answer claims and reference-run attribution.
- [x] Label historical incomplete numeric audits and current retrospective corrections accurately.
- [x] Verify the headline arithmetic against committed aggregates and document an offline verification command.
- [x] Commit owned source changes. Root rebuilds and visually checks the PDF.

## Task D: integration and release verification

Owner: root. Paths: plan/spec, `docs/BUILD_STATUS.md`, regenerated PDF/summary,
and integration fixes needed by independent review.

- [x] Integrate worker commits and independently review the complete diff.
- [x] Run full Python suite, Node tests, scanner/summary/aggregate checks and whitespace checks.
- [x] Rebuild and inspect report PDF, retaining an honest post-submission revision note.
- [x] Test compatibility with current main and verify the pre-existing pilot package.
- [x] Fix review findings, record exact evidence and remaining limitations.
Publication receipt: the final branch head and hosted checks are recorded on [PR 16](https://github.com/k2jac9/fleet-witness/pull/16). Publication advances only the existing PR branch; merging the PR remains outside this task.

## Final offline outcome

The integrated implementation passed 378 of 379 local Python tests; the sole
remaining failure is the inherited TLS root-count assertion documented in
`docs/BUILD_STATUS.md`. Independent review found no remaining blocking findings
after 160 targeted tests. Five Node tests, the existing pilot package verifier,
real Bandit validation, the sequential PowerShell harness and PDF inspection
passed. Historical experiment/review records and accepted ADRs are preserved.
