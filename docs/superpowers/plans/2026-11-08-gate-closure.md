# Publication and gate closure

Authority: owner request on 2026-11-08 to push all current work and unblock remaining gates. Continue accepted ADR-0010/0011 and the existing live-gateway design; do not waive factual acceptance gates. Implementation is native in this isolated worktree, followed by independent review.

## Scope

Preserve and publish all four existing topic branches. Reproduce the current 142 Python and five viewer tests. Refresh exact runtime selections from authoritative upstream sources, implement and execute stable/preview/previous and promised-consumer CI, and retain baseline identities. Reconcile provider prerequisites using official documentation and available read-only account evidence. Implement only the accepted provider boundary; live calls require all ADR-0010 pre-calibration evidence. Reconcile the research/task handoff and publish a reviewed integration candidate. Preserve historical records and rollback assets. No expansion to public attack observation, no credential publication, no forced history changes, and no deletion of retained resources.

## Tasks

1. Publication: inspect every local branch, scan unpublished tracked objects for secret patterns, run full offline suites, push named refs atomically, verify remote SHAs. Artifact root: `/home/neo/Projects/fleet-witness-artifacts/gate-closure-20261108T192726Z/`.
2. Runtime CI: own `.github/workflows/ci.yml`, `ci/runtime-matrix.json`, `scripts/ci_runtime.py`, `tests/test_ci_runtime.py`, `docs/RUNTIME_ADOPTION.md`, and the narrow `flake.nix` worker-source allowlist correction. Record authoritative release/artifact identities, all required lanes and freshness. Security behavior uses failing tests first. Execute real hosted checks and retain actual results. No global runtime switch or replacement of accepted cloud image.
3. Provider gate reconciliation: own `docs/GATES.md` and any separate provider implementation/test paths explicitly added to this plan before edits. Verify account/rates/usage/retention/TLS facts from official sources and record remaining missing facts. Do not fabricate verified flags, substitute public prices for account prices, or label offline fixtures as production. A missing provider fact does not prevent independent CI and publication work.
4. Research/handoff: own `docs/research-report.md`, `docs/ROADMAP.md`, `docs/CONTROLLED_PILOT.md`, `README.md`, `fleet/tasks.json`, and a new section in `docs/BUILD_STATUS.md`. Make current status and scripted study limitations unambiguous; retain historical sections verbatim. Scheduling metadata requires source-bound completion evidence and does not grant acceptance.
5. Review and publish: run full Python/viewer/fleet checks, review exact diff independently, address material findings with behavioral regression checks, retain the independent report in `docs/reviews/initial-slice.md`, push final branch and publish a concrete PR. Integrate main only after review and required CI. Verify remote identities and report external facts still missing.

## Review focus

- Version policy must distinguish upcoming prereleases, previous supported release line, older promised consumers, and exact retained rollback.
- CI records must bind actual executable/source/artifact identities, and unavailable runtimes must fail visibly.
- Provider documentation/record edits must not create authority or silently relax accepted gates.
- Tracked publication must exclude credentials, private raw receipts, TLS session material and retained browser profiles.
- Scripted trial counts must not be presented as independent model observations.

## Progress

- Baseline: 142 Python and five viewer tests passed at `63431b112c9150e178a58ee31833ea6111e6a5d4`.
- Secret-pattern scan: 63 unpublished tracked blobs checked, no potential hits; bounded heuristic only.

- Publication: all four original topic refs pushed atomically and verified; each original hosted check passed.
- Runtime: seven new behavioral tests, observed red then green; 149 Python and five viewer tests passed. Hosted run 42515494887 exercised all 11 exact runtime lanes; actual identities and passing log endings retained and independently checked.
- Nix: first build failed with five missing-manifest errors; adding `ci` to the worker allowlist produced a successful immutable offline build at d90857e with 149 Python and five viewer tests.
- Provider: public documents refreshed; account billing/reasoning bounds and substantive data-handling terms are unresolved factual prerequisites. No paid activation or new deployment performed.
- Handoff: campaign totals reverified, research draft delivered, task scheduling reconciled; historical evidence and rollback remain intact.
- Independent review: one Important finding, masked pipeline failures, fixed in a405921 with a real verifier failure probe (exit 0 before, 1 after). No other material finding. Original verdict and resolution are retained separately; final-source checks and integration receipt belong to the PR.
