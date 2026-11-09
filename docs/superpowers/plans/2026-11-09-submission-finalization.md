# Submission finalization implementation plan

> **For agentic workers:** Use superpowers:executing-plans. One fresh independent whole-branch review follows implementation.

**Goal:** Make the submission easy to verify and demonstrate, then prepare its final event entry.

**Architecture:** An offline standard-library verifier checks the explicit public
package and derived data. Local browser capture produces labeled media without
adding authority to the application. Existing CI and publication tooling integrate
these additions.

**Tech Stack:** Python 3.11+ standard library, existing Node runtime matrix, installed
Chromium and FFmpeg for authoring only.

**Spec:** `docs/superpowers/specs/2026-11-09-submission-finalization-design.md`.

## Global constraints

- Owner/integrator: Alejandro Castellanos. Task: `submission-finalization-20261109`.
- One isolated worktree; retained artifacts in the admitted sibling task packet.
- Preserve title/authors/abstract, numerical findings, datasets, accepted ADRs,
  old REPORT artifacts and current PDF bytes. No paid calls or cloud mutation.
- Private contact/account/form records never enter Git, media or the ZIP.
- Exact source/runtime evidence, full Python suite, independent review and green
  hosted CI precede integration. Existing owner green-merge authority persists.

## Review focus

1. Unsafe ZIP members or filesystem links must be rejected without extraction.
2. Internally consistent but stale/tampered package data must not silently pass
   the repository comparison or frozen-cohort checks.
3. Duplicate pair presentations, wrong totals and misleading summary labels must
   fail even if checksums are recomputed.
4. Media must show actual application output, correctly labeled, with no private
   desktop/browser information or implication of a new live-model run.
5. Submission readiness and actual event confirmation must remain distinct.

### Task 1: Offline verifier and CI

Owned: `scripts/verify_submission.py`, `scripts/build_latest_submission.py`,
`tests/test_submission_verifier.py`, `.github/workflows/ci.yml`.

Interfaces: `verify_submission(package: Path, repository: Path | None = None) -> dict`
checks ZIP bytes; `verify_directory(directory: Path) -> dict` checks an extracted
allowlist. CLI defaults to the repo ZIP with source comparison; the standalone
packaged script defaults to its own directory. Explicit `--package` verifies a
ZIP; explicit `--directory` verifies extracted files. JSON output and nonzero
exit on invalid input. No writes or network.

- [x] Write behavioral tests using actual ZIP bytes and independent expected
  counts: 160 trials, 80 pairs, raw 18 invalid approvals / zero invalid denials,
  explicit zero invalid approvals / 40 invalid denials, 30 effects, 68 attempts,
  28 authorization denials, ten duplicate no-ops, $0.2605526 provider charge.
- [x] Observe failure before implementation; add bounded readers, exact checksum
  coverage, provenance/metadata consistency and cohort recomputation.
- [x] Verify corrupt/missing/stale/duplicate/traversal/symlink/oversized input and
  unchanged output trees. Add the verifier to the Python CI command sequence.

### Task 2: Public media and package

Owned: `fleet_witness/web/index.html`, `docs/assets/fleet-witness-cover.png`,
`docs/assets/fleet-witness-viewer.png`, `docs/submission/latest/`,
`docs/submission/latest-submission.zip`, `docs/report/latest.provenance.json`,
`docs/submission/media/`, `README.md`, `docs/SUBMISSION.md`, `docs/AI_ASSISTANCE.md`.

- [x] Correct the stale footer, generate the seed-42 demo and capture its real UI.
- [x] Render and inspect the PNGs; record and review a captioned 180-second MP4,
  including real UI interactions and separately labeled recorded study results.
- [x] Record media source/digests/tools, update metadata and copy-ready links,
  refresh publication provenance and rebuild the explicit package.
- [x] Run the new verifier on the repo ZIP and extracted package, including its
  standalone entrypoint. Inspect duration, frames, captions, file sizes and hashes.

### Task 3: Acceptance, review and delivery

Owned: `docs/BUILD_STATUS.md`, this plan and its spec; private artifact packet.

- [x] Full Python/Node tests, planner, demo, links/whitespace and preservation checks.
- [x] One independent whole-branch review; owner resolves findings and runs the
  exact final-source runtime matrix. Merge green work and synchronize clean main.
- [ ] Prepare the form using user-provided data. Required missing information
  stays pending; no invented contact details or submission success. Preserve the
  actual confirmation if the form can be submitted.

## Execution ledger and rulings

- Native worktree tool has no path parameter; Git creates the worktree under
  Projects as required by owner policy. Existing unrelated worktrees stay intact.
- The brainstorming/design menu is unnecessary: the owner selected all three
  concrete recommendations and previously requested autonomous execution.
- Preserve the sibling artifact packet instead of deleting skill scratch.
- Initial preflight used an unsupported flag and failed before heavy work;
  corrected --budget-gib/--output-dir admission passed. Both records are retained.

- Task 1 complete locally: eight red-to-green mutation tests; repository and
  standalone package checks pass. The full suite now has 317 tests.
- Task 2 complete: two inspected PNGs, 180-second H.264 video (2,506,489 bytes),
  captions, public hashes and explicit 17-member package. PDF and data unchanged.
- Task 3 local checks complete: 317 Python / five Node tests; planner, demo,
  video decode and local links pass. Independent review and hosted CI follow.
- Ruling: keep the existing admitted sibling packet as the execution ledger and
  retain it after integration, instead of deleting skill scratch — owner policy
  requires failed receipts and rollback evidence; this consumes bounded disk space.
- Ruling: use an explicitly labeled edited sequence of captured browser states,
  held for reading, with captions and no audio — it fulfills the walkthrough while
  avoiding a real-time-execution claim; it is less fluid than a continuous recording.
- No form submission: the owner is unsure of contact emails and prior submission
  status. The private form record preserves that uncertainty without inventing data.
