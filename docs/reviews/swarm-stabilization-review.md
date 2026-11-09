# Independent whole-candidate review

Task: swarm-stabilization-20261109, independent final review.
Base: `bba5e8813142cad4e1fe9657057e3cc1709c56c9`.
Reviewed HEAD: `8c0c790515db16f1af8468c4978070a505709b82`.
Stabilization begins after `6061cb20f39ac19fcc95b09303e02ebcd43a9887`.
Checkout: `/home/neo/Projects/fleet-witness/.worktrees/stabilization-20261109`.
Read-only review: no checkout, branch or index mutation; no credentials, network, paid calls or subagents.

## Strengths

- The SQLite ledger reserves before dispatch, uses `BEGIN IMMEDIATE`, retains reservations across restarts and process crashes, and commits accounting with its audit row. Immutable caps and unresolved holds meaningfully prevent the prior tag/reset and ambiguous-charge problems. Large known liabilities are retained rather than clipped to available funds.
- Provider transport has one direct HTTPS attempt, no inherited proxy/redirect/retry layer, bounded request and response sizes, a bounded caller deadline and protected request fields. Failure receipts retain request identity and held liability even when the logical response never completes.
- The public/private split removes raw prompts from detector events while retaining private request/response evidence and source/runtime/configuration identity. Defaults remain offline; operator assertions are accurately described as assertions, not cryptographic qualification.
- Archive validation precedes destination creation and covers traversal, aliases, links, collisions and expansion. The reconstructed zero-seat control actually invokes `Institution.execute`; historical receipt authentication and new model observations are explicitly disclaimed. Raw archive/reviews and accepted ADRs were unchanged by stabilization.
- The report corrects conventional medians, paired denominators, causal figure wording and incomplete historical cost/provenance claims. Its reference-verification and live-qualification limitations remain visible.

## Findings

### Important R1: shared run request limit is enforced separately for each model record

Locations: `fleet_witness/swarm/ledger.py:189-191`; `fleet_witness/swarm/operator.py:95-109`.

`authorized_clients` requires identical request limits and advertises one shared run envelope, but `Ledger.reserve` counts rows by `authorization_id`. Each model necessarily has a distinct record, so each can consume the entire shared limit. This does not bypass the monetary cap, but it exceeds the independently authorized request count and repeats after restart because the durable query uses the wrong scope.

Reproduction: create two valid synthetic records for two models with the same ledger, run ID, caps, expiry and `request_limit=1`; construct them through the real `authorized_clients`; replace only `_env_key` with a synthetic string and `_post` with a deterministic valid response. One call per model succeeds. The real ledger reports two dispatched attempts and no halt. Evidence: `request-limit/result.json`, `request-limit/ledger.sqlite3`, and private synthetic authorization bundle in this directory. No actual provider request was made.

Fix: durably bind an immutable shared request cap to a run/envelope and count all of its reservations in the same transaction, across models/processes/restarts. Preserve any additional per-record limit separately. Add a behavioral regression that the second model cannot dispatch after the shared count is consumed.

### Important R2: new provider fixtures break the Git-free offline worker snapshot

Locations: `tests/test_swarm_provider.py:15-21`; `fleet_witness/swarm/authorization.py:28-31,65-69`; `flake.nix:43-62`; `nix/offline-task.sh:26`.

The provider fixture builds an authorization from the executing checkout's Git HEAD. In the intentionally Git-free Nix worker source, `source_identity()` returns `source_commit=None`, and the production validator correctly rejects it because a 40-character reviewed commit is required. Consequently ordinary offline security tests fail in the supported worker source layout before they exercise their intended behavior. A Git checkout passing the tests does not qualify that snapshot.

Evidence: inspected the fixture, validator, source filter and offline task directly. The parent independently executed the bounded source-only snapshot probe at this same HEAD; `../snapshot-provider-receipt.json` records `snapshot_has_git=false`, exit 1, with failures retained in `../snapshot-provider-red.log`. This is not a Nix derivation build or boot test.

Fix: make synthetic test source identities controlled and self-contained while continuing to test production rejection of absent/mismatched source identity. Do not weaken paid authorization or add credentials/Git state to the worker snapshot just to satisfy fixture assumptions. Exercise the full supported Git-free offline task after the fix.

### Important R3: reproduction silently attributes swapped model datasets to the wrong models

Locations: `scripts/reproduce_tables.py:47-55,74-79`; `scripts/independence.py:33-45`.

Each named sweep is internally validated, but its manifest model ID is never checked against the model assigned by the hard-coded root/label mapping. Swapping the three DeepSeek ambiguous sweep directories with their gpt-oss counterparts passes all checks and emits `independence.json` labeled DeepSeek over gpt-oss observations and vice versa. The output contains no actual model identity to expose the mismatch locally. Input hashes faithfully bind the wrong mapping; they do not establish its correctness.

Reproduction: extracted the unchanged committed ZIP into `mismatched-models/extracted`, swapped only the six copied ambiguous sweep directory names, and ran real `reproduce(inputs, fresh_output, skip_checker=True)`. It succeeded with `inputs_unchanged=true`. `mismatched-models/result.json` records `ambig-deepseek-s3000` containing `openrouter:openai/gpt-oss-20b` and `ambig-gptoss-s3000` containing `openrouter:deepseek/deepseek-v4-flash-0731`, while derived labels remain DeepSeek and gpt-oss. Full outputs, input hashes, extraction receipt and log are retained. Original archive and reproduction inputs elsewhere were untouched.

Fix: validate the declared dataset's model and relevant experiment identity before creating outputs, including agreement between each model's main and ambiguous sweeps. Bind the actual provider/model IDs into derived results. Add swapped/wrong-model and mismatched configuration regressions.

### Minor R4 (integrator escalated to Important): an undispatched reservation counts as a provider attempt in review manifests

Locations: `fleet_witness/swarm/run_records.py:11-16,87-93`; consumers `scripts/peer_review.py:205` and `scripts/reviewer_speedtest.py:106`.

`public_attempts` drops the per-attempt `provider_attempts` field, and `PrivateRunLog.summary` counts list length. If reservation succeeds but dispatch persistence fails, the provider exception and authoritative ledger correctly report zero dispatched attempts, yet review/speedtest manifest summaries report one. The reservation must remain visible, but it must not become an HTTP attempt in the summary.

Reproduction: real `ModelClient` and ledger, synthetic key, dispatch patched to raise an `OSError` before its write, transport patched to fail if called. Exception count=0, ledger count=0 and transport calls=0; writing the exception through `public_attempts` and `PrivateRunLog` produces summary count=1. Evidence: `attempt-count/result.json` and private receipt/ledger. Reviewer grades this Minor because spending still stops and liability remains correct; the integrator explicitly escalated it to Important because accurate failure accounting is central to this task. Both assessments are preserved here.

Fix: retain the safe per-attempt dispatch count and sum it, while retaining reservation IDs separately. Cover pre-dispatch persistence failure and successful dispatch followed by timeout.

## Verification and review coverage

- Read owner/workspace/runtime policies, project AGENTS, architecture, accepted ADRs, approved plan/spec and ledger rulings. Inspected changed executable source directly in provider/accounting, runner/operator/private receipts, kernel/reproduction, review scripts and report passes; did not treat the large historical review corpus as executable authority.
- `PYTHONDONTWRITEBYTECODE=1 python -m unittest discover -s tests -p 'test_swarm*.py' -v`: 56 passed, `swarm-focused.log`.
- `PYTHONDONTWRITEBYTECODE=1 python -m unittest discover -s tests -p 'test_reproduction.py' -v`: 13 passed, `reproduction-focused.log`.
- `git diff --check BASE..HEAD`: passed. HEAD and clean worktree rechecked. `git diff --name-only 6061cb20..HEAD -- docs/adr data/fleet-witness-runs-2026-11-08.zip docs/report/reviews docs/report/review-data.md` was empty.
- Three bounded offline reproductions above use real production paths except explicit synthetic credential, transport and persistence-failure doubles. No spend authority was issued.
- The full 228-test suite, viewer 5-test suite, depth-six checker and PDF page inspection are parent/worker evidence supplied to this review, not independently rerun here. The supplied integrated reproduction binds source `5090252`; parent states code is identical at the reviewed HEAD. Full final checks and hosted CI remain integrator gates.
- One read command used a guessed ADR-0009 filename and failed; corrected using `rg --files docs/adr` and read the actual `0009-gcp-deployment.md`. No source or evidence was changed by that failed read.

## Declined to judge

- Live provider access, billing units/prices, retention, actual TLS/provider behavior and independent operator qualification: this review is explicitly offline and has no credential/network authority; operator assertions are not evidence of those facts.
- Historical receipt signatures, exact prompts, HTTP attempts and complete billing: those source records were not retained; reconstruction is correctly labeled and cannot recreate them.
- Cloud deployment, dashboard expiry, external spend and host/process isolation: outside this local candidate review; separate gates remain pending.
- Hostile same-UID filesystem races or compromised trusted operator: current implementation explicitly trusts the host/operator; private modes and worktrees are not a hostile-process sandbox.
- A migration/reconciliation operator utility: explicitly not implemented or authorized by this stabilization; existing JSON ledgers fail closed and unresolved holds remain held. Its absence must not be interpreted as permission to initialize a fresh live ledger.
- Independently source-verifying literature/novelty claims and historical authorship/timing: unavailable within the offline review constraint; the report keeps source verification pending before submission.
- Independent visual reinspection of every PDF page: relied on the retained publication-worker rendering/inspection evidence; this review inspected current report prose, figure changes and correction/provenance records.
- Tightening the inherited heuristic `parse_vote`/`parse_sign` logical-answer parsers: these are unchanged from the review base and changing them changes experimental treatment. The provider envelope is hardened here; strict inner-answer semantics require an explicit integrator ruling before future paid qualification, not an implied finding that these parsers satisfy ADR-0010's closed-schema supervisor contract.

## Assessment

**Ready to merge: No.** The candidate substantially improves preservation, transactional budgets and reproducibility, but the shared request-count envelope and dataset attribution still fail concrete offline probes, and the supported Git-free worker test path regresses. Fix the findings, preserve these failures, rerun the required final checks and obtain review of the exact updated commit before integration. This review grants no merge, publish, deployment or paid-call authority.
