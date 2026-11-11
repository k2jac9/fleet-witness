# Fleet Witness Assurance and Research Implementation Plan

> **For agentic workers:** Use `superpowers:executing-plans` for owner-led implementation. Independent review remains required by `AGENTS.md`; do not dispatch agents unless the session and task contract authorize it. Checkboxes describe future work, not completed work.

**Goal:** Repair the five audit findings without changing historical evidence, then prepare a separately reviewed, offline-first study of verifiable positive evidence.

**Architecture:** Keep the strict receipt-checking controller and the auditor-judged institution as separate contracts. Fix input handling and verification reporting locally, introduce explicit parser/provenance versions for new swarm runs, and protect run artifacts. A future verifier-result intervention is designed and rehearsed under a separate version before any new paid research.

**Tech stack:** Python 3.11+ standard library, SQLite, unittest, existing Node viewer and Git; optional NixOS/GCP under separate acceptance.

**Spec:** `docs/superpowers/specs/2026-11-10-assurance-and-research-design.md` (proposed). Base `416cc81f4c4d840089ff1fef59b2dc01184e97ba`; rebase task intake on the then-current reviewed commit and record it before editing.

## Global constraints

- Read `AGENTS.md`, architecture, accepted ADRs, assigned task, owner workstation policies, and the spec. One owner per task, literal owned paths, isolated branch/worktree, independent diff review, owner integration. Reconcile the file list and current DAG before allocation; correct any conflicting task contract before dispatch. Existing starter tasks marked done are not authorization to reuse them.
- Python runtime/tests use the standard library; Python 3.11+ and existing Node consumers remain supported. Default runs are offline and zero spend.
- Never rewrite accepted ADRs, frozen designs, raw data, prior responses, failed receipts, original papers, historical reviews or rollback assets. If a contract changes, propose a successor ADR and migration; label newly derived outputs and sources.
- The controller rechecks current authorization and applicable evidence with the release and audit event in one SQLite transaction. Supervisor/verifier output is never direct release authority. Paired trials retain equal facts and isolated effects; truth and keys remain outside model inputs.
- Security-sensitive fixes start with a failing behavioral test. Each implementation task remains provisional until its owner runs the full standard-library suite on that task's candidate and obtains the required independent diff review; the integrator reruns the full suite on the final combined candidate. Every task records exact source, runtime, commands, failures, reviewer and outcome. Do not claim untouched task status or live/hosted acceptance from local tests.
- No paid calls, deployments, new credentials, invitations, external messages or network scanning in this plan. Cloud inventory and billing readbacks are separate read-only operational tasks subject to applicable access and project policy. Existing spend ceilings do not qualify a new experiment.
- Before heavy builds, archive extraction/reproduction or image work, declare expected growth/output lifecycle and pass `workstation-storage` preflight/run for the real paths; preserve failures and do not release reservations without liveness review.

## Review focus

1. Already-stored malformed attestations and non-ASCII signatures must not poison valid quorum (Task 1).
2. A base invariant violation, escaped required mutant, malformed result or checker process error must not look like successful reproduction (Task 2).
3. Old archived records must keep their original treatment while new malformed/negated model outputs abstain (Task 3).
4. A permissive umask, pre-existing path, symlink, wrong owner or private data in a public export must not expose sealed material (Task 4).
5. A checker early return or exception must release queued database connections without losing the counterexample or altering measured semantics (Task 5).

## Sequence and owned paths

| Task | Depends on | Owned implementation/test paths | Deliverable |
| --- | --- | --- | --- |
| 0 | none | intake packet outside repo; no production changes | exact source, ownership and evidence baseline |
| 1 | 0 | `fleet_witness/institution.py`, `tests/test_institution.py` | safe institution input handling |
| 2 | 1 | `fleet_witness/verify_institution.py`, `scripts/reproduce_tables.py`, `tests/test_institution.py`, `tests/test_reproduction.py` | truthful checker/reproduction status |
| 3 | 2 | `fleet_witness/swarm/providers.py`, `fleet_witness/swarm/runner.py`, `fleet_witness/swarm/run_records.py`, `fleet_witness/swarm/sweep.py`, `tests/test_swarm_provider.py`, `tests/test_swarm_provenance.py`, `tests/test_reproduction.py` | versioned strict new-run parser and treatment-safe analysis |
| 4 | 3 | `fleet_witness/swarm/runner.py`, `fleet_witness/swarm/run_records.py`, `tests/test_swarm_provenance.py` | private run artifacts |
| 5 | 1 and 2 | `fleet_witness/verify_institution.py`, `tests/test_institution.py` | deterministic checker cleanup |
| 6 | 1–5 | integrator-owned `docs/TESTING.md`, `docs/SWARM.md`, `docs/GATES.md`, `docs/BUILD_STATUS.md` | integrated review and source-bound evidence |
| 7 | 6 | new successor design/ADR and new versioned implementation paths selected at intake | offline verifier-result design and rehearsal, separately scoped |
| 8 | 7 | research plan and operator evidence outside source until separately scoped | preregistered held-out cohort readiness, no dispatch |
| 9 | independent operational lane | current runbooks/adoption record only after observations | infrastructure and runtime qualification |

Overlapping paths make Tasks 1, 2 and 3 sequential at integration; Task 5 follows Tasks 1 and 2, and Task 4 follows Task 3. Do not create concurrent owners for overlapping paths. The integrator alone owns shared status documents after candidate review.

## Task 0: Intake and preserve baseline

- [ ] Inspect `git status --short --branch`, `git log -1 --format='%H %cI %s'`, `git worktree list --porcelain`, `python scripts/fleet.py validate` and `python scripts/fleet.py plan` in the authoritative checkout. Record exact source, task IDs, owned paths, active worktrees, runtime binaries, known gates and a new sibling artifact packet. Do not inspect unrelated worktrees or prune/overwrite them.
- [ ] Confirm the preceding audit's five reproducers on the selected source using synthetic data only; retain inputs, outputs, exit codes and expected failures. The prior audit found 320 Python/five Node tests passing at the base and pre-existing SQLite warnings; rerun only checks necessary to establish a changed base and record their real result.
- [ ] Prepare one isolated worktree/branch per approved implementation task, after reconciling the manifest, owned files, accepted ADRs and acceptance. Preserve unrelated edits and avoid shared-path parallel ownership.

## Task 1: Fail closed on malformed institution evidence

**Interfaces:** Preserve `Institution.submit_attestation(case_id, attestation)` and `Institution.execute(case_id, attempt_id)`. `_valid_attesters` returns the existing set/list semantics for normal/mutant paths. Invalid entries never count and do not throw; an effect and its audit remain atomic.

- [ ] Add tests in `tests/test_institution.py` in two independent cases. With valid case evidence, submit a list-valued auditor, a non-ASCII attestation signature and missing/wrong-type fields; assert no exception, invalid rows never count, insufficient quorum yields an audited denial, and a later valid quorum creates exactly one audited effect. In a separate case with a malformed evidence signature and valid quorum, assert an audited denial and no effect. Include already-persisted malformed JSON-compatible attestation rows and audit-insertion rollback.
- [ ] Run `python -m unittest discover -s tests -p test_institution.py -v`; retain the failing output and expected error before changing implementation.
- [ ] In `institution.py`, validate structure, field types and ASCII lowercase hexadecimal 64-character HMAC signatures before lookup/comparison. Treat malformed persisted entries as invalid. Validate `evidence` defensively without accepting malformed signatures; keep authentic-but-insufficient evidence semantics of the institution unchanged.
- [ ] Rerun the focused test; assert all pass and the valid quorum, duplicate and rollback tests still pass. Review the diff independently, then record the exact candidate commit and results.

## Task 2: Make bounded-checker failures observable

**Interfaces:** Keep `check(depth, mutations, stop_at_first, require_majority)` and existing human-readable CLI output. Add a versioned `--json` mode returning a closed result containing both kernel results and, when requested, all required mutant results; exit `0` only if both base checks hold and every requested mutant is caught, `1` for a failed check, and use normal argparse nonzero handling for malformed arguments. In JSON mode stdout is JSON only; diagnostics go to stderr. The default reproduction invokes the structured mode and retains both result and stderr.

- [ ] Add CLI/reproduction tests: mock one base violation, one uncaught mutant, malformed JSON, and subprocess failure separately; assert nonzero CLI/reproduction status and retained failure evidence. Assert a passing stub produces exit 0 and `--skip-checker` records `executed: false` without a pass claim. Test zero and negative depths are refused rather than vacuously verified.
- [ ] Run `python -m unittest discover -s tests -p test_reproduction.py -v` and the focused institution tests; retain expected failures.
- [ ] Implement structured result and status in `fleet_witness/verify_institution.py`. Update `scripts/reproduce_tables.py` to validate the schema, check both process status and structured outcome, persist command/source/result/failure provenance before raising, and keep extracted input hashes unchanged. Avoid parsing human-readable success text as authority.
- [ ] Repeat the focused suites. Verify a controlled injected violation and uncaught mutant cannot return success, then verify ordinary `--skip-checker` remains explicitly skipped. Run depth six with all mutants only after storage admission and record its actual result, resource use and retained log; a smaller mocked test is not depth-six evidence.

## Task 3: Version strict parsing for new swarm records

**Interfaces:** Preserve legacy `parse_vote(text)` / `parse_sign(text)` for old treatment and historical reproduction. Introduce named `parse_vote_strict(text)` and `parse_sign_strict(text)` returning the same `(outcome, reason)` shape. New-run provenance records `swarm-strict-v1`; known historical fixtures without an identifier are labeled `legacy-recorded`, while unknown missing/unsupported identifiers are refused by default. Summaries refuse mixed treatment IDs rather than pool them. Controlled supervisor parsing is unchanged.

- [ ] Add parser tests for exact JSON `{"vote":"approve","reason":"ok"}` and `{"sign":true,"reason":"ok"}`; reject prose `I do not approve this release.`, trailing text, duplicate/unknown fields, missing reason, non-string reason, `"true"`, malformed JSON, excessive length/depth and invalid Unicode as abstention. Verify a completed fake-run manifest and an interrupted run's start record carry the selected parser identity; historical reconstruction continues consuming its recorded outcomes. Assert mixed strict/legacy and unidentified manifests cannot be pooled, while explicitly identified historical fixtures still reproduce their prior counts.
- [ ] Run `python -m unittest discover -s tests -p test_swarm_provider.py -v` and `python -m unittest discover -s tests -p test_swarm_provenance.py -v`, retaining red results.
- [ ] Implement one bounded closed-object parser with duplicate-key rejection and exact types/allowed values; wire only new swarm runs to strict functions. No fallback on English keywords and no reuse of pilot-only schemas. Give invalid output an explicit abstention with a bounded non-authoritative reason. Persist an exclusive, private `run-start.json` with parser identity before the first call and also record it in the finished manifest; do not create an early `manifest.json`, because `run_sweep` currently treats that file as completion. Preserve public detector behavior deliberately.
- [ ] Update `swarm/sweep.py:summarize` to validate treatment identity before pooling. Map only explicitly identified historical archive/fixtures to `legacy-recorded`; reject mixed, unknown or unsupported treatment IDs with a clear error. Keep the original archive immutable and retain existing historical denominators. Test partial start records without treating them as completed runs.
- [ ] Rerun focused tests and `python -m unittest discover -s tests -p test_reproduction.py -v`. Compare a preserved representative historical archive/fixture's hashes and derived results before/after; where full archive reproduction is run, use fresh admitted paths and retain all outputs.

## Task 4: Keep new swarm material private by construction

**Interfaces:** `run_swarm(output, client, ...)` continues accepting a new path or a verified owner-private empty directory. It creates private directories (`0700`) and regular files (`0600`) for truth, events, manifest, decisions, database, journals and private receipts; no public export is implied. Document that same-user and compromised-host processes remain trusted.

- [ ] Add a POSIX behavioral test under umask `022` with a traversable temporary parent: run a one-case fake swarm and assert the new root, `truth.json`, `events.jsonl`, `institution.sqlite3` and private logs have owner-only access. Assert symlink roots, permissive pre-existing directories, nonempty directories and wrong-owner cases where safely simulatable are refused before model calls; do not chmod or remove caller data. Restore umask after the test.
- [ ] Run `python -m unittest discover -s tests -p test_swarm_provenance.py -v` and retain the failure.
- [ ] Make path creation/validation explicit in `runner.py` and `run_records.py`, using directory-anchored and no-follow/exclusive operations where appropriate. Verify ownership and restrictive modes; avoid process-global umask mutation in concurrent code. Ensure SQLite's journal/sidecar files inherit protection from the verified private directory. Model reasons stay private unless a future reviewed, sanitized export explicitly includes them.
- [ ] Rerun focused tests, including the existing private/public receipt tests. Inspect actual resulting modes and verify no new public export or changed historical archive. State filesystem and same-UID trust limitations in the task receipt.

## Task 5: Close checker state connections on every path

**Interfaces:** Preserve `check(...)` result schema and counterexample content. Explicitly close every cloned/queued SQLite connection after its final use, including discarded duplicate states, depth-limited states, normal completion, first-violation returns and exceptions.

- [ ] Add focused tests instrumenting created/closed connections on normal completion, duplicate-state disposal, injected violation and injected `_apply` exception. Assert every owned connection closes and the original exception/counterexample survives. Separately test Python `ResourceWarning` collection in a bounded subprocess; do not hide warnings globally.
- [ ] Run the focused institution suite and retain red results. Implement `try/finally` ownership cleanup in `verify_institution.py`; do not close a state still needed by the queue.
- [ ] Rerun focused tests and compare checker state/transition counts and all seven mutant outcomes against the preserved base at the same depth and source identities. Measure peak RSS, wall time and warnings on the same runtime; test the configured 1 GiB worker limit only in an admitted disposable environment. Report observed values and any remaining warnings, not an assumed improvement.

## Task 6: Integrate and independently review

- [ ] Integrator reviews every task's exact diff, red/green results and threat boundary; an independent reviewer checks the combined diff and resolved findings. Preserve all failed receipts. Update current `docs/TESTING.md`, `docs/SWARM.md`, `docs/GATES.md`, and prepend a dated `docs/BUILD_STATUS.md` entry with the tested base or code-tree identity, commands, results and unexecuted checks. Use “the containing commit identifies this revision” rather than attempting a self-referential commit hash. Store final commit, exact-tree CI and review identities in the external artifact packet or a clearly separate later evidence commit. Do not edit historical manuscript, study design, outputs or accepted ADRs.
- [ ] Run `python -m unittest discover -s tests -v`, `node --test tests/viewer.test.mjs`, `python scripts/fleet.py validate`, `python scripts/fleet.py plan`, `python -m scripts.verify_submission`, and `git diff --check`. Record interpreter and executable identities, output, exit status and warnings. Run admitted default reproduction including depth-six checker separately; retain exact source/input/output hashes and any failure.
- [ ] Require exact-candidate hosted stable, upcoming, previous and promised consumer lanes; refresh upstream selections at the normal review or before an upgrade and record unavailable lanes. Review any preview failure without treating it as stable acceptance. Do not claim CI from YAML or apply older CI to a changed tree.
- [ ] Owner integrates only after independent review and applicable checks; report task IDs, exact commits, changed paths, actual results and remaining gaps. This plan itself does not authorize a merge or publication.

## Task 7: Design an offline verifier-result intervention

**Design gate:** Produce a new explicitly proposed successor design/ADR before behavioral implementation if required by the accepted contract. The pre-existing pilot's `pilot_design.py`, prompts, hashes, data and authorization stay frozen. Avoid treating a trusted verifier's result as independent oracle truth without testing provenance and binding.

- [ ] Compare at least: unchanged current facts/instructions; a structured verifier result available to both paired arms; and a deliberate information intervention where only the treatment sees that result. Select the experimental question and avoid calling the latter a prompt-only comparison. Define exact result schema, evidence-set digest, run/artifact binding, time/snapshot policy, authenticated producer and freshness semantics; choose safe representation for unknown/invalid. Record threat model, tradeoffs, leakage constraints and migration in the proposed design.
- [ ] Assign a new schema, module paths, explicit task owner/owned paths and focused acceptance in the successor plan. First write failing tests for valid, forged, wrong issuer/scope/artifact/run, stale, absent, tampered and substituted results, untrusted reviewer text, policy revocation after decision, duplicate execution and separate trial state. Ensure model-visible payload never includes issuer keys or sealed evaluator truth.
- [ ] Implement only the approved offline interface and fake-provider rehearsal in the isolated task worktree; preserve separate evaluator truth and verify controller execution rechecks current authority independently. Report false approvals, false denials and invalid responses separately. Full suites and independent review are required; fake behavior is not a live result.

## Task 8: Preregister a new held-out study, then requalify

- [ ] Write a distinct preregistration specifying hypothesis, baseline, information difference, primary joint safety/availability metrics, denominator, case families, held-out generation, sample rationale, randomization, dependence assumptions, stopping, missingness and analysis. Freeze source/design and label exploratory versus confirmatory. No number of calls is inherited as authorization from the old cohort.
- [ ] Before any dispatch, independently verify source-bound review/CI, current provider/model/route/account access, price/units/all billable token bounds, handling/retention, TLS/host, canonical ledger and unresolved liabilities. Specify a valid operator record and applicable request/count/duration/cap; preserve previous budget authority without treating a dated balance as current.
- [ ] Run and reconcile a separate calibration only when all applicable gates and existing authority permit it. Retain stopped/failed calls, never silently retry or resume a closed cohort. Collection, reconciliation and publication are separate future actions; this plan records no approval or execution of them.

## Task 9: Separate operations and longer-term research

- [ ] Read-only inventory: identify exact cloud project/service/job/image/VM/disk and audit-log identities, costs, and expiry-task attribution; report missing access or ambiguous absence. Do not recreate, delete or start resources to make a check pass. Retain output outside Git and redact credentials.
- [ ] Produce separately owned host/collector/gateway and rollback acceptance plans using `docs/NIXOS_FLEET.md`, `docs/DEPLOY_GCP.md`, `docs/OPERATIONS.md`, `docs/SECURITY_POLICY.md`, and `docs/RUNTIME_ADOPTION.md`. A configured namespace, stopped VM or scheduled deletion is not observed containment, recovery or expiry. Verify both IPv4/IPv6 metadata and host-proxy boundaries only within approved targets.
- [ ] Evaluate correlated honest errors, seat steering, multi-case bounded checking, and trusted-authority composition as separately scoped research. Public observation, signing-key changes, external effects, other providers and automated worker dispatch need independent design/authorization; none is a prerequisite for local assurance fixes.

## Plan self-review and current limitations

Tasks 1–5 map to every prior audit finding and each review-focus item has its own failing behavioral test. Task 6 makes exact-source acceptance and historical preservation explicit. Tasks 7–9 are design/qualification handoffs; their implementation details must be resolved in their own scoped design rather than guessed here. A future independent reviewer must inspect the plan and each implementation diff. The planning review did not establish current cloud state, provider access, current upstream runtime freshness or event submission, and it did not read every page of the image-only event capture.

On 2026-11-10 an independent builder checked this proposed plan against current code. Its findings led to separate malformed-evidence and malformed-attestation tests, parser-treatment checks before pooling, a pre-call start record that does not masquerade as a completed manifest, non-self-referential commit/CI receipts, rejection of zero-depth checking, and full-suite acceptance for each implementation task. This planning check is not a review of future implementation diffs.
