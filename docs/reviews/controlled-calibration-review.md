# Independent whole-branch review

Task: `controlled-live-calibration-20261109`.
Reviewer: independent read-only review agent.
Checkout: `/home/neo/Projects/fleet-witness/.worktrees/live-calibration-20261109`.
Base: `b50569e4ae56c6958f5b7f2ceebc9f70e310f246`.
Reviewed head: `ebedd474a1c590d9ea3bf43c72d492274fa87888`.
Final source check: HEAD unchanged; `git status --porcelain` empty.

Reviewed the complete seven-file branch diff, owner policies, repository AGENTS, architecture and accepted ADRs, live-gateway design, controlled-calibration plan/progress ledger, provider authorization/operator/ledger/transport implementation, input/proposal validators, current tests, and relevant retained official response-schema documentation. No checkout/index/HEAD mutations, real keys, account access, network calls, or subagents were used. Only synthetic generated scratch data and this review packet were written.

## Strengths

- Reuses the existing canonical durable accounting authority rather than creating a second spend ledger. A one-request calibration reserves its entire authorized envelope, preserves holds and prevents same-authorization retries.
- Supervisor requests pass the six-field and nested evidence allowlists. Paired facts stay identical; input construction excludes issuer keys and privileged truth. The runner has no controller dependency or effect authority.
- Closed proposal validation produces explicit invalid outcomes; proposal and contract are stored in the accounting transaction. A failed settlement cannot return an approval proposal.
- The runner requires deliberate live selection, source-bound authorization and bounded request/token/deadline limits. New exclusive private artifacts preserve prior output and separate preparation from terminal results.
- Documentation clearly distinguishes this code candidate and mocked tests from live qualification, account reconciliation and confirmatory study acceptance. Open TLS/runtime/credential/account/handling gates are accurately retained.

## Issues

### Critical (Must Fix)

None found.

### Important (Should Fix)

1. **Contradictory provider envelopes can be promoted to successful proposals and release the hold.**
   - Location: `fleet_witness/swarm/providers.py:280-302`, especially the new `_supervisor_envelope` at lines 340-360.
   - The strict path validates selected identity/output fields but does not reject `status="completed"` combined with non-null `incomplete_details`. It also ignores a supplied top-level `output_text` that contradicts the single message's text. The retained provider schema describes incomplete_details as why the response is incomplete, and output_text as the joined output text. These are conflicting statements about the same result.
   - Reproduction: `probes.json` cases `completed_with_incomplete_details` and `conflicting_output_text` both returned `status="succeeded"`, an `approve` proposal, `held_usd=0`, and `halted=false`. The latter carried a different `deny` proposal in top-level output_text. The `in_progress` control correctly remained unresolved with the full $1 held.
   - Impact: an ambiguous provider response becomes a successful controlled-supervisor outcome and an ordinary settled request. This violates ADR-0010's unresolved treatment of ambiguous provider responses and makes the calibration's strict-response claim unreliable. No controller effect occurs, but the accounting/outcome boundary is wrong.
   - Fix: validate consistency of the response's known status/content representations before settlement. Require absent/null incomplete_details on completed responses; if output_text is present, require the documented string form and exact agreement with the message text (or reject that representation by explicit contract). Keep ambiguous envelopes unresolved with no proposal and the full reservation. Add failing behavioral tests for both cases; preserve legacy `complete` behavior unless separately scoped.

2. **The prepared artifact directory's parent is never flushed before dispatch.**
   - Location: `fleet_witness/controlled_calibration.py:79-86` and `_write_private` at lines 51-62.
   - The runner creates a new directory and fsyncs manifest.json and that directory, but never fsyncs the directory's parent. Flushing a directory persists its contents; it does not establish durability of the new directory entry in its parent. A system crash can therefore lose the output directory and prepared receipt after provider dispatch despite the explicit durability intent.
   - Evidence: the `fsync_targets` probe observed only `result/manifest.json`, `result`, `result/result.json`, `result`; `parent_fsynced=false`. This is a verified missing durability operation, not a claim that an actual power-loss test was executed.
   - Impact: the canonical ledger still protects the spend reservation, but the separately promised durable prepared manifest can disappear, losing its calibration-specific provenance and output location after a crash.
   - Fix: persist the newly created output directory entry by fsyncing its parent before dispatch, retaining the file and child-directory fsyncs. Add a behavioral ordering/failure test showing no credential or network access if any required preparation flush fails.

### Minor (Nice to Have)

1. **A supplied output-message ID is not type-validated.**
   - Location: `fleet_witness/swarm/providers.py:348-355`.
   - The allowlist accepts `id`, but never checks its value. A dictionary in `output[0].id` is accepted as a successful supervisor response (`invalid_message_id` in probes.json). The retained public schema specifies Optional[str], so absence/null can be allowed while an object is malformed.
   - Fix: validate supplied message IDs against their documented type and an explicit bound. Consider similarly validating the optional metadata fields that the strict envelope deliberately permits. This does not presently create effects or bypass the main response-ID check.

## Validation and evidence

- `PYTHONDONTWRITEBYTECODE=1 python -m unittest discover -s tests -v`: retained `python-tests.log` reports 248 tests in 26.839 seconds, OK. Inherited unclosed-SQLite ResourceWarnings remain visible; no warning-free claim. The command's final exit code was not separately retained by this review invocation.
- `PYTHONDONTWRITEBYTECODE=1 node --test tests/viewer.test.mjs`: exit 0; retained `viewer-tests.log` reports five passed, zero failed.
- `git diff --check b50569e..ebedd47`: no output/errors.
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python .../review/probes.py`: exit 0; synthetic keys and mocked transport only. Script and exact JSON outcomes retained here.
- Local runtimes: Python 3.15.0, Node v26.11.1. This is local regression evidence, not final-source hosted compatibility-matrix execution or runtime promotion.

## Recommendations

Fix the two Important issues with failing behavior tests, retain their RED/GREEN evidence, and run the required full suite on the final source. Update BUILD_STATUS and the task ledger with final source/test/review outcomes before integration. Continue treating the proposed calibration as a code candidate until separate live gates close.

## Declined to judge

- Actual provider billing, USD/credit conversion, balance, reasoning/fee ceilings and retention/handling acceptance: require account/provider evidence; flags and the owner statement are not independent qualification. Documentation keeps these gates open.
- TLS trust pinning, alternate-chain denial, actual credential-file loader and live worker/host isolation: inherited transport uses default TLS and environment credentials; these are explicitly unqualified operational/migration gates, not accepted by merging this candidate. No real-key probe was authorized for this review.
- Account-to-credential binding: the reused authorization schema has no explicit account field and environment credential selection is not cryptographically bound to the evidence hash. Account/runtime/trust binding must be settled in the separately gated activation design; this review does not accept flags as proof or declare live readiness.
- Provider `incomplete` with exactly max_output_tokens and coherent reported usage: treated by this branch as a billed invalid answer. I did not equate this terminal truncation condition with queued/in-progress; the actual provider billing semantics remain a live gate. The confirmed finding above concerns contradictory completed/incomplete representations.
- Hostile same-UID process races that replace source, credentials, directories or ledger files: worktrees/private files are not a hostile-process sandbox; the accepted contract calls for separately verified host isolation. Static symlink/exclusive-file checks were reviewed; no isolation claim is granted.
- Power-loss recovery on a real filesystem/host: no destructive crash experiment performed. The missing parent flush is reported from source and traced calls.
- Hosted final-source runtime matrix, deployment/cloud state, dashboard expiry, real calibration, billing reconciliation and confirmatory study: outside this read-only code review; no success inferred from older receipts or local test results.

## Assessment

**Ready to merge? With fixes.**

The code largely follows the approved integration plan and preserves the data-only/accounting boundaries, but the strict envelope must reject contradictory outcomes and the prepared receipt needs its complete directory-durability sequence. Fixing these establishes code readiness only; paid activation remains HOLD until the documented independent qualification and acceptance gates actually close.

## Integrator resolution

The original review above remains a verdict on ebedd47. In the single fix pass,
contradictory status/text now retains the full hold; malformed optional message
IDs are also rejected (integrator treated identity validation as part of the
strict-envelope acceptance defect). Parent-directory fsync occurs before
credential access or dispatch, and flush failure prevents both. Nineteen
focused tests pass after retained RED/GREEN evidence. Full final-suite results
are recorded in BUILD_STATUS. This resolution is not a second independent
review or live acceptance. All declined operational/host/account judgments
remain open; coherent terminal truncation remains an accounted invalid answer.
