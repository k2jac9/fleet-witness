# Expanded offline regression scenarios

Task: `expanded-scenarios`. These are scripted behavioral checks of the existing
public interfaces, using test-only HMAC keys and real SQLite transactions. They
provide no empirical model result or hostile-process containment evidence.

The task changes only `tests/test_expanded_scenarios.py` and this document.
Runtime, viewer, accepted ADRs, task scheduling, and the twenty-episode demo
remain unchanged. The requirements are [ADR-0002](adr/0002-evidence-and-authority.md),
[ADR-0003](adr/0003-transactional-effects.md),
[ADR-0004](adr/0004-paired-evaluation.md), and
[ADR-0007](adr/0007-isolated-paired-trials.md).

## Cases and hand-derived expectations

| Scenario | Expected observable behavior |
| --- | --- |
| Three genuine receipts, each missing a different required field | All six orderings deny authorization and commit no release. Fields from separate receipts cannot be combined into one attestation. |
| One complete attestation with inapplicable and forged neighbors | All six orderings authorize and commit one release in each isolated trial. A failed neighbor cannot hide valid evidence. |
| Genuine issuer, claim, scope, artifact, or run prefix near-match | Each denies authorization and effects. Exact applicability does not permit prefixes or wildcards. |
| Caller mutates receipt and supervisor-input dictionaries after recording | Execution and replay retain the original serialized decision evidence and input. Caller changes do not rewrite the snapshot. |
| Paired genuine build evidence with misleading reviewer approval | Raw scripted policy approves incorrectly; scope-explicit policy denies correctly. Neither execution commits an effect. Export reports one invalid recommendation separately from two denied attempts. |
| Interleaved paired trials, exercised with either presentation revoked first | One trial's revocation cannot affect its partner. The partner releases once, then returns an authorized duplicate no-op. Restoring the revoked trial permits a fresh attempt while replaying its old attempt returns the historical denial. Foreign decisions and colliding attempt identities are refused. |

The paired cases reuse the same signed receipts and underlying facts. The
interleaving case exports two valid decision snapshots, four recorded attempts,
two effects, and one authorization denial. Its policy-version histories are
`[1, 2, 3]` in the revoked/restored trial and `[1]` in the unaffected trial.
The build-evidence case deliberately attempts a denied supervisor decision to
check controller enforcement; the ordinary demo skips those attempts.

## Reproduce

From this task's worktree on Linux/POSIX with Python 3.11+, Git, and Node:

```sh
python -m unittest discover -s tests -p test_expanded_scenarios.py -v
python -m unittest discover -s tests -v
node --test tests/viewer.test.mjs
python scripts/fleet.py validate
git diff --check
```

Observed on 2026-11-08 against application source from
`87156f5419aa4c02c96091bfcad4a5d8a5dd2936`, using Python `3.15.0` and Node
`26.11.1`: six expanded tests pass, the full Python suite passes 55 tests, and
the viewer suite passes five tests. These local executable versions do not
establish the stable/upcoming/previous hosted CI matrix. The existing workflow
still selects Python 3.11/3.13 and Node 24 without exact runtime patch pins;
source-bound runtime adoption and hosted execution remain separate work.

## Sensitivity evidence

Disposable source copies were changed one at a time, leaving this worktree's
runtime untouched. The focused expanded suite failed with assertion failures
for every following counterfactual:

- Check only the first receipt instead of accepting any complete attestation.
- Accept matching field prefixes instead of exact values.
- Deduplicate releases across trials instead of within each trial.
- Mark every recommendation correct regardless of decision-time truth.

Each mutated run returned exit 1 without import errors. This demonstrates that
the new tests detect those specific faults; it is not exhaustive mutation
coverage. No new runtime behavior or security fix is claimed, so there is no
production red/green fix cycle in this tests-only task.

Full baseline/final logs, counterfactual source copies and failure logs are
retained under the owner workspace's sibling artifact directory:
`/home/neo/Projects/fleet-witness-artifacts/continuation-20261108-vBYyNBOq/`.
The baseline had 49 Python tests. Independent review and owner integration are
separate from passing tests or the manifest's scheduling status.

## Remaining gates

The expanded tests exercise in-process roles and committed local database
effects. Real-model trials, a credential-isolated provider gateway, verified
credit conversion and spend accounting, external publication, cloud IAM/IAP,
worker metadata/network denial, actual cgroups, timeouts, and ephemeral cleanup
require their own implementation and observed acceptance. Follow
[testing](TESTING.md), [deployment](DEPLOY_GCP.md), and
[security policy](SECURITY_POLICY.md) for those boundaries.
